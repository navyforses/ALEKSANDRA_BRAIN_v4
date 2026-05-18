"""
undo.py — Phase 5 Day 5 manager_actions reverse path.

Undo contract (Phase 5 plan §"Day 5"):

  - Only rows with reversed_at IS NULL AND created_at > now()-'24h' are
    undoable (UndoNotAllowed raised otherwise).

  - Single-shot: once reversed_at is set, a second undo on the same row
    raises UndoNotAllowed("already reversed").

  - Reversing an INSERT (create/add_event/add_milestone/add_contact)
    DELETEs the target_record_id row from target_table.

  - Reversing an UPDATE writes the before_payload back onto the target
    row's columns. UPDATEs whose before_payload is missing or empty are
    refused — there is nothing to restore.

  - Audit trail: undo writes a NEW manager_actions row with
    action_type='reverse', target_table='manager_actions',
    target_record_id=original_action_id. The pre/after_payload of the
    reverse row swap places (original.after_payload -> before;
    original.before_payload -> after) so the audit log can show what
    was undone.

  - Reversed actions stay queryable forever — immutable trail.

Refused targets
---------------
Reversing a 'dismiss' or 'log_pattern' is a no-op on target rows; the
undo path still appends a reverse audit row so the operator's intent
is recorded, but it does NOT touch intake_drops.status (a dismiss is
permanent the moment it lands — re-opening must go through a new drop).

Public surface
--------------
    undo(manager_action_id, *, manager_user_id) -> UndoResult
    list_undoable(manager_user_id, *, limit=30) -> list[dict]
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import psycopg2

from scripts.ledger import load_env


UNDO_WINDOW_HOURS = 24
UNDO_LIST_LIMIT = 30

# action_types that touch target_table rows (and therefore have a
# matching reverse path). Everything else still gets a reverse audit
# row but no target write.
TARGET_WRITING_ACTION_TYPES = frozenset(
    {"create", "update", "add_event", "add_milestone", "add_contact"}
)

# Tables we know how to delete from / restore in. Stays narrow on
# purpose — adding new tables requires writing a matching reverse
# routine here.
REVERSIBLE_TABLES = frozenset({"aleksandra_timeline", "therapies", "contacts"})


class UndoNotAllowed(RuntimeError):
    pass


class UndoError(RuntimeError):
    pass


@dataclass
class UndoResult:
    reverse_action_id: str
    original_action_id: str
    target_table: str
    target_action_taken: str  # 'deleted_row' | 'restored_row' | 'audit_only'


def _open():
    load_env()
    return psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")


def _delete_target_row(
    cur: psycopg2.extensions.cursor, *, target_table: str, target_record_id: str
) -> None:
    if target_table not in REVERSIBLE_TABLES:
        raise UndoError(f"no reverse routine for target_table={target_table!r}")
    cur.execute(
        f"DELETE FROM {target_table} WHERE id = %s",  # noqa: S608 - table name is allow-listed
        (target_record_id,),
    )


def _restore_target_row(
    cur: psycopg2.extensions.cursor,
    *,
    target_table: str,
    target_record_id: str,
    before_payload: dict[str, Any],
) -> None:
    """Restore the target row's columns to the before-image values.

    The set of columns the writer is allowed to touch is narrow per
    table — anything not present in the per-table SET clause is left
    alone. This matches the apply_action.py writers.
    """
    if target_table == "aleksandra_timeline":
        cur.execute(
            """
            UPDATE aleksandra_timeline
            SET event_date=%s, event_type=%s, title=%s,
                description=%s, institution=%s, location=%s
            WHERE id=%s
            """,
            (
                before_payload.get("event_date"),
                before_payload.get("event_type"),
                before_payload.get("title"),
                before_payload.get("description"),
                before_payload.get("institution"),
                before_payload.get("location"),
                target_record_id,
            ),
        )
        return
    if target_table == "therapies":
        cur.execute(
            """
            UPDATE therapies
            SET aleksandra_notes=%s,
                evidence_summary=%s,
                aleksandra_status=%s,
                updated_at=NOW()
            WHERE id=%s
            """,
            (
                before_payload.get("aleksandra_notes"),
                before_payload.get("evidence_summary"),
                before_payload.get("aleksandra_status"),
                target_record_id,
            ),
        )
        return
    if target_table == "contacts":
        cur.execute(
            """
            UPDATE contacts
            SET full_name=%s, email=%s
            WHERE id=%s
            """,
            (
                before_payload.get("full_name"),
                before_payload.get("email"),
                target_record_id,
            ),
        )
        return
    raise UndoError(f"no restore routine for target_table={target_table!r}")


def undo(manager_action_id: str, *, manager_user_id: str) -> UndoResult:
    """Reverse one manager_actions row. Single transaction.

    Raises UndoNotAllowed when the row is outside the 24-h window, has
    already been reversed, or belongs to a different operator.
    """
    conn = _open()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT manager_user_id, action_type, target_table,
                       target_record_id, before_payload, after_payload,
                       reversed_at, created_at
                FROM manager_actions
                WHERE id = %s
                  AND manager_user_id = %s
                  AND reversed_at IS NULL
                  AND created_at > now() - interval '{UNDO_WINDOW_HOURS} hours'
                FOR UPDATE
                """,  # noqa: S608 - interval is a literal int
                (manager_action_id, manager_user_id),
            )
            row = cur.fetchone()
            if row is None:
                raise UndoNotAllowed(
                    "row not found OR already reversed OR outside 24h window OR "
                    "manager_user_id mismatch"
                )
            (
                _muid,
                action_type,
                target_table,
                target_record_id,
                before_payload,
                after_payload,
                _reversed_at,
                _created_at,
            ) = row

            target_action: str = "audit_only"

            if action_type in TARGET_WRITING_ACTION_TYPES and target_record_id:
                if action_type == "update":
                    if not before_payload:
                        raise UndoError(
                            "update action has no before_payload — cannot restore"
                        )
                    _restore_target_row(
                        cur,
                        target_table=target_table,
                        target_record_id=str(target_record_id),
                        before_payload=before_payload,
                    )
                    target_action = "restored_row"
                else:
                    # create / add_event / add_milestone / add_contact
                    _delete_target_row(
                        cur,
                        target_table=target_table,
                        target_record_id=str(target_record_id),
                    )
                    target_action = "deleted_row"

            # Single-shot: mark the original row reversed.
            cur.execute(
                """
                UPDATE manager_actions
                SET reversed_at = NOW(), reversed_by = %s
                WHERE id = %s
                """,
                (manager_user_id, manager_action_id),
            )

            # Audit trail: append a reverse row. before/after swap so the
            # audit log shows "we went from after_payload back to before_payload".
            reverse_before = json.dumps(after_payload) if after_payload else None
            reverse_after = json.dumps(before_payload) if before_payload else None
            cur.execute(
                """
                INSERT INTO manager_actions
                    (manager_user_id, action_type, target_table,
                     target_record_id, before_payload, after_payload,
                     source_input, approved_at)
                VALUES (%s, 'reverse', 'manager_actions', %s,
                        %s::jsonb, %s::jsonb, 'api', NOW())
                RETURNING id
                """,
                (
                    manager_user_id,
                    manager_action_id,
                    reverse_before,
                    reverse_after,
                ),
            )
            reverse_id = str(cur.fetchone()[0])

        conn.commit()
        return UndoResult(
            reverse_action_id=reverse_id,
            original_action_id=manager_action_id,
            target_table=target_table,
            target_action_taken=target_action,
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_undoable(
    manager_user_id: str, *, limit: int = UNDO_LIST_LIMIT
) -> list[dict[str, Any]]:
    """Return the last N undoable manager_actions for this operator."""
    conn = _open()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, action_type, target_table, target_record_id,
                       created_at
                FROM manager_actions
                WHERE manager_user_id = %s
                  AND reversed_at IS NULL
                  AND created_at > now() - interval '{UNDO_WINDOW_HOURS} hours'
                ORDER BY created_at DESC
                LIMIT %s
                """,  # noqa: S608
                (manager_user_id, int(limit)),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [
        {
            "id": str(r[0]),
            "action_type": r[1],
            "target_table": r[2],
            "target_record_id": str(r[3]) if r[3] else None,
            "created_at": r[4].isoformat() if r[4] else None,
        }
        for r in rows
    ]


__all__ = [
    "undo",
    "list_undoable",
    "UndoNotAllowed",
    "UndoError",
    "UndoResult",
    "UNDO_WINDOW_HOURS",
    "UNDO_LIST_LIMIT",
    "REVERSIBLE_TABLES",
]
