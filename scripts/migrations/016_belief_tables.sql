-- ═══════════════════════════════════════════════════════════
-- Migration 016 (SQL): Phase 7.0 Belief State Foundation
-- ═══════════════════════════════════════════════════════════
--
-- Purely additive — creates 3 new tables for the v7 digital-twin belief layer:
--
--   1. belief_dimensions  — catalog of the 13 dimensions of Aleksandra's twin
--                           (cyst_volume, brainstem, seizures, tone, eye_track,
--                            head_control, GMFCS, Bayley, feeding, respiratory,
--                            CSF_biomarkers, neuroplasticity, family_readiness).
--                           Every row MUST carry a primary-source citation
--                           (PMID / DOI / dataset URL) — Phase 7.0 hard rule #1.
--
--   2. belief_evidence    — every observation that triggers a posterior update.
--                           Includes idempotency hash so repeated ingestion of
--                           the same source/value pair is a no-op.
--
--   3. belief_traces      — posterior summaries (mean, sd, hdi, rhat, ess) for
--                           one (dimension, evidence) pair. Append-only-style.
--
-- No ALTER on existing tables. No ALTER COLUMN TYPE (Phase 6.1 incident: ALTER
-- TYPE drops policies on PG <15). 100% CREATE-only.
--
-- RLS pattern: copied from migration 008 — service_role full + authenticated
-- read. Same naming convention (<table>_service_all + <table>_family_read).
--
-- Coexists with scripts/migrations/016_restore_hypotheses.py (Phase 6.1
-- emergency data-restore, different file extension, different purpose).
--
-- IDEMPOTENT: every CREATE uses IF NOT EXISTS; policies are DROP+CREATE.
--
-- HUMAN-APPROVAL GATE: do NOT apply until Shako has run the pre-flight backup
-- (scripts/migrations/016_pre_flight_backup.sh). See 016_runbook.md.
--
-- Apply via:
--   psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f scripts/migrations/016_belief_tables.sql

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ═══════════════════════════════════════════════════════════
-- Part 1: belief_dimensions — 13-D catalog
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS belief_dimensions (
  id              SERIAL PRIMARY KEY,
  name            TEXT NOT NULL UNIQUE,
  distribution    TEXT NOT NULL,
  prior_params    JSONB NOT NULL,
  units           TEXT,
  valid_min       NUMERIC,
  valid_max       NUMERIC,
  citation        TEXT NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT belief_dimensions_distribution_chk
    CHECK (distribution IN (
      'beta','normal','poisson','categorical',
      'gamma','bernoulli','vector','exp_decay'
    )),
  CONSTRAINT belief_dimensions_citation_nonempty
    CHECK (length(citation) >= 10)
);

COMMENT ON TABLE belief_dimensions IS
  'Phase 7.0 BELIEF: catalog of the 13 dimensions of Aleksandra digital twin. citation NOT NULL + length >= 10 enforces hard rule #1 (every prior must trace to a primary source: PMID / DOI / dataset URL).';

COMMENT ON COLUMN belief_dimensions.prior_params IS
  'JSONB hyperparameters for the prior. Shape depends on `distribution`: Beta {alpha, beta}; Normal {mu, sigma}; Poisson {lambda}; Categorical {probs:[...]}; Gamma {alpha, beta}; Bernoulli {p}; Vector {mean:[...], cov:[[...]]}; ExpDecay {rate}.';

-- ═══════════════════════════════════════════════════════════
-- Part 2: belief_evidence — observations
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS belief_evidence (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dimension_id    INT NOT NULL REFERENCES belief_dimensions(id) ON DELETE RESTRICT,
  source          TEXT NOT NULL,
  source_ref      TEXT NOT NULL,
  value           JSONB NOT NULL,
  evidence_hash   TEXT NOT NULL UNIQUE,
  confidence      NUMERIC NOT NULL,
  observed_at     TIMESTAMPTZ NOT NULL,
  ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT belief_evidence_source_chk
    CHECK (source IN (
      'mri_report','voice_note','research_paper',
      'manual','tvb_sim','causal_estimate'
    )),
  CONSTRAINT belief_evidence_confidence_range
    CHECK (confidence >= 0 AND confidence <= 1)
);

