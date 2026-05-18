"""
apply_action.py — Phase 5 Day 4 single-action executor.

Given one approved ProposedAction:

  1. Refuse if target_table is not in ALLOWED_TARGET_TABLES.
  2. Run the INSERT / UPDATE against the target table.
  3. Append a single manager_actions row carrying before_payload +
     after_payload + intake_drop_id so undo can replay the pre-image.

apply_action operates on its own connection but supports being called
inside a parent transaction by accepting a `cur` parameter from
apply_batch.

Public surface
--------------
    apply(action, *, manager_user_id) -> AppliedActionResult
    _apply_with_cursor(action, cur, *, manager_user_id) -> AppliedActionResult
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import psycopg2

from scripts.ledger import load_env
from scripts.manager.routing._shared import ALLOWED_TARGET_TABLES, ProposedAction


@dataclass
class AppliedActionResult:
    manager_action_id: str
    target_record_id: str
    action_type: str
    target_table: str


class ApplyError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Per-table writers. Each returns the target_record_id (uuid string).
# The writers stay deliberately narrow — only the small set of columns
# the entity router proposes. Adding new columns later requires editing
# the corresponding writer.
# ---------------------------------------------------------------------------
def _write_aleksandra_timeline(
    cur: psycopg2.extensions.cursor, action: ProposedAction
) -> str:
    p = action.after_payload
    if action.action_type in {"add_event", "add_milestone", "create"}:
        cur.execute(
            """
            INSERT INTO aleksandra_timeline
                (event_date, event_type, title, description, institution, location)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                p.get("event_date"),
                p.get("event_type") or "observation",
                p.get("title") or "(no title)",
                p.get("description"),
                p.get("institution"),
                p.get("location"),
            ),
        )
        return str(cur.fetchone()[0])
    if action.action_type == "update" and action.target_record_id:
        cur.execute(
            """
            UPDATE aleksandra_timeline
            SET event_date=%s, event_type=%s, title=%s,
                description=%s, institution=%s, location=%s
            WHERE id=%s
            """,
            (
                p.get("event_date"),
                p.get("event_type"),
                p.get("title"),
                p.get("description"),
                p.get("institution"),
                p.get("location"),
                action.target_record_id,
            ),
        )
        return action.target_record_id
    raise ApplyError(
        f"aleksandra_timeline does not support action_type={action.action_type!r}"
    )


def _write_therapies(cur: psycopg2.extensions.cursor, action: ProposedAction) -> str:
    p = action.after_payload
    if action.action_type == "create":
        cur.execute(
            """
            INSERT INTO therapies (name, name_aliases, therapy_type,
                                   evidence_in_hie, aleksandra_status,
                                   aleksandra_notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                p.get("name"),
                p.get("name_aliases"),
                p.get("therapy_type"),
                p.get("evidence_in_hie") or "unknown",
                p.get("aleksandra_status") or "evaluating",
                p.get("aleksandra_notes"),
            ),
        )
        return str(cur.fetchone()[0])
    if action.action_type == "update" and action.target_record_id:
        # Only update fields the router proposed — never dose/name even if
        # an upstream bug snuck them into the payload. Defense in depth.
        cur.execute(
            """
            UPDATE therapies
            SET aleksandra_notes=%s,
                evidence_summary=COALESCE(%s, evidence_summary),
                aleksandra_status=COALESCE(%s, aleksandra_status),
                updated_at=NOW()
            WHERE id=%s
            """,
            (
                p.get("aleksandra_notes"),
                p.get("evidence_summary"),
                p.get("aleksandra_status"),
                action.target_record_id,
            ),
        )
        return action.target_record_id
    raise ApplyError(f"therapies does not support action_type={action.action_type!r}")


def _write_contacts(cur: psycopg2.extensions.cursor, action: ProposedAction) -> str:
    p = action.after_payload
    if action.action_type in {"add_contact", "create"}:
        cur.execute(
            """
            INSERT INTO contacts (full_name, email, contact_type, institution)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (
                p.get("full_name"),
                p.get("email"),
                p.get("contact_type") or "researcher",
                p.get("institution"),
            ),
        )
        return str(cur.fetchone()[0])
    if action.action_type == "update" and action.target_record_id:
        cur.execute(
            """
            UPDATE contacts
            SET full_name=COALESCE(%s, full_name),
                email=COALESCE(%s, email)
            WHERE id=%s
            """,
            (p.get("full_name"), p.get("email"), action.target_record_id),
        )
        return action.target_record_id
    raise ApplyError(f"contacts does not support action_type={action.action_type!r}")


# ---------------------------------------------------------------------------
# manager_actions writer — every successful apply produces ONE row.
# ---------------------------------------------------------------------------
def _log_manager_action(
    cur: psycopg2.extensions.cursor,
    *,
    manager_user_id: str,
    action: ProposedAction,
    written_target_id: str,
) -> str:
    cur.execute(
        """
        INSERT INTO manager_actions
            (manager_user_id, action_type, target_table, target_record_id,
             before_payload, after_payload, source_input, intake_drop_id,
             approved_at)
        VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb,
                'api', %s, NOW())
        RETURNING id
        """,
        (
            manager_user_id,
            action.action_type,
            action.target_table,
            written_target_id,
            json.dumps(action.before_payload) if action.before_payload else None,
            json.dumps(action.after_payload),
            action.intake_drop_id,
        ),
    )
    return str(cur.fetchone()[0])


# ---------------------------------------------------------------------------
# Cursor-scoped apply — used by apply_batch inside a parent transaction.
# ---------------------------------------------------------------------------
def _apply_with_cursor(
    action: ProposedAction,
    cur: psycopg2.extensions.cursor,
    *,
    manager_user_id: str,
) -> AppliedActionResult:
    if action.target_table not in ALLOWED_TARGET_TABLES:
        raise ApplyError(
            f"target_table {action.target_table!r} not in ALLOWED_TARGET_TABLES"
        )

    if action.target_table == "aleksandra_timeline":
        written = _write_aleksandra_timeline(cur, action)
    elif action.target_table == "therapies":
        written = _write_therapies(cur, action)
    elif action.target_table == "contacts":
        written = _write_contacts(cur, action)
    else:
        raise ApplyError(
            f"no writer implemented for target_table {action.target_table!r}"
        )

    ma_id = _log_manager_action(
        cur,
        manager_user_id=manager_user_id,
        action=action,
        written_target_id=written,
    )
    return AppliedActionResult(
        manager_action_id=ma_id,
        target_record_id=written,
        action_type=action.action_type,
        target_table=action.target_table,
    )


def apply(action: ProposedAction, *, manager_user_id: str) -> AppliedActionResult:
    """Apply one approved action atomically. Opens its own connection."""
    load_env()
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        with conn.cursor() as cur:
            result = _apply_with_cursor(action, cur, manager_user_id=manager_user_id)
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


__all__ = ["apply", "ApplyError", "AppliedActionResult", "_apply_with_cursor"]
