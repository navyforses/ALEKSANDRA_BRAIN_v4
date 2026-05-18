"""
log_action.py — Phase 5 Day 5 manager_actions writer for non-target actions.

The main write path is ``scripts.manager.routing.apply_action`` (Day 4) —
every BRAIN-applied CRUD ends up there. This module covers two edge
cases that don't go through apply_action:

  1. ``log_dismiss(intake_drop_id)`` — operator rejects an intake_drops
     row. Writes ``action_type='dismiss'`` with the intake_drop_id as
     provenance; no target_table change.

  2. ``log_pattern(pattern_payload)`` — operator records a longitudinal
     observation (e.g., "feeding has improved over 7 days") that
     doesn't fit a single table. Stored as ``action_type='log_pattern'``
     with the full description in ``after_payload`` so the audit log
     still shows the moment.
"""

from __future__ import annotations

import json
import os
from typing import Any

import psycopg2

from scripts.ledger import load_env


def _conn():
    load_env()
    return psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")


def log_dismiss(
    *,
    intake_drop_id: str,
    manager_user_id: str,
    reason: str | None = None,
) -> str:
    """Append a manager_actions row recording the operator's dismiss."""
    payload = {"reason": reason or "no reason provided"}
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO manager_actions
                    (manager_user_id, action_type, target_table,
                     after_payload, source_input, intake_drop_id, approved_at)
                VALUES (%s, 'dismiss', 'intake_drops', %s::jsonb,
                        'api', %s, NOW())
                RETURNING id
                """,
                (manager_user_id, json.dumps(payload), intake_drop_id),
            )
            row = cur.fetchone()
            # Also mark the intake_drops row as rejected so it stops appearing
            # in the operator's pending queue.
            cur.execute(
                "UPDATE intake_drops SET status='rejected', resolved_at=NOW() WHERE id=%s",
                (intake_drop_id,),
            )
        conn.commit()
        return str(row[0])
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def log_pattern(
    *,
    manager_user_id: str,
    description: str,
    payload: dict[str, Any] | None = None,
) -> str:
    """Append a longitudinal-observation row to manager_actions."""
    body = {"description": description, **(payload or {})}
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO manager_actions
                    (manager_user_id, action_type, target_table,
                     after_payload, source_input, approved_at)
                VALUES (%s, 'log_pattern', 'kv_state', %s::jsonb,
                        'api', NOW())
                RETURNING id
                """,
                (manager_user_id, json.dumps(body)),
            )
            row = cur.fetchone()
        conn.commit()
        return str(row[0])
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


__all__ = ["log_dismiss", "log_pattern"]