CREATE INDEX IF NOT EXISTS idx_belief_evidence_dimension
  ON belief_evidence(dimension_id);

CREATE INDEX IF NOT EXISTS idx_belief_evidence_observed_at
  ON belief_evidence(observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_belief_evidence_source
  ON belief_evidence(source, observed_at DESC);

COMMENT ON TABLE belief_evidence IS
  'Phase 7.0 BELIEF: every observation that triggers a Bayesian update. evidence_hash UNIQUE makes ingestion idempotent — re-running the same parse over the same source is a no-op (Phase 7.0 verifier check #6).';

COMMENT ON COLUMN belief_evidence.evidence_hash IS
  'SHA-256 over (source, source_ref, value, observed_at). Hex string. UNIQUE constraint enforces idempotency at the evidence layer (Phase 7.0 verifier check_7_0_06).';

COMMENT ON COLUMN belief_evidence.source_ref IS
  'External reference: PMID for research_paper, R2 path for mri_report/voice_note, intake_drops.id for manual, run_id for tvb_sim/causal_estimate.';

-- ═══════════════════════════════════════════════════════════
-- Part 3: belief_traces — posterior summaries
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS belief_traces (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dimension_id    INT NOT NULL REFERENCES belief_dimensions(id) ON DELETE RESTRICT,
  evidence_id     UUID NOT NULL REFERENCES belief_evidence(id) ON DELETE RESTRICT,
  posterior_mean  NUMERIC NOT NULL,
  posterior_sd    NUMERIC NOT NULL,
  hdi_3           NUMERIC NOT NULL,
  hdi_97          NUMERIC NOT NULL,
  n_samples       INT NOT NULL,
  rhat            NUMERIC NOT NULL,
  ess_bulk        NUMERIC NOT NULL,
  arviz_summary   JSONB,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT belief_traces_sd_nonneg
    CHECK (posterior_sd >= 0),
  CONSTRAINT belief_traces_hdi_ordered
    CHECK (hdi_97 >= hdi_3),
  CONSTRAINT belief_traces_n_samples_positive
    CHECK (n_samples > 0),
  CONSTRAINT belief_traces_rhat_floor
    CHECK (rhat >= 1.0),
  CONSTRAINT belief_traces_ess_positive
    CHECK (ess_bulk > 0),
  CONSTRAINT belief_traces_dim_evidence_unique
    UNIQUE (dimension_id, evidence_id)
);

CREATE INDEX IF NOT EXISTS idx_belief_traces_dimension
  ON belief_traces(dimension_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_belief_traces_created_at
  ON belief_traces(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_belief_traces_evidence
  ON belief_traces(evidence_id);

COMMENT ON TABLE belief_traces IS
  'Phase 7.0 BELIEF: posterior summary (one row per (dimension, evidence) update). UNIQUE(dimension_id, evidence_id) enforces idempotency at the trace layer; arviz_summary holds the full ArviZ stats blob if richer diagnostics are needed downstream.';

COMMENT ON COLUMN belief_traces.rhat IS
  'Gelman-Rubin convergence diagnostic. Phase 7.0 verifier requires rhat < 1.01 across all 13 dimensions (check_7_0_05). DB-level CHECK only floors at 1.0 (the theoretical minimum).';

COMMENT ON COLUMN belief_traces.ess_bulk IS
  'Effective sample size (bulk). Phase 7.0 verifier requires ess_bulk > 400 across all 13 dimensions (check_7_0_05).';

-- ═══════════════════════════════════════════════════════════
-- Part 4: RLS — match migration 008 service_role + family-read pattern
-- ═══════════════════════════════════════════════════════════

ALTER TABLE belief_dimensions ENABLE ROW LEVEL SECURITY;
ALTER TABLE belief_evidence   ENABLE ROW LEVEL SECURITY;
ALTER TABLE belief_traces     ENABLE ROW LEVEL SECURITY;

-- belief_dimensions
DROP POLICY IF EXISTS belief_dimensions_service_all ON belief_dimensions;
DROP POLICY IF EXISTS belief_dimensions_family_read ON belief_dimensions;
CREATE POLICY belief_dimensions_service_all ON belief_dimensions
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY belief_dimensions_family_read ON belief_dimensions
  FOR SELECT TO authenticated USING (true);

-- belief_evidence
DROP POLICY IF EXISTS belief_evidence_service_all ON belief_evidence;
DROP POLICY IF EXISTS belief_evidence_family_read ON belief_evidence;
CREATE POLICY belief_evidence_service_all ON belief_evidence
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY belief_evidence_family_read ON belief_evidence
  FOR SELECT TO authenticated USING (true);

-- belief_traces
DROP POLICY IF EXISTS belief_traces_service_all ON belief_traces;
DROP POLICY IF EXISTS belief_traces_family_read ON belief_traces;
CREATE POLICY belief_traces_service_all ON belief_traces
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY belief_traces_family_read ON belief_traces
  FOR SELECT TO authenticated USING (true);

-- ═══════════════════════════════════════════════════════════
-- Part 5: updated_at trigger on belief_dimensions
-- ═══════════════════════════════════════════════════════════
-- (belief_evidence + belief_traces are append-only; no trigger needed.)

CREATE OR REPLACE FUNCTION belief_dimensions_touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS belief_dimensions_updated_at ON belief_dimensions;
CREATE TRIGGER belief_dimensions_updated_at
  BEFORE UPDATE ON belief_dimensions
  FOR EACH ROW EXECUTE FUNCTION belief_dimensions_touch_updated_at();

COMMIT;

-- ═══════════════════════════════════════════════════════════
-- POST-APPLY SMOKE TEST (manual, NOT in this transaction)
-- ═══════════════════════════════════════════════════════════
--
-- 1. Confirm tables exist + RLS enabled:
--      psql "$SUPABASE_DB_URL" -c "\d belief_dimensions"
--      psql "$SUPABASE_DB_URL" -c "\d belief_evidence"
--      psql "$SUPABASE_DB_URL" -c "\d belief_traces"
--    Each output must show "Row security: enabled" and the two policies.
--
-- 2. Confirm tables are empty (population happens Day 6+):
--      SELECT count(*) FROM belief_dimensions;  -- expect 0
--      SELECT count(*) FROM belief_evidence;    -- expect 0
--      SELECT count(*) FROM belief_traces;      -- expect 0
--
-- 3. Confirm anon can't read (RLS sanity):
--      curl -s -H "apikey: $SUPABASE_ANON_KEY" \
--        "$SUPABASE_URL/rest/v1/belief_dimensions?select=id&limit=1"
--      # Expected: HTTP 401 OR empty body 200 — NEVER a row.
--
-- 4. Confirm migration 008 base tables still healthy (regression):
--      SELECT count(*) FROM hypotheses;
--      SELECT count(*) FROM therapies;
--      SELECT count(*) FROM contacts;
--    All three should match the pre-flight rowcounts.csv from
--    .planning/backups/pre_016/.
--
-- ═══════════════════════════════════════════════════════════
-- ROLLBACK (apply only if migration 016 must be reversed)
-- ═══════════════════════════════════════════════════════════
--
-- BEGIN;
-- DROP TRIGGER IF EXISTS belief_dimensions_updated_at ON belief_dimensions;
-- DROP FUNCTION IF EXISTS belief_dimensions_touch_updated_at();
-- DROP TABLE IF EXISTS belief_traces CASCADE;
-- DROP TABLE IF EXISTS belief_evidence CASCADE;
-- DROP TABLE IF EXISTS belief_dimensions CASCADE;
-- -- pgcrypto extension stays (used by Phase 1-5 tables).
-- COMMIT;
