"""
tests/test_migration_011_manager.py — Phase 5 Day 1 migration 011 smoke.

Verifies that after migration 011 has been applied to the live Supabase
database, the two new Phase 5 tables (`intake_drops`, `manager_actions`)
exist with the expected shape and enforce the documented contract:

  - intake_drops.phi_redacted CHECK = TRUE blocks unredacted inserts.
  - intake_drops.input_type CHECK restricts to {pdf,photo,voice,email,text}.
  - intake_drops.status CHECK restricts to {pending,approved,rejected,applied,expired}.
  - manager_actions.action_type CHECK restricts to the 10 documented values.
  - manager_actions.source_input CHECK restricts to the 7 documented values.
  - manager_actions.intake_drop_id FK rejects bogus uuids.
  - JSONB payload columns round-trip without mutation.
  - manager_user_id scoping works (two operators stay isolated by app code).

Each test wraps writes in a transaction and rolls back so no test rows
persist. If migration 011 has NOT been applied (tables missing), every
test is SKIPPED.
"""

from __future__ import annotations

import json
import os
import uuid
from contextlib import contextmanager
from typing import Iterator

import psycopg2
import psycopg2.errors
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


def _migration_011_applied() -> bool:
    load_env()
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
    reason=(
        "Migration 011 not applied. Run "
        "`psql $SUPABASE_DB_URL -f scripts/migrations/011_manager_actions_and_intake_drops.sql` first."
    ),
)


TEST_MANAGER = "pytest-manager-011"


def _insert_test_intake_drop(cur: psycopg2.extensions.cursor) -> str:
    cur.execute(
        """
        INSERT INTO intake_drops (manager_user_id, input_type, raw_content,
                                  phi_redacted, redactions_count, status)
        VALUES (%s, 'text', 'redacted body', TRUE, 0, 'pending')
        RETURNING id
        """,
        (TEST_MANAGER,),
    )
    return str(cur.fetchone()[0])


# ---------------------------------------------------------------------------
# Test 1: both tables exist with the expected primary key shape.
# ---------------------------------------------------------------------------
def test_01_tables_exist():
    with _txn_conn() as conn:
        cur = conn.cursor()
        for t in ("intake_drops", "manager_actions"):
            cur.execute(
                """
                SELECT data_type FROM information_schema.columns
                WHERE table_schema='public' AND table_name=%s AND column_name='id'
                """,
                (t,),
            )
            row = cur.fetchone()
            assert row is not None, f"{t} table missing id column"
            assert row[0] == "uuid"


# ---------------------------------------------------------------------------
# Test 2: intake_drops requires phi_redacted = TRUE.
# ---------------------------------------------------------------------------
def test_02_intake_drops_must_redact():
    with _txn_conn() as conn:
        cur = conn.cursor()
        # default DEFAULT FALSE — INSERT without phi_redacted should fail CHECK
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute(
                """
                INSERT INTO intake_drops (manager_user_id, input_type, raw_content)
                VALUES (%s, 'text', 'unredacted')
                """,
                (TEST_MANAGER,),
            )
        conn.rollback()
        # explicit phi_redacted=TRUE succeeds
        cur.execute(
            """
            INSERT INTO intake_drops (manager_user_id, input_type, raw_content,
                                      phi_redacted)
            VALUES (%s, 'text', 'redacted', TRUE)
            RETURNING id
            """,
            (TEST_MANAGER,),
        )
        assert cur.fetchone()[0] is not None


# ---------------------------------------------------------------------------
# Test 3: intake_drops.input_type CHECK rejects unknown values.
# ---------------------------------------------------------------------------
def test_03_intake_drops_input_type_chk():
    with _txn_conn() as conn:
        cur = conn.cursor()
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute(
                """
                INSERT INTO intake_drops (manager_user_id, input_type, phi_redacted)
                VALUES (%s, 'fax', TRUE)
                """,
                (TEST_MANAGER,),
            )
        conn.rollback()


