-- ═══════════════════════════════════════════════════════════
-- Migration 018 (SQL): Phase 7.2 SCM Persistence + Audit + Estimates
-- ═══════════════════════════════════════════════════════════
--
-- Purely additive — creates 3 new tables for the v7 causal-layer SCM
-- persistence + audit + estimate-cache:
--
--   1. scms              — head + history of every named SCM. Rows are
--                          IMMUTABLE; a "revert" or "soft-delete" appends
--                          a NEW row at version = prev_max + 1, so the
--                          full edit lineage is reconstructible from the
--                          (name, version) sequence.
--
--   2. scm_audit_log     — append-only ledger keyed on scm_id. Every
--                          create/update/revert/delete writes one row
--                          with a JSONB diff (added/removed edges/nodes).
--
--   3. causal_estimates  — cached DoWhy estimate results keyed on
--                          (scm_id, treatment, outcome, method) so
--                          re-running the same do() query is idempotent
--                          at the persistence layer.
--
-- No ALTER on existing tables. No DROP. 100% CREATE-only.
--
-- RLS pattern: matches migration 016 — service_role full + authenticated
-- read on each of the 3 tables. Same naming convention
-- (<table>_service_all + <table>_family_read).
--
-- IDEMPOTENT: every CREATE uses IF NOT EXISTS; policies are DROP+CREATE.
--
-- HUMAN-APPROVAL GATE: do NOT apply until Shako has run the pre-flight
-- backup (scripts/migrations/018_runbook.md §0). Coexists cleanly with
-- migrations 016 (belief) and 017 (Neo4j) — references neither.
--
-- Apply via:
--   psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f scripts/migrations/018_scm_tables.sql

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ═══════════════════════════════════════════════════════════
-- Part 1: scms — versioned SCM rows
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS scms (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            TEXT NOT NULL,
  version         INT NOT NULL DEFAULT 1,
  description     TEXT,
  graph_json      JSONB NOT NULL,
  created_by      TEXT NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT scms_name_version_unique UNIQUE (name, version),
  CONSTRAINT scms_version_positive CHECK (version >= 1)
);

CREATE INDEX IF NOT EXISTS scms_name_idx ON scms (name);

COMMENT ON TABLE scms IS
  'Phase 7.2 CAUSAL: versioned SCM rows. UNIQUE(name, version) enforces lineage; revert/soft-delete appends a NEW version rather than mutating in place. The latest version per name is the SCM head.';

COMMENT ON COLUMN scms.graph_json IS
  'NetworkX node-link JSON form ({directed,multigraph,graph,nodes,links}). Round-trips losslessly via brain.causal.scm_persistence.{scm_to_graph_json,graph_json_to_scm}.';

-- ═══════════════════════════════════════════════════════════
-- Part 2: scm_audit_log — append-only mutation ledger
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS scm_audit_log (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scm_id          UUID REFERENCES scms(id) ON DELETE RESTRICT,
  operation       TEXT NOT NULL,
  diff            JSONB,
  actor           TEXT NOT NULL,
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT scm_audit_log_operation_chk
    CHECK (operation IN ('create','update','delete','revert'))
);

CREATE INDEX IF NOT EXISTS scm_audit_log_scm_id_idx
  ON scm_audit_log (scm_id);
CREATE INDEX IF NOT EXISTS scm_audit_log_occurred_at_idx
  ON scm_audit_log (occurred_at DESC);

COMMENT ON TABLE scm_audit_log IS
  'Phase 7.2 CAUSAL: append-only audit ledger. Every scms mutation (create/update/revert/delete) writes one row with a JSONB diff. ON DELETE RESTRICT mirrors migration 016''s belief_evidence pattern — audit lineage is preserved even if the underlying SCM row is later replaced.';

-- ═══════════════════════════════════════════════════════════
-- Part 3: causal_estimates — DoWhy result cache
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS causal_estimates (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scm_id              UUID REFERENCES scms(id) ON DELETE RESTRICT,
  treatment           TEXT NOT NULL,
  outcome             TEXT NOT NULL,
  method              TEXT NOT NULL,
  effect              NUMERIC NOT NULL,
  ci_low              NUMERIC,
  ci_high             NUMERIC,
  refutation_passed   BOOLEAN,
  raw_result          JSONB,
  computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT causal_estimates_unique
    UNIQUE (scm_id, treatment, outcome, method)
);

CREATE INDEX IF NOT EXISTS causal_estimates_scm_id_idx
  ON causal_estimates (scm_id);
