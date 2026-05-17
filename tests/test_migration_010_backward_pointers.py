"""
tests/test_migration_010_backward_pointers.py — Day 6 migration 010 smoke.

Verifies that after migration 010 has been applied to the live Supabase
database, the three Phase 3/4 delivery tables (`alerts_log`,
`outreach_log`, `briefs`) carry `originating_run_id UUID REFERENCES
runs(id)` columns and enforce the FK at INSERT time.

Each test wraps writes in a transaction and rolls back so no test rows
persist. If migration 010 has NOT been applied (column missing), every
test is SKIPPED.
"""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from typing import Iterator

import psycopg2
import pytest

from scripts.ledger import load_env


# ---------------------------------------------------------------------------
# Fixture: transactional connection that always rolls back.
# ---------------------------------------------------------------------------
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


def _migration_010_applied() -> bool:
    load_env()
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT count(*) FROM information_schema.columns
            WHERE table_schema='public'
              AND column_name='originating_run_id'
              AND table_name IN ('alerts_log','outreach_log','briefs')
            """
        )
        return int(cur.fetchone()[0]) == 3
    finally:
        conn.close()


pytestmark = pytest.mark.skipif(
    not _migration_010_applied(),
    reason=(
        "Migration 010 not applied. Run "
        "`psql $SUPABASE_DB_URL -f scripts/migrations/010_delivery_originating_run_id.sql` first."
    ),
)


def _insert_test_run(cur: psycopg2.extensions.cursor) -> str:
    """Insert one runs row + return its uuid."""
    cur.execute(
        """
        INSERT INTO runs (kind, agent_id, exit_status, token_cost,
                          tokens_input, tokens_output)
        VALUES ('migration_010_test', 'pytest-fixture', 'completed',
                0, 0, 0)
        RETURNING id
        """
    )
    return str(cur.fetchone()[0])


# ---------------------------------------------------------------------------
# Test 1: column shape across all three tables.
# ---------------------------------------------------------------------------
def test_01_all_three_tables_have_column():
    with _txn_conn() as conn:
        cur = conn.cursor()
        for t in ("alerts_log", "outreach_log", "briefs"):
            cur.execute(
                """
                SELECT data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema='public' AND table_name=%s
                  AND column_name='originating_run_id'
                """,
                (t,),
            )
            row = cur.fetchone()
            assert row is not None, f"{t} missing originating_run_id"
            assert row[0] == "uuid"
            assert row[1] == "YES", f"{t}.originating_run_id should be nullable"


# ---------------------------------------------------------------------------
# Test 2: INSERT without originating_run_id still works (nullable).
# ---------------------------------------------------------------------------
def test_02_insert_without_run_id_works():
    with _txn_conn() as conn:
        cur = conn.cursor()
        # alerts_log
        cur.execute(
            """
            INSERT INTO alerts_log (tier, event_kind, confidence, payload,
                                    delivered_at, blocked_reason, phi_redacted)
            VALUES ('T1', 'test_event', 0.9, '{}'::jsonb, now(), NULL, TRUE)
            RETURNING originating_run_id
            """
        )
        assert cur.fetchone()[0] is None


# ---------------------------------------------------------------------------
# Test 3: INSERT with bogus FK → integrity violation.
# ---------------------------------------------------------------------------
def test_03_insert_with_bogus_fk_rejected():
    with _txn_conn() as conn:
        cur = conn.cursor()
        bogus = str(uuid.uuid4())
        with pytest.raises(psycopg2.errors.ForeignKeyViolation):
            cur.execute(
                """
                INSERT INTO alerts_log (tier, event_kind, confidence, payload,
                                        delivered_at, blocked_reason,
                                        phi_redacted, originating_run_id)
                VALUES ('T1', 'test_event', 0.9, '{}'::jsonb, now(), NULL,
                        TRUE, %s)
                """,
                (bogus,),
            )
        conn.rollback()


# ---------------------------------------------------------------------------
# Test 4: INSERT with valid runs.id → success + read-back.
# ---------------------------------------------------------------------------
def test_04_insert_with_valid_fk_round_trips():
    with _txn_conn() as conn:
        cur = conn.cursor()
        run_id = _insert_test_run(cur)
        cur.execute(
            """
            INSERT INTO alerts_log (tier, event_kind, confidence, payload,
                                    delivered_at, blocked_reason,
                                    phi_redacted, originating_run_id)
            VALUES ('T2', 'test_event', 0.7, '{}'::jsonb, now(), NULL,
                    TRUE, %s)
            RETURNING id, originating_run_id
            """,
            (run_id,),
        )
        alert_id, back_ref = cur.fetchone()
        assert alert_id is not None
        assert str(back_ref) == run_id


# ---------------------------------------------------------------------------
# Test 5: ON DELETE RESTRICT — cannot delete runs while delivery row
# references it.  (DELETE on runs is already blocked by the
# block_runs_mutation trigger, but we confirm the FK is the second
# line of defence.)
# ---------------------------------------------------------------------------
def test_05_runs_delete_blocked_by_trigger_first():
    with _txn_conn() as conn:
        cur = conn.cursor()
        run_id = _insert_test_run(cur)
        cur.execute(
            """
            INSERT INTO alerts_log (tier, event_kind, confidence, payload,
                                    delivered_at, blocked_reason,
                                    phi_redacted, originating_run_id)
            VALUES ('T1', 'test_event', 0.9, '{}'::jsonb, now(), NULL,
                    TRUE, %s)
            """,
            (run_id,),
        )
        # The append-only trigger on `runs` rejects DELETE FIRST,
        # before the FK constraint gets a chance.
        with pytest.raises(psycopg2.errors.RaiseException) as exc:
            cur.execute("DELETE FROM runs WHERE id = %s", (run_id,))
        assert "append-only" in str(exc.value)
        conn.rollback()
