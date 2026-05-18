"""
tests/test_routing_apply.py — Phase 5 Day 4 apply_action + apply_batch tests.

All tests are transactional and roll back so no rows persist in
production. Skipped if SUPABASE_DB_URL or migration 011 is absent.
"""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from typing import Iterator

import psycopg2
import pytest

from scripts.ledger import load_env
from scripts.manager.routing._shared import ProposedAction
from scripts.manager.routing.apply_action import (
    ApplyError,
    _apply_with_cursor,
)


TEST_MANAGER = "pytest-routing-day4"


@contextmanager
def _txn_conn() -> Iterator[psycopg2.extensions.connection]:
    load_env()
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        yield conn
    finally:
        try:
            conn.rollback()
        finally:
            conn.close()


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
    reason="Migration 011 not applied (intake_drops + manager_actions absent).",
)


# ---------------------------------------------------------------------------
# add_event on aleksandra_timeline + manager_actions row appears
# ---------------------------------------------------------------------------
def test_apply_add_event_writes_timeline_and_audit_row():
    action = ProposedAction(
        action_type="add_event",
        target_table="aleksandra_timeline",
        target_record_id=None,
        before_payload=None,
        after_payload={
            "event_date": "2026-06-10",
            "event_type": "appointment",
            "title": "pytest fixture event",
            "description": "rolled-back test",
            "institution": "BMC",
        },
        confidence=0.93,
        auto_execute=True,
        rationale="test",
        source_entity_kind="calendar",
    )
    with _txn_conn() as conn:
        with conn.cursor() as cur:
            res = _apply_with_cursor(action, cur, manager_user_id=TEST_MANAGER)
            assert res.target_table == "aleksandra_timeline"
            assert res.target_record_id
            # Confirm the timeline row exists in this transaction
            cur.execute(
                "SELECT title FROM aleksandra_timeline WHERE id=%s",
                (res.target_record_id,),
            )
            assert cur.fetchone()[0] == "pytest fixture event"
            # Confirm the audit row exists
            cur.execute(
                """
                SELECT action_type, target_table, target_record_id
                FROM manager_actions WHERE id=%s
                """,
                (res.manager_action_id,),
            )
            row = cur.fetchone()
            assert row[0] == "add_event"
            assert row[1] == "aleksandra_timeline"
            assert str(row[2]) == res.target_record_id


# ---------------------------------------------------------------------------
# Disallowed target table refused
# ---------------------------------------------------------------------------
def test_apply_refuses_disallowed_target():
    action = ProposedAction(
        action_type="create",
        target_table="runs",
        target_record_id=None,
        before_payload=None,
        after_payload={"foo": "bar"},
        confidence=0.99,
        auto_execute=False,
        rationale="test",
        source_entity_kind="unknown",
    )
    with _txn_conn() as conn:
        with conn.cursor() as cur:
            with pytest.raises(ApplyError):
                _apply_with_cursor(action, cur, manager_user_id=TEST_MANAGER)


# ---------------------------------------------------------------------------
# Batch all-or-nothing rollback
# ---------------------------------------------------------------------------
def test_batch_rollback_on_failure():
    """If the second action fails, the first must roll back."""
    good = ProposedAction(
        action_type="add_event",
        target_table="aleksandra_timeline",
        target_record_id=None,
        before_payload=None,
        after_payload={
            "event_date": "2026-06-11",
            "event_type": "observation",
            "title": "batch good",
        },
        confidence=0.93,
        auto_execute=True,
        rationale="t",
        source_entity_kind="timeline",
    )
    bad = ProposedAction(
        action_type="create",
        target_table="runs",  # disallowed
        target_record_id=None,
        before_payload=None,
        after_payload={"foo": "bar"},
        confidence=0.93,
        auto_execute=False,
        rationale="t",
        source_entity_kind="unknown",
    )
    from scripts.manager.routing.apply_batch import apply_many

    res = apply_many([good, bad], manager_user_id=TEST_MANAGER)
    assert res.committed is False
    assert res.error
    assert res.results == []
    # Confirm the "good" timeline row did NOT survive
    load_env()
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM aleksandra_timeline WHERE title='batch good'")
        n = int(cur.fetchone()[0])
        assert n == 0, "rollback did not reverse the first INSERT"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# intake_drop_id provenance link survives the round-trip.
# ---------------------------------------------------------------------------
def test_apply_records_intake_drop_id():
    with _txn_conn() as conn:
        with conn.cursor() as cur:
            # Set up a fixture intake_drops row
            cur.execute(
                """
                INSERT INTO intake_drops (manager_user_id, input_type,
                                          raw_content, phi_redacted)
                VALUES (%s, 'text', 'test', TRUE)
                RETURNING id
                """,
                (TEST_MANAGER,),
            )
            drop_id = str(cur.fetchone()[0])

            action = ProposedAction(
                action_type="add_milestone",
                target_table="aleksandra_timeline",
                target_record_id=None,
                before_payload=None,
                after_payload={
                    "event_date": "2026-05-18",
                    "event_type": "observation",
                    "title": "weight 7.3 kg",
                },
                confidence=0.92,
                auto_execute=True,
                rationale="t",
                source_entity_kind="timeline",
                intake_drop_id=drop_id,
            )
            res = _apply_with_cursor(action, cur, manager_user_id=TEST_MANAGER)
            cur.execute(
                "SELECT intake_drop_id FROM manager_actions WHERE id=%s",
                (res.manager_action_id,),
            )
            assert str(cur.fetchone()[0]) == drop_id


# ---------------------------------------------------------------------------
# Bogus intake_drop_id rejected (FK from manager_actions to intake_drops)
# ---------------------------------------------------------------------------
def test_apply_bogus_intake_drop_id_rejected():
    bogus = str(uuid.uuid4())
    action = ProposedAction(
        action_type="add_event",
        target_table="aleksandra_timeline",
        target_record_id=None,
        before_payload=None,
        after_payload={
            "event_date": "2026-06-12",
            "event_type": "appointment",
            "title": "should fail",
        },
        confidence=0.93,
        auto_execute=True,
        rationale="t",
        source_entity_kind="calendar",
        intake_drop_id=bogus,
    )
    with _txn_conn() as conn:
        with conn.cursor() as cur:
            with pytest.raises(psycopg2.errors.ForeignKeyViolation):
                _apply_with_cursor(action, cur, manager_user_id=TEST_MANAGER)