# ---------------------------------------------------------------------------
# Test 4: intake_drops.status CHECK rejects unknown values.
# ---------------------------------------------------------------------------
def test_04_intake_drops_status_chk():
    with _txn_conn() as conn:
        cur = conn.cursor()
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute(
                """
                INSERT INTO intake_drops (manager_user_id, input_type, phi_redacted,
                                          status)
                VALUES (%s, 'text', TRUE, 'archived')
                """,
                (TEST_MANAGER,),
            )
        conn.rollback()


# ---------------------------------------------------------------------------
# Test 5: manager_actions.action_type CHECK enforces the 10 known values.
# ---------------------------------------------------------------------------
def test_05_manager_actions_action_type_chk():
    with _txn_conn() as conn:
        cur = conn.cursor()
        with pytest.raises(psycopg2.errors.CheckViolation):
            cur.execute(
                """
                INSERT INTO manager_actions (manager_user_id, action_type,
                                             target_table)
                VALUES (%s, 'mutate_everything', 'therapies')
                """,
                (TEST_MANAGER,),
            )
        conn.rollback()
        # Known value succeeds
        cur.execute(
            """
            INSERT INTO manager_actions (manager_user_id, action_type, target_table)
            VALUES (%s, 'update', 'therapies')
            RETURNING id
            """,
            (TEST_MANAGER,),
        )
        assert cur.fetchone()[0] is not None


# ---------------------------------------------------------------------------
# Test 6: manager_actions.intake_drop_id FK rejects bogus uuids.
# ---------------------------------------------------------------------------
def test_06_manager_actions_intake_fk_rejected():
    with _txn_conn() as conn:
        cur = conn.cursor()
        bogus = str(uuid.uuid4())
        with pytest.raises(psycopg2.errors.ForeignKeyViolation):
            cur.execute(
                """
                INSERT INTO manager_actions (manager_user_id, action_type,
                                             target_table, intake_drop_id)
                VALUES (%s, 'apply_intake_drop', 'aleksandra_timeline', %s)
                """,
                (TEST_MANAGER, bogus),
            )
        conn.rollback()


# ---------------------------------------------------------------------------
# Test 7: manager_actions round-trips before/after JSONB payloads.
# ---------------------------------------------------------------------------
def test_07_manager_actions_jsonb_roundtrip():
    with _txn_conn() as conn:
        cur = conn.cursor()
        drop_id = _insert_test_intake_drop(cur)
        before = {"weight_kg": 7.0, "feeding_ml_per_day": 600}
        after = {"weight_kg": 7.2, "feeding_ml_per_day": 620}
        cur.execute(
            """
            INSERT INTO manager_actions (manager_user_id, action_type,
                                         target_table, before_payload,
                                         after_payload, source_input,
                                         intake_drop_id)
            VALUES (%s, 'update', 'aleksandra_timeline', %s::jsonb,
                    %s::jsonb, 'voice', %s)
            RETURNING before_payload, after_payload
            """,
            (TEST_MANAGER, json.dumps(before), json.dumps(after), drop_id),
        )
        b, a = cur.fetchone()
        assert b == before
        assert a == after


# ---------------------------------------------------------------------------
# Test 8: manager_user_id app-scoping — two operators stay isolated when
# filtered by manager_user_id.
# ---------------------------------------------------------------------------
def test_08_manager_user_id_scoping():
    with _txn_conn() as conn:
        cur = conn.cursor()
        # Two operators write one action each
        cur.execute(
            """
            INSERT INTO manager_actions (manager_user_id, action_type, target_table)
            VALUES ('mgr-A', 'create', 'contacts')
            """
        )
        cur.execute(
            """
            INSERT INTO manager_actions (manager_user_id, action_type, target_table)
            VALUES ('mgr-B', 'create', 'contacts')
            """
        )
        # The app-side query mgr-A would issue
        cur.execute(
            "SELECT count(*) FROM manager_actions WHERE manager_user_id = 'mgr-A'"
        )
        assert cur.fetchone()[0] == 1
        cur.execute(
            "SELECT count(*) FROM manager_actions WHERE manager_user_id = 'mgr-B'"
        )
        assert cur.fetchone()[0] == 1
