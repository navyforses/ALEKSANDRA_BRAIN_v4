"""
audit_query.py — Phase 5 Day 5 manager_actions read/list helpers.

Two public surfaces:

  page(manager_user_id, *, limit, offset, action_type, target_table)
      Paginated chronological list (newest first) used by /audit-log.

  list_recent(manager_user_id, *, limit) — for the BrainPanel activity
  feed. Includes intake_drop_id so the UI can link back to the drop
  that triggered the action.

Both surfaces filter strictly on manager_user_id so two operators (if
that day ever comes) can't see each other's audit trail through the
REST surface.
"""

from __future__ import annotations

import os
from typing import Any

import psycopg2

from scripts.ledger import load_env


def _open():
    load_env()
    return psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")


def _row_to_dict(row: tuple) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "action_type": row[1],
        "target_table": row[2],
        "target_record_id": str(row[3]) if row[3] else None,
        "before_payload": row[4],
        "after_payload": row[5],
        "source_input": row[6],
        "intake_drop_id": str(row[7]) if row[7] else None,
        "approved_at": row[8].isoformat() if row[8] else None,
        "reversed_at": row[9].isoformat() if row[9] else None,
        "reversed_by": row[10],
        "created_at": row[11].isoformat() if row[11] else None,
    }


_BASE_SELECT = """
    SELECT id, action_type, target_table, target_record_id,
           before_payload, after_payload, source_input, intake_drop_id,
           approved_at, reversed_at, reversed_by, created_at
    FROM manager_actions
"""


def page(
    manager_user_id: str,
    *,
    limit: int = 25,
    offset: int = 0,
    action_type: str | None = None,
    target_table: str | None = None,
) -> list[dict[str, Any]]:
    """Return one page of manager_actions, newest first."""
    where = ["manager_user_id = %s"]
    params: list[Any] = [manager_user_id]
    if action_type:
        where.append("action_type = %s")
        params.append(action_type)
    if target_table:
        where.append("target_table = %s")
        params.append(target_table)
    sql = (
        _BASE_SELECT
        + " WHERE "
        + " AND ".join(where)
        + " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    )
    params.extend([int(limit), int(offset)])
    conn = _open()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
    finally:
        conn.close()
    return [_row_to_dict(r) for r in rows]


def list_recent(manager_user_id: str, *, limit: int = 25) -> list[dict[str, Any]]:
    """Newest N actions for the BRAIN-panel activity feed."""
    return page(manager_user_id, limit=limit, offset=0)


__all__ = ["page", "list_recent"]