CREATE INDEX IF NOT EXISTS causal_estimates_computed_at_idx
  ON causal_estimates (computed_at DESC);

COMMENT ON TABLE causal_estimates IS
  'Phase 7.2 CAUSAL: cache of DoWhy effect estimates. UNIQUE(scm_id, treatment, outcome, method) is the idempotency key — re-running the same do() query against the same SCM head replaces the prior row via ON CONFLICT DO UPDATE.';

COMMENT ON COLUMN causal_estimates.refutation_passed IS
  'NULL = not yet refuted; TRUE/FALSE per the random_common_cause + placebo_treatment_refuter outcome (brain.causal.sensitivity.refute_estimate_all).';

-- ═══════════════════════════════════════════════════════════
-- Part 4: RLS — match migration 016 service_role + family-read pattern
-- ═══════════════════════════════════════════════════════════

ALTER TABLE scms              ENABLE ROW LEVEL SECURITY;
ALTER TABLE scm_audit_log     ENABLE ROW LEVEL SECURITY;
ALTER TABLE causal_estimates  ENABLE ROW LEVEL SECURITY;

-- scms
DROP POLICY IF EXISTS scms_service_all ON scms;
DROP POLICY IF EXISTS scms_family_read ON scms;
CREATE POLICY scms_service_all ON scms
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY scms_family_read ON scms
  FOR SELECT TO authenticated USING (true);

-- scm_audit_log
DROP POLICY IF EXISTS scm_audit_log_service_all ON scm_audit_log;
DROP POLICY IF EXISTS scm_audit_log_family_read ON scm_audit_log;
CREATE POLICY scm_audit_log_service_all ON scm_audit_log
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY scm_audit_log_family_read ON scm_audit_log
  FOR SELECT TO authenticated USING (true);

-- causal_estimates
DROP POLICY IF EXISTS causal_estimates_service_all ON causal_estimates;
DROP POLICY IF EXISTS causal_estimates_family_read ON causal_estimates;
CREATE POLICY causal_estimates_service_all ON causal_estimates
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY causal_estimates_family_read ON causal_estimates
  FOR SELECT TO authenticated USING (true);

-- ═══════════════════════════════════════════════════════════
-- Part 5: updated_at trigger on scms
-- ═══════════════════════════════════════════════════════════
-- (scm_audit_log + causal_estimates are append-only / cache; no trigger.)

CREATE OR REPLACE FUNCTION scms_touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS scms_updated_at ON scms;
CREATE TRIGGER scms_updated_at
  BEFORE UPDATE ON scms
  FOR EACH ROW EXECUTE FUNCTION scms_touch_updated_at();

COMMIT;

-- ═══════════════════════════════════════════════════════════
-- POST-APPLY SMOKE TEST (manual, NOT in this transaction)
-- ═══════════════════════════════════════════════════════════
--
-- 1. Confirm tables exist + RLS enabled:
--      psql "$SUPABASE_DB_URL" -c "\d scms"
--      psql "$SUPABASE_DB_URL" -c "\d scm_audit_log"
--      psql "$SUPABASE_DB_URL" -c "\d causal_estimates"
--    Each output must show "Row security: enabled" and the two policies.
--
-- 2. Confirm tables empty (population is Day 12+ create_scm() calls):
--      SELECT count(*) FROM scms;             -- expect 0
--      SELECT count(*) FROM scm_audit_log;    -- expect 0
--      SELECT count(*) FROM causal_estimates; -- expect 0
--
-- 3. Confirm migration 016 belief tables unaffected (regression):
--      SELECT count(*) FROM belief_dimensions;
--      SELECT count(*) FROM belief_evidence;
--      SELECT count(*) FROM belief_traces;
--    All three must match pre_018/rowcounts.csv exactly.
--
-- ═══════════════════════════════════════════════════════════
-- ROLLBACK (apply only if migration 018 must be reversed)
-- ═══════════════════════════════════════════════════════════
--
-- BEGIN;
-- DROP TRIGGER IF EXISTS scms_updated_at ON scms;
-- DROP FUNCTION IF EXISTS scms_touch_updated_at();
-- DROP TABLE IF EXISTS causal_estimates CASCADE;
-- DROP TABLE IF EXISTS scm_audit_log CASCADE;
-- DROP TABLE IF EXISTS scms CASCADE;
-- -- pgcrypto extension stays (used by migrations 016 + Phase 1-5 tables).
-- COMMIT;
