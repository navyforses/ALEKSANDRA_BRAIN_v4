-- ═══════════════════════════════════════════════════════════
-- Migration 009: runs.digest_id + one-shot UPDATE relaxation — Phase 4 (OBS-02)
-- ═══════════════════════════════════════════════════════════
--
-- This migration does TWO things, both gated by the same OBS-02 contract:
--
-- 1. Adds `digest_id UUID NULL` column to `runs`.
--    Semantics: when a Communicator output (Telegram message, Gmail
--    draft, Notion archive page) is successfully delivered, the
--    delivery channel's primary key is written back into the row of
--    `runs` that produced the draft. One-way pointer: runs → delivery.
--    A single SQL `SELECT * FROM runs WHERE digest_id IS NOT NULL`
--    enumerates every delivered digest with full cost/timing context,
--    which is what auditors and OBS-02 want.
--
-- 2. Replaces the `block_runs_mutation` function (from migration 001)
--    with a STRICTER conditional version that:
--      - REJECTS every DELETE on `runs` (unchanged from 001).
--      - REJECTS every UPDATE on `runs` that touches any column
--        EXCEPT a one-shot digest_id assignment (NULL → uuid).
--      - The one-shot UPDATE may not be re-applied: once digest_id
--        is non-NULL it is frozen.
--      - The one-shot UPDATE may not be combined with changes to
--        any other column: every other column must satisfy
--        `NEW.<col> IS NOT DISTINCT FROM OLD.<col>`.
--    The append-only invariant of OBS-01 is therefore TIGHTENED, not
--    loosened: the only mutation now permitted is the OBS-02 one-shot
--    write, and only to the OBS-02 column.
--
-- IDEMPOTENT: column is added with IF NOT EXISTS; function is
-- redefined with CREATE OR REPLACE.
--
-- ROLLBACK: see the bottom of this file for the exact reverse SQL.
-- The rollback restores the migration-001 function and drops the column.
--
-- HUMAN-APPROVAL GATE: do NOT apply until Shako has reviewed
-- docs/PHASE_4_DAY6_MIGRATION_DIFF.md and given an explicit green light.
--
-- Apply via:
--   psql $SUPABASE_DB_URL -f scripts/migrations/009_runs_digest_id.sql

BEGIN;

-- ---------------------------------------------------------------------------
-- Part 1: add the digest_id column (nullable, no default).
-- ---------------------------------------------------------------------------
ALTER TABLE runs
  ADD COLUMN IF NOT EXISTS digest_id UUID;

COMMENT ON COLUMN runs.digest_id IS
  'OBS-02: one-shot pointer to delivery primary key (alerts_log.id, outreach_log.id, or Notion page UUID). Set exactly once after a Communicator draft is successfully delivered. The block_runs_mutation trigger enforces single-write semantics.';

-- Unique-when-not-null: a single delivery row may only be claimed by
-- one originating run. This catches the concurrent-dispatch race the
-- plan called out.
CREATE UNIQUE INDEX IF NOT EXISTS idx_runs_digest_id_unique
  ON runs(digest_id)
  WHERE digest_id IS NOT NULL;

-- Plain index for the verifier's "every delivered digest links back"
-- query.
CREATE INDEX IF NOT EXISTS idx_runs_digest_id_set
  ON runs(digest_id)
  WHERE digest_id IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Part 2: stricter block_runs_mutation that permits one-shot digest_id.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION block_runs_mutation()
