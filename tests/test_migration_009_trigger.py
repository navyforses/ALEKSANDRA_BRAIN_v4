"""
tests/test_migration_009_trigger.py — Day 6 migration 009 trigger smoke.

Verifies that after migration 009 has been applied to the live Supabase
database, the `block_runs_mutation` trigger:

  1. Still rejects DELETE on `runs`.
  2. Still rejects an ordinary UPDATE (e.g. changing `exit_status`).
  3. ALLOWS a one-shot UPDATE that sets `digest_id` from NULL to a
     UUID, leaving every other column unchanged.
  4. REJECTS a one-shot UPDATE that also changes another column in the
     same statement.
  5. REJECTS a second UPDATE attempting to overwrite an already-set
     `digest_id`.
  6. REJECTS an UPDATE that clears `digest_id` back to NULL.
  7. INSERT continues to work normally.
  8. The partial unique index `idx_runs_digest_id_unique` rejects two
     rows claiming the same digest_id.

Each test wraps its writes in a transaction and rolls back at the end so
no test rows persist. The rollback is what undoes the legitimate
one-shot UPDATE in test 3 — without it, a test-only digest_id would be
permanently glued to a test-only runs row.

If migration 009 has NOT been applied (no `digest_id` column on
`runs`), every test in this file is skipped with a clear reason. Run
the migration first via:

    psql $SUPABASE_DB_URL -f scripts/migrations/009_runs_digest_id.sql

Then run:

    pytest tests/test_migration_009_trigger.py -v
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
# Test fixture: a transactional connection that always rolls back.
# ---------------------------------------------------------------------------
@contextmanager
def _txn_conn() -> Iterator[psycopg2.extensions.connection]:
    load_env()
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        yield conn
    finally:
        # ALWAYS rollback. Tests do not commit; any inserted/updated
        # row is discarded so we never pollute the production runs
        # ledger with smoke fixtures.
        try:
            conn.rollback()
        finally:
            conn.close()


def _migration_009_applied() -> bool:
    """True if `digest_id` column exists on `runs`."""
    load_env()
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name='runs'
              AND column_name='digest_id'
            """
        )
        return cur.fetchone() is not None
    finally:
        conn.close()


pytestmark = pytest.mark.skipif(
    not _migration_009_applied(),
    reason=(
        "Migration 009 not applied. Run "
        "`psql $SUPABASE_DB_URL -f scripts/migrations/009_runs_digest_id.sql` first."
    ),
)


def _insert_test_run(cur: psycopg2.extensions.cursor) -> str:
    """Insert a single test runs row, return its uuid as string."""
    cur.execute(
        """
        INSERT INTO runs (kind, agent_id, exit_status, token_cost,
                          tokens_input, tokens_output)
        VALUES ('migration_009_test', 'pytest-fixture', 'in_progress',
                0, 0, 0)
        RETURNING id
        """
    )
    return str(cur.fetchone()[0])


# ---------------------------------------------------------------------------
# Test 1: INSERT still works.
# ---------------------------------------------------------------------------
def test_01_insert_still_works():
    with _txn_conn() as conn:
        cur = conn.cursor()
        row_id = _insert_test_run(cur)
        # Verify the row is visible to this transaction.
        cur.execute("SELECT id, kind FROM runs WHERE id = %s", (row_id,))
        row = cur.fetchone()
        assert row is not None
        assert row[1] == "migration_009_test"


# ---------------------------------------------------------------------------
# Test 2: DELETE still rejected.
# ---------------------------------------------------------------------------
def test_02_delete_rejected():
    with _txn_conn() as conn:
        cur = conn.cursor()
        row_id = _insert_test_run(cur)
        with pytest.raises(psycopg2.errors.RaiseException) as exc:
            cur.execute("DELETE FROM runs WHERE id = %s", (row_id,))
        assert "append-only" in str(exc.value)
        assert "DELETE" in str(exc.value)
        conn.rollback()  # clear the error state before the txn-rollback


# ---------------------------------------------------------------------------
# Test 3: Ordinary UPDATE (no digest_id change) rejected.
# ---------------------------------------------------------------------------
def test_03_ordinary_update_rejected():
    with _txn_conn() as conn:
        cur = conn.cursor()
        row_id = _insert_test_run(cur)
        with pytest.raises(psycopg2.errors.RaiseException) as exc:
            cur.execute(
                "UPDATE runs SET exit_status = 'completed' WHERE id = %s",
                (row_id,),
            )
        assert "append-only" in str(exc.value)
        conn.rollback()


