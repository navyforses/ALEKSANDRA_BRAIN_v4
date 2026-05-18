-- ═══════════════════════════════════════════════════════════
-- Migration 011: Phase 5 manager_actions + intake_drops (MNG foundation)
-- ═══════════════════════════════════════════════════════════
--
-- Adds two new tables that anchor the Phase 5 BRAIN AI Manager Assistant:
--
--   1. intake_drops      — every PDF/photo/voice/email/text dropped into
--                          the BRAIN panel. PHI redaction is mandatory
--                          (CHECK phi_redacted = TRUE).
--
--   2. manager_actions   — append-only-style audit of every CRUD the
--                          manager applies on Shako's behalf. Carries
--                          before_payload + after_payload so the undo
--                          path can restore pre-state for 24 h / 30
--                          most-recent actions.
--
-- Auth model: NO Supabase Auth. The single-operator system identifies
-- Shako via a hardcoded `manager_user_id` env var. RLS still matches
-- the migration 008 pattern (service_role full + authenticated read)
-- so no second auth model is introduced.
--
-- Order matters: intake_drops MUST be created BEFORE manager_actions
-- because manager_actions.intake_drop_id has a FK pointing to it.
--
-- Append-only impact on Phase 0 runs trigger: ZERO. This migration
-- only adds NEW tables — it does not touch `runs` or the
-- `block_runs_mutation` trigger (migration 009).
--
-- IDEMPOTENT: every CREATE uses IF NOT EXISTS; CHECKs and FKs are
-- declared inline at table-create time.
--
-- HUMAN-APPROVAL GATE: do NOT apply until Shako has reviewed
-- docs/PHASE_5_DAY1_MIGRATION_DIFF.md.
--
-- Apply via:
--   psql $SUPABASE_DB_URL -f scripts/migrations/011_manager_actions_and_intake_drops.sql

BEGIN;

-- ═══════════════════════════════════════════════════════════
-- Part 1: intake_drops — every BRAIN-panel ingest
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS intake_drops (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Operator scope (hardcoded manager_user_id env var; no auth.users FK)
  manager_user_id     TEXT NOT NULL,

  -- Source classification
  input_type          TEXT NOT NULL,
  filename            TEXT,
  r2_artifact_path    TEXT,
  content_hash        TEXT,

  -- Parsed material (redacted only)
  raw_content         TEXT,
  parsed_entities     JSONB,
  proposed_actions    JSONB,

  -- Lifecycle
  status              TEXT NOT NULL DEFAULT 'pending',

  -- PHI safety gate — mandatory; matches migration 008 pattern
  phi_redacted        BOOLEAN NOT NULL DEFAULT FALSE,
  redactions_count    INTEGER NOT NULL DEFAULT 0,

  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  resolved_at         TIMESTAMPTZ,

  CONSTRAINT intake_drops_input_type_chk
    CHECK (input_type IN ('pdf','photo','voice','email','text')),
  CONSTRAINT intake_drops_status_chk
    CHECK (status IN ('pending','approved','rejected','applied','expired')),
  CONSTRAINT intake_drops_must_redact
    CHECK (phi_redacted = TRUE)
);