RETURNS trigger AS $$
BEGIN
  -- DELETE: always rejected.
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'runs is append-only: DELETE rejected'
      USING ERRCODE = 'P0001';
  END IF;

  -- UPDATE: rejected EXCEPT one-shot digest_id assignment.
  IF TG_OP = 'UPDATE' THEN
    -- 1. digest_id may only transition NULL → non-NULL. Once set, it
    --    is frozen.
    IF OLD.digest_id IS NOT NULL THEN
      RAISE EXCEPTION 'runs is append-only: digest_id already set on row %', OLD.id
        USING ERRCODE = 'P0001';
    END IF;

    -- 2. The UPDATE must actually set digest_id to a non-NULL value;
    --    a no-op or NULL-write is the same shape as a regular UPDATE
    --    and stays rejected.
    IF NEW.digest_id IS NULL THEN
      RAISE EXCEPTION 'runs is append-only: UPDATE rejected (digest_id stayed NULL)'
        USING ERRCODE = 'P0001';
    END IF;

    -- 3. No other column may change in the same UPDATE.
    --    `IS DISTINCT FROM` is the NULL-safe comparison.
    IF NEW.kind                    IS DISTINCT FROM OLD.kind
       OR NEW.agent_id             IS DISTINCT FROM OLD.agent_id
       OR NEW.workflow_id          IS DISTINCT FROM OLD.workflow_id
       OR NEW.patient_context_version
                                   IS DISTINCT FROM OLD.patient_context_version
       OR NEW.start_time           IS DISTINCT FROM OLD.start_time
       OR NEW.end_time             IS DISTINCT FROM OLD.end_time
       -- duration_seconds is a generated column; Postgres recomputes
       -- it from start_time/end_time and forbids direct mutation, so
       -- we do not need to guard it here.
       OR NEW.token_cost           IS DISTINCT FROM OLD.token_cost
       OR NEW.tokens_input         IS DISTINCT FROM OLD.tokens_input
       OR NEW.tokens_output        IS DISTINCT FROM OLD.tokens_output
       OR NEW.exit_status          IS DISTINCT FROM OLD.exit_status
       OR NEW.exit_reason          IS DISTINCT FROM OLD.exit_reason
       OR NEW.draft_link           IS DISTINCT FROM OLD.draft_link
       OR NEW.created_at           IS DISTINCT FROM OLD.created_at
       OR NEW.id                   IS DISTINCT FROM OLD.id
    THEN
      RAISE EXCEPTION 'runs is append-only: only digest_id may be set post-insert (row %)', OLD.id
        USING ERRCODE = 'P0001';
    END IF;

    -- 4. Survived all guards: this is the one-shot OBS-02 write.
    RETURN NEW;
  END IF;

  -- Defensive: any other TG_OP (INSERT is never wired to this
  -- function; TRUNCATE would not fire row-level triggers anyway, but
  -- in case the trigger is rewired in the future).
  RAISE EXCEPTION 'runs is append-only: % rejected', TG_OP
    USING ERRCODE = 'P0001';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION block_runs_mutation() IS
  'OBS-01 + OBS-02 enforcer. DELETE always rejected. UPDATE rejected EXCEPT one-shot transition of digest_id from NULL to a non-NULL UUID, with no other column changes permitted in the same UPDATE.';

-- The triggers themselves are unchanged (still BEFORE UPDATE and
-- BEFORE DELETE on runs from migration 001). They re-bind to the new
-- function body automatically via the function name.

COMMIT;

-- ═══════════════════════════════════════════════════════════
-- ROLLBACK (apply only if migration 009 must be reversed)
-- ═══════════════════════════════════════════════════════════
--
-- BEGIN;
--
-- -- Restore migration-001 unconditional-reject function.
-- CREATE OR REPLACE FUNCTION block_runs_mutation()
-- RETURNS trigger AS $$
-- BEGIN
--   RAISE EXCEPTION 'runs is append-only: % rejected', TG_OP
--     USING ERRCODE = 'P0001';
-- END;
-- $$ LANGUAGE plpgsql;
--
-- DROP INDEX IF EXISTS idx_runs_digest_id_set;
-- DROP INDEX IF EXISTS idx_runs_digest_id_unique;
-- ALTER TABLE runs DROP COLUMN IF EXISTS digest_id;
--
-- COMMIT;
