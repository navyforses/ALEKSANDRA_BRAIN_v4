-- ═══════════════════════════════════════════════════════════
-- Migration 019 (SQL): Phase 7.3 Simulation Engine — Scenarios + Runs + Comparisons
-- ═══════════════════════════════════════════════════════════
--
-- Purely additive — creates 3 new tables for the v7 simulation-layer
-- Studio CRUD + Monte Carlo run cache + scenario-vs-scenario comparison:
--
--   1. scenarios               — named Monte Carlo scenarios authored
--                                via Studio. Idempotency via
--                                scenario_hash UNIQUE (SHA-256 of
--                                canonical scenario JSON; collision -> the
--                                same simulation result).
--
--   2. simulation_runs         — one row per (scenario_id, engine) run.
--                                summary_json carries the aggregated
--                                ScenarioSummary (mean/sd/hdi80/hdi95
--                                per outcome per day). engine in
--                                {monte_carlo,tvb,combined}.
--
--   3. simulation_comparisons  — one row per pairwise A-vs-B compare run.
--                                delta_json + p_a_better_json carry the
--                                ScenarioComparison payload.
--
-- No ALTER on existing tables. No DROP. 100% CREATE-only.
--
-- RLS pattern: matches migration 018 — service_role full + authenticated
-- read on each of the 3 tables. Same naming convention
-- (<table>_service_all + <table>_family_read).
--
-- IDEMPOTENT: every CREATE uses IF NOT EXISTS; policies are DROP+CREATE.
--
-- HUMAN-APPROVAL GATE: do NOT apply until Shako has run the pre-flight
-- backup (scripts/migrations/019_runbook.md §0). Coexists cleanly with
-- migrations 016 (belief) and 018 (SCM) — references neither.
--
-- Apply via:
--   psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f scripts/migrations/019_sim_tables.sql

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ═══════════════════════════════════════════════════════════
-- Part 1: scenarios — Studio-authored Monte Carlo scenarios
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS scenarios (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            TEXT NOT NULL UNIQUE,
  scenario_json   JSONB NOT NULL,
  scenario_hash   TEXT NOT NULL UNIQUE,
  created_by      TEXT NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS scenarios_name_idx ON scenarios (name);
CREATE INDEX IF NOT EXISTS scenarios_scenario_hash_idx ON scenarios (scenario_hash);

COMMENT ON TABLE scenarios IS
  'Phase 7.3 SIM: Studio-authored Monte Carlo scenarios. scenario_hash UNIQUE is the idempotency key (SHA-256 of canonical scenario JSON excluding name/description/random_seed); creating a scenario whose hash already exists must return the existing row rather than insert a duplicate.';

COMMENT ON COLUMN scenarios.scenario_json IS
  'Pydantic Scenario.model_dump() payload — interventions, horizon_days, n_samples, outcomes. Round-trips losslessly via brain.sim.persistence.scenario_to_json / json_to_scenario.';

COMMENT ON COLUMN scenarios.scenario_hash IS
  'SHA-256 hash from brain.sim.scenario.compute_scenario_hash. 64-char hex. Excludes name/description/random_seed so equivalent scenarios collide.';

-- ═══════════════════════════════════════════════════════════
-- Part 2: simulation_runs — one row per (scenario, engine) execution
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS simulation_runs (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id         UUID REFERENCES scenarios(id) ON DELETE CASCADE,
  engine              TEXT NOT NULL,
  n_samples           INT,
  duration_ms_sim     INT,
  elapsed_seconds     NUMERIC,
  summary_json        JSONB NOT NULL,
  completed_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT simulation_runs_engine_chk
    CHECK (engine IN ('monte_carlo','tvb','combined')),
  CONSTRAINT simulation_runs_elapsed_nonneg
    CHECK (elapsed_seconds IS NULL OR elapsed_seconds >= 0),
  CONSTRAINT simulation_runs_n_samples_pos
    CHECK (n_samples IS NULL OR n_samples > 0)
);

CREATE INDEX IF NOT EXISTS simulation_runs_scenario_id_idx
  ON simulation_runs (scenario_id);
CREATE INDEX IF NOT EXISTS simulation_runs_completed_at_idx
  ON simulation_runs (completed_at DESC);

COMMENT ON TABLE simulation_runs IS
  'Phase 7.3 SIM: one row per Monte Carlo / TVB / combined run against a scenario. summary_json carries the aggregated ScenarioSummary (mean/sd/hdi_80/hdi_95 per outcome per day). engine in {monte_carlo,tvb,combined}. elapsed_seconds CHECK >= 0 guards against negative wall-clock writes from clock skew.';

COMMENT ON COLUMN simulation_runs.summary_json IS
  'brain.sim.aggregator.ScenarioSummary.model_dump() — scenario_hash, n_samples, horizon_days, outcomes[], summaries[OutcomeSummary], elapsed_seconds.';

-- ═══════════════════════════════════════════════════════════
-- Part 3: simulation_comparisons — pairwise scenario comparisons
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS simulation_comparisons (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_a_id     UUID REFERENCES scenarios(id) ON DELETE CASCADE,
  scenario_b_id     UUID REFERENCES scenarios(id) ON DELETE CASCADE,
  delta_json        JSONB NOT NULL,
  p_a_better_json   JSONB NOT NULL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS simulation_comparisons_scenario_a_idx
  ON simulation_comparisons (scenario_a_id);
CREATE INDEX IF NOT EXISTS simulation_comparisons_scenario_b_idx
  ON simulation_comparisons (scenario_b_id);
CREATE INDEX IF NOT EXISTS simulation_comparisons_created_at_idx
  ON simulation_comparisons (created_at DESC);

COMMENT ON TABLE simulation_comparisons IS
  'Phase 7.3 SIM: one row per (scenario_a, scenario_b) pairwise comparison. delta_json carries the per (outcome, day) mean_delta + interpretation; p_a_better_json carries the P(A better than B) probabilities. Both side IDs point at scenarios.id with ON DELETE CASCADE so deleting a scenario reaps its comparisons.';

-- ═══════════════════════════════════════════════════════════
-- Part 4: RLS — match migration 018 service_role + family-read pattern
-- ═══════════════════════════════════════════════════════════

ALTER TABLE scenarios               ENABLE ROW LEVEL SECURITY;
ALTER TABLE simulation_runs         ENABLE ROW LEVEL SECURITY;
ALTER TABLE simulation_comparisons  ENABLE ROW LEVEL SECURITY;

-- scenarios
DROP POLICY IF EXISTS scenarios_service_all ON scenarios;
DROP POLICY IF EXISTS scenarios_family_read ON scenarios;
CREATE POLICY scenarios_service_all ON scenarios
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY scenarios_family_read ON scenarios
  FOR SELECT TO authenticated USING (true);

-- simulation_runs
DROP POLICY IF EXISTS simulation_runs_service_all ON simulation_runs;
DROP POLICY IF EXISTS simulation_runs_family_read ON simulation_runs;
CREATE POLICY simulation_runs_service_all ON simulation_runs
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY simulation_runs_family_read ON simulation_runs
  FOR SELECT TO authenticated USING (true);

-- simulation_comparisons
DROP POLICY IF EXISTS simulation_comparisons_service_all ON simulation_comparisons;
DROP POLICY IF EXISTS simulation_comparisons_family_read ON simulation_comparisons;
CREATE POLICY simulation_comparisons_service_all ON simulation_comparisons
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY simulation_comparisons_family_read ON simulation_comparisons
  FOR SELECT TO authenticated USING (true);

-- ═══════════════════════════════════════════════════════════
-- Part 5: updated_at-style trigger on scenarios (idempotent)
-- ═══════════════════════════════════════════════════════════
-- scenarios has only created_at + immutable JSON; we still ship a
-- no-op-safe touch trigger to keep the pattern aligned with migration 018
-- in case a future migration adds an updated_at column.

CREATE OR REPLACE FUNCTION scenarios_touch_created_at()
RETURNS TRIGGER AS $$
BEGIN
  -- created_at is immutable on UPDATE; preserve the original row value.
  NEW.created_at = OLD.created_at;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS scenarios_created_at_immutable ON scenarios;
CREATE TRIGGER scenarios_created_at_immutable
  BEFORE UPDATE ON scenarios
  FOR EACH ROW EXECUTE FUNCTION scenarios_touch_created_at();

COMMIT;

-- ═══════════════════════════════════════════════════════════
-- POST-APPLY SMOKE TEST (manual, NOT in this transaction)
-- ═══════════════════════════════════════════════════════════
--
-- 1. Confirm tables exist + RLS enabled:
--      psql "$SUPABASE_DB_URL" -c "\d scenarios"
--      psql "$SUPABASE_DB_URL" -c "\d simulation_runs"
--      psql "$SUPABASE_DB_URL" -c "\d simulation_comparisons"
--    Each output must show "Row security: enabled" and the two policies.
--
-- 2. Confirm tables empty (population is Phase 7.3 Day 11+ save_scenario() calls):
--      SELECT count(*) FROM scenarios;              -- expect 0
--      SELECT count(*) FROM simulation_runs;        -- expect 0
--      SELECT count(*) FROM simulation_comparisons; -- expect 0
--
-- 3. Confirm migrations 016 + 018 tables unaffected (regression):
--      SELECT count(*) FROM belief_dimensions;
--      SELECT count(*) FROM scms;
--      SELECT count(*) FROM scm_audit_log;
--    All must match pre_019/rowcounts.csv exactly.
--
-- ═══════════════════════════════════════════════════════════
-- ROLLBACK (apply only if migration 019 must be reversed) — spec §5.2
-- ═══════════════════════════════════════════════════════════
--
-- BEGIN;
-- DROP TRIGGER IF EXISTS scenarios_created_at_immutable ON scenarios;
-- DROP FUNCTION IF EXISTS scenarios_touch_created_at();
-- DROP TABLE IF EXISTS simulation_comparisons CASCADE;
-- DROP TABLE IF EXISTS simulation_runs CASCADE;
-- DROP TABLE IF EXISTS scenarios CASCADE;
-- -- pgcrypto extension stays (used by migrations 016 + 018 + Phase 1-5 tables).
-- COMMIT;