# ---------------------------------------------------------------------------
# Test 4: One-shot digest_id NULL → uuid ALLOWED.
# ---------------------------------------------------------------------------
def test_04_one_shot_digest_id_allowed():
    with _txn_conn() as conn:
        cur = conn.cursor()
        row_id = _insert_test_run(cur)
        new_digest = str(uuid.uuid4())

        # The legitimate one-shot write.
        cur.execute(
            "UPDATE runs SET digest_id = %s WHERE id = %s",
            (new_digest, row_id),
        )
        # Verify it stuck (within the transaction).
        cur.execute("SELECT digest_id FROM runs WHERE id = %s", (row_id,))
        assert str(cur.fetchone()[0]) == new_digest


# ---------------------------------------------------------------------------
# Test 5: One-shot UPDATE that also changes another column REJECTED.
# ---------------------------------------------------------------------------
def test_05_one_shot_with_other_column_change_rejected():
    with _txn_conn() as conn:
        cur = conn.cursor()
        row_id = _insert_test_run(cur)
        new_digest = str(uuid.uuid4())
        with pytest.raises(psycopg2.errors.RaiseException) as exc:
            cur.execute(
                """
                UPDATE runs
                SET digest_id = %s, exit_status = 'completed'
                WHERE id = %s
                """,
                (new_digest, row_id),
            )
        assert "only digest_id may be set" in str(exc.value)
        conn.rollback()


# ---------------------------------------------------------------------------
# Test 6: Second UPDATE overwriting an already-set digest_id REJECTED.
# ---------------------------------------------------------------------------
def test_06_double_digest_id_assignment_rejected():
    with _txn_conn() as conn:
        cur = conn.cursor()
        row_id = _insert_test_run(cur)
        first_digest = str(uuid.uuid4())
        second_digest = str(uuid.uuid4())

        # First assignment OK.
        cur.execute(
            "UPDATE runs SET digest_id = %s WHERE id = %s",
            (first_digest, row_id),
        )

        # Second assignment rejected.
        with pytest.raises(psycopg2.errors.RaiseException) as exc:
            cur.execute(
                "UPDATE runs SET digest_id = %s WHERE id = %s",
                (second_digest, row_id),
            )
        assert "digest_id already set" in str(exc.value)
        conn.rollback()


# ---------------------------------------------------------------------------
# Test 7: Clearing digest_id back to NULL REJECTED.
# ---------------------------------------------------------------------------
def test_07_clearing_digest_id_rejected():
    with _txn_conn() as conn:
        cur = conn.cursor()
        row_id = _insert_test_run(cur)
        first_digest = str(uuid.uuid4())

        cur.execute(
            "UPDATE runs SET digest_id = %s WHERE id = %s",
            (first_digest, row_id),
        )
        # Now try to clear it.
        with pytest.raises(psycopg2.errors.RaiseException) as exc:
            cur.execute(
                "UPDATE runs SET digest_id = NULL WHERE id = %s",
                (row_id,),
            )
        assert "digest_id already set" in str(exc.value)
        conn.rollback()


# ---------------------------------------------------------------------------
# Test 8: Two rows cannot claim the same digest_id (unique index).
# ---------------------------------------------------------------------------
def test_08_digest_id_unique():
    with _txn_conn() as conn:
        cur = conn.cursor()
        row_a = _insert_test_run(cur)
        row_b = _insert_test_run(cur)
        shared = str(uuid.uuid4())

        cur.execute(
            "UPDATE runs SET digest_id = %s WHERE id = %s",
            (shared, row_a),
        )
        with pytest.raises(psycopg2.errors.UniqueViolation):
            cur.execute(
                "UPDATE runs SET digest_id = %s WHERE id = %s",
                (shared, row_b),
            )
        conn.rollback()


# ---------------------------------------------------------------------------
# Test 9: Setting digest_id to NULL when already NULL also rejected
# (defensive: the guard catches no-op-shaped UPDATEs).
# ---------------------------------------------------------------------------
def test_09_null_to_null_rejected():
    with _txn_conn() as conn:
        cur = conn.cursor()
        row_id = _insert_test_run(cur)
        with pytest.raises(psycopg2.errors.RaiseException) as exc:
            cur.execute(
                "UPDATE runs SET digest_id = NULL WHERE id = %s",
                (row_id,),
            )
        assert "digest_id stayed NULL" in str(exc.value)
        conn.rollback()
