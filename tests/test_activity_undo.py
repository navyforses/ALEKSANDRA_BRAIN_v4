"""
tests/test_activity_undo.py — Phase 5 Day 5 undo + audit-query tests.

Live-DB tests are SKIPPED if migration 011 isn't applied. Round-trip
tests COMMIT (because undo itself is a multi-row transaction), then
hand-clean using DELETE so no test rows persist between runs.
"""

from __future__ import annotations

import os
import uuid

import psycopg2
import pytest

from scripts.ledger import load_env
from scripts.manager.activity.undo import (
    UNDO_LIST_LIMIT,
    UNDO_WINDOW_HOURS,
    UndoNotAllowed,
    list_undoable,
    undo,
)
from scripts.manager.activity.audit_query import list_recent, page
from scripts.manager.activity.log_action import log_dismiss, log_pattern
from scripts.manager.routing._shared import ProposedAction
from scripts.manager.routing.apply_action import apply as apply_action


TEST_MANAGER = f"pytest-day5-{uuid.uuid4().hex[:8]}"


def _migration_011_applied() -> bool:
    load_env()
    if not os.environ.get("SUPABASE_DB_URL"):
        return False
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT count(*) FROM information_schema.tables
            WHERE table_schema='public'
              AND table_name IN ('intake_drops','manager_actions')
            """
        )
        return int(cur.fetchone()[0]) == 2
    finally:
        conn.close()


pytestmark = pytest.mark.skipif(
    not _migration_011_applied(),
    reason="Migration 011 not applied.",
)


def _open():
    load_env()
    return psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")


def _cleanup_manager(manager_user_id: str) -> None:
    """Wipe every test row this manager_user_id produced."""
    conn = _open()
    try:
        with conn.cursor() as cur:
            # Drop any timeline rows we INSERTed via apply.
            cur.execute(
                """
                DELETE FROM aleksandra_timeline
                WHERE id IN (
                    SELECT DISTINCT target_record_id
                    FROM manager_actions
                    WHERE manager_user_id = %s
                      AND target_table = 'aleksandra_timeline'
                      AND target_record_id IS NOT NULL
                )
                """,
                (manager_user_id,),
            )
            cur.execute(
                "DELETE FROM manager_actions WHERE manager_user_id = %s",
                (manager_user_id,),
            )
            cur.execute(
                "DELETE FROM intake_drops WHERE manager_user_id = %s",
                (manager_user_id,),
            )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def _per_test_cleanup():
    yield
    _cleanup_manager(TEST_MANAGER)


# ---------------------------------------------------------------------------
# Insert -> undo deletes the row + writes reverse audit row
# ---------------------------------------------------------------------------
def test_undo_add_event_deletes_timeline_row_and_writes_reverse():
    action = ProposedAction(
        action_type="add_event",
        target_table="aleksandra_timeline",
        target_record_id=None,
        before_payload=None,
        after_payload={
            "event_date": "2026-06-20",
            "event_type": "appointment",
            "title": "pytest day5 event",
            "description": "to be reversed",
        },
        confidence=0.95,
        auto_execute=True,
        rationale="t",
        source_entity_kind="calendar",
    )
    applied = apply_action(action, manager_user_id=TEST_MANAGER)
    res = undo(applied.manager_action_id, manager_user_id=TEST_MANAGER)
    assert res.target_action_taken == "deleted_row"
    assert res.target_table == "aleksandra_timeline"

    # Confirm the timeline row is gone
    conn = _open()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM aleksandra_timeline WHERE id=%s",
            (applied.target_record_id,),
        )
        assert cur.fetchone()[0] == 0
        # Original action row should be reversed
        cur.execute(
            "SELECT reversed_at, reversed_by FROM manager_actions WHERE id=%s",
            (applied.manager_action_id,),
        )
        rev_at, rev_by = cur.fetchone()
        assert rev_at is not None
        assert rev_by == TEST_MANAGER
        # Reverse audit row exists
        cur.execute(
            "SELECT action_type, target_record_id FROM manager_actions WHERE id=%s",
            (res.reverse_action_id,),
        )
        atype, trid = cur.fetchone()
        assert atype == "reverse"
        assert str(trid) == applied.manager_action_id
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Double-undo refused
# ---------------------------------------------------------------------------
def test_double_undo_refused():
    action = ProposedAction(
        action_type="add_milestone",
        target_table="aleksandra_timeline",
        target_record_id=None,
        before_payload=None,
        after_payload={
            "event_date": "2026-06-21",
            "event_type": "observation",
            "title": "pytest day5 milestone",
        },
        confidence=0.92,
        auto_execute=True,
        rationale="t",
        source_entity_kind="timeline",
    )
    applied = apply_action(action, manager_user_id=TEST_MANAGER)
    undo(applied.manager_action_id, manager_user_id=TEST_MANAGER)
    with pytest.raises(UndoNotAllowed):
        undo(applied.manager_action_id, manager_user_id=TEST_MANAGER)


# ---------------------------------------------------------------------------
# manager_user_id scoping — undo on someone else's row refused
# ---------------------------------------------------------------------------
def test_undo_refuses_other_managers_row():
    action = ProposedAction(
        action_type="add_event",
        target_table="aleksandra_timeline",
        target_record_id=None,
        before_payload=None,
        after_payload={
            "event_date": "2026-06-22",
            "event_type": "appointment",
            "title": "pytest day5 cross-manager",
        },
        confidence=0.93,
        auto_execute=True,
        rationale="t",
        source_entity_kind="calendar",
    )
    applied = apply_action(action, manager_user_id=TEST_MANAGER)
    with pytest.raises(UndoNotAllowed):
        undo(applied.manager_action_id, manager_user_id="someone-else")


# ---------------------------------------------------------------------------
# list_undoable returns the row we just inserted
# ---------------------------------------------------------------------------
def test_list_undoable_includes_recent_action():
    action = ProposedAction(
        action_type="add_milestone",
        target_table="aleksandra_timeline",
        target_record_id=None,
        before_payload=None,
        after_payload={
            "event_date": "2026-06-23",
            "event_type": "observation",
            "title": "pytest list undoable",
        },
        confidence=0.95,
        auto_execute=True,
        rationale="t",
        source_entity_kind="timeline",
    )
    applied = apply_action(action, manager_user_id=TEST_MANAGER)
    rows = list_undoable(TEST_MANAGER, limit=5)
    assert any(r["id"] == applied.manager_action_id for r in rows)


# ---------------------------------------------------------------------------
# Audit query — list_recent + page filtering
# ---------------------------------------------------------------------------
def test_audit_query_list_recent():
    a1 = ProposedAction(
        action_type="add_event",
        target_table="aleksandra_timeline",
        target_record_id=None,
        before_payload=None,
        after_payload={
            "event_date": "2026-06-24",
            "event_type": "appointment",
            "title": "pytest audit1",
        },
        confidence=0.93,
        auto_execute=True,
        rationale="t",
        source_entity_kind="calendar",
    )
    a2 = ProposedAction(
        action_type="add_milestone",
        target_table="aleksandra_timeline",
        target_record_id=None,
        before_payload=None,
        after_payload={
            "event_date": "2026-06-25",
            "event_type": "observation",
            "title": "pytest audit2",
        },
        confidence=0.93,
        auto_execute=True,
        rationale="t",
        source_entity_kind="timeline",
    )
    apply_action(a1, manager_user_id=TEST_MANAGER)
    apply_action(a2, manager_user_id=TEST_MANAGER)

    rows = list_recent(TEST_MANAGER, limit=10)
    titles = [r["after_payload"]["title"] for r in rows if r["after_payload"]]
    assert "pytest audit1" in titles
    assert "pytest audit2" in titles

    # Filtered page
    filtered = page(TEST_MANAGER, limit=5, action_type="add_event")
    assert all(r["action_type"] == "add_event" for r in filtered)
    assert any(
        r["after_payload"] and r["after_payload"]["title"] == "pytest audit1"
        for r in filtered
    )


# ---------------------------------------------------------------------------
# log_dismiss writes audit + updates intake_drops.status
# ---------------------------------------------------------------------------
def test_log_dismiss_updates_intake_drop():
    conn = _open()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO intake_drops (manager_user_id, input_type,
                                          raw_content, phi_redacted)
                VALUES (%s, 'text', 'to dismiss', TRUE)
                RETURNING id
                """,
                (TEST_MANAGER,),
            )
            drop_id = str(cur.fetchone()[0])
        conn.commit()
    finally:
        conn.close()

    action_id = log_dismiss(
        intake_drop_id=drop_id,
        manager_user_id=TEST_MANAGER,
        reason="not relevant",
    )
    assert action_id

    conn = _open()
    try:
        cur = conn.cursor()
        cur.execute("SELECT status FROM intake_drops WHERE id=%s", (drop_id,))
        assert cur.fetchone()[0] == "rejected"
        cur.execute("SELECT action_type FROM manager_actions WHERE id=%s", (action_id,))
        assert cur.fetchone()[0] == "dismiss"
    finally:
        conn.close()


def test_log_pattern_appends_audit_row():
    action_id = log_pattern(
        manager_user_id=TEST_MANAGER,
        description="feeding has improved over 7 days",
        payload={"days": 7},
    )
    assert action_id


# ---------------------------------------------------------------------------
# Constants are within sane bounds
# ---------------------------------------------------------------------------
def test_constants_documented():
    assert UNDO_WINDOW_HOURS == 24
    assert UNDO_LIST_LIMIT == 30