CREATE INDEX IF NOT EXISTS idx_intake_drops_manager_created
  ON intake_drops(manager_user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_intake_drops_pending
  ON intake_drops(manager_user_id, created_at DESC)
  WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_intake_drops_content_hash
  ON intake_drops(content_hash)
  WHERE content_hash IS NOT NULL;

COMMENT ON TABLE intake_drops IS
  'Phase 5 MNG: every multi-modal drop into the BRAIN panel. PHI redactor runs BEFORE insert (CHECK enforces phi_redacted=TRUE). content_hash backs dedup; r2_artifact_path is the cold-copy reference for PDF/photo originals.';

COMMENT ON COLUMN intake_drops.manager_user_id IS
  'Hardcoded operator id (env var MANAGER_USER_ID). No FK to auth.users — Phase 5 ships single-operator. RLS keys on this column when Supabase Auth lands in a later phase.';

COMMENT ON COLUMN intake_drops.parsed_entities IS
  'Structured JSON of entities extracted from the drop — MedicationEntity / CalendarEntity / ContactEntity / TimelineEntity / PHIBlock. Schema lives in scripts/manager/intake/_shared.py.';

ALTER TABLE intake_drops ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS intake_drops_service_all ON intake_drops;
DROP POLICY IF EXISTS intake_drops_family_read ON intake_drops;
CREATE POLICY intake_drops_service_all ON intake_drops
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY intake_drops_family_read ON intake_drops
  FOR SELECT TO authenticated USING (true);

-- ═══════════════════════════════════════════════════════════
-- Part 2: manager_actions — every BRAIN-applied CRUD
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS manager_actions (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Operator scope (hardcoded manager_user_id env var; no auth.users FK)
  manager_user_id     TEXT NOT NULL,

  -- What the manager did
  action_type         TEXT NOT NULL,
  target_table        TEXT NOT NULL,
  target_record_id    UUID,

  -- Before/after for undo
  before_payload      JSONB,
  after_payload       JSONB,

  -- Provenance
  source_input        TEXT,
  source_metadata     JSONB,
  intake_drop_id      UUID REFERENCES intake_drops(id) ON DELETE RESTRICT,

  -- Approval + undo bookkeeping
  approved_at         TIMESTAMPTZ,
  reversed_at         TIMESTAMPTZ,
  reversed_by         TEXT,

  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT manager_actions_action_type_chk
    CHECK (action_type IN (
      'create','update','draft_email','add_event','add_milestone',
      'add_contact','log_pattern','dismiss','apply_intake_drop','reverse'
    )),
  CONSTRAINT manager_actions_source_input_chk
    CHECK (source_input IS NULL OR source_input IN (
      'voice','pdf','photo','email','text','api','briefing'
    ))
);

CREATE INDEX IF NOT EXISTS idx_manager_actions_manager_created
  ON manager_actions(manager_user_id, created_at DESC);

-- Undo-window partial index: the only rows undo_query has to scan.
-- IMMUTABLE-only predicates in partial indexes: now() is volatile, so we
-- cannot include the 24-hour cutoff here. Instead, the activity_undo
-- query passes the cutoff at runtime: WHERE reversed_at IS NULL AND
-- created_at > now() - interval '24 hours' AND manager_user_id = ...
CREATE INDEX IF NOT EXISTS idx_manager_actions_undoable
  ON manager_actions(manager_user_id, created_at DESC)
  WHERE reversed_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_manager_actions_intake_drop
  ON manager_actions(intake_drop_id)
  WHERE intake_drop_id IS NOT NULL;

COMMENT ON TABLE manager_actions IS
  'Phase 5 MNG: append-only-style audit of every BRAIN-applied CRUD on Shako''s behalf. before_payload + after_payload anchor the undo path. Reversed rows stay queryable forever; reversed_at marks the moment the original was rolled back. Reverse itself writes a NEW row with action_type=''reverse''.';

COMMENT ON COLUMN manager_actions.intake_drop_id IS
  'Provenance link to the intake_drops row that produced this action (if any). Manager-only actions without a drop (e.g. dismiss, log_pattern) leave this NULL.';

COMMENT ON COLUMN manager_actions.reversed_at IS
  'NULL until undo runs on this row. After undo: the moment reversal completed. Once set, this row cannot be reverse-applied a second time (single-shot, no double-undo).';

ALTER TABLE manager_actions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS manager_actions_service_all ON manager_actions;
DROP POLICY IF EXISTS manager_actions_family_read ON manager_actions;
CREATE POLICY manager_actions_service_all ON manager_actions
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY manager_actions_family_read ON manager_actions
  FOR SELECT TO authenticated USING (true);

COMMIT;

-- ═══════════════════════════════════════════════════════════
-- POST-APPLY SMOKE TEST (manual, NOT in this transaction)
-- ═══════════════════════════════════════════════════════════
--
--   curl -s -H "apikey: $SUPABASE_ANON_KEY" \
--     "$SUPABASE_URL/rest/v1/manager_actions?select=id&limit=1"
--   # Expected: HTTP 401 OR empty body 200 — NEVER a row
--
--   curl -s -H "apikey: $SUPABASE_ANON_KEY" \
--     "$SUPABASE_URL/rest/v1/intake_drops?select=id&limit=1"
--   # Expected: HTTP 401 OR empty body 200
--
-- After both anon checks confirm no leakage, run:
--
--   .venv/Scripts/python.exe -X utf8 -m pytest tests/test_migration_011_manager.py -v
--
-- All 8 cases should PASS.
--
-- ═══════════════════════════════════════════════════════════
-- ROLLBACK (apply only if migration 011 must be reversed)
-- ═══════════════════════════════════════════════════════════
--
-- BEGIN;
--
-- DROP INDEX IF EXISTS idx_manager_actions_intake_drop;
-- DROP INDEX IF EXISTS idx_manager_actions_undoable;
-- DROP INDEX IF EXISTS idx_manager_actions_manager_created;
-- DROP TABLE IF EXISTS manager_actions;
--
-- DROP INDEX IF EXISTS idx_intake_drops_content_hash;
-- DROP INDEX IF EXISTS idx_intake_drops_pending;
-- DROP INDEX IF EXISTS idx_intake_drops_manager_created;
-- DROP TABLE IF EXISTS intake_drops;
--
-- COMMIT;
