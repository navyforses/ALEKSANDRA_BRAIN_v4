-- ═══════════════════════════════════════════════════════════
-- Migration 020 (SQL): Phase 7.4 Active Learning — Questions + Rate Log
-- ═══════════════════════════════════════════════════════════
--
-- Purely additive — creates 2 new tables for the v7 active-learning layer:
--
--   1. active_questions   — one row per EIG-ranked question sent (or
--                            queued) for the wife. Tracks render text +
--                            response + posterior delta when applied.
--
--   2. active_rate_log    — one row per ISO week with the per-week send
--                            count. Constitutional rule #11 (cap = 3)
--                            enforced via CHECK constraint and DB-level
--                            ON CONFLICT clause in record_sent().
--
-- No ALTER on existing tables. No DROP. 100% CREATE-only.
--
-- RLS pattern: matches migrations 018/019 — service_role full +
-- authenticated read on each of the 2 tables. Same naming convention
-- (<table>_service_all + <table>_family_read).
--
-- IDEMPOTENT: every CREATE uses IF NOT EXISTS; policies are DROP+CREATE.
--
-- HUMAN-APPROVAL GATE: do NOT apply until Shako has run the pre-flight
-- backup (scripts/migrations/020_runbook.md §0). Coexists cleanly with
-- migrations 016 (belief), 018 (SCM), 019 (sim) — references migration 016
-- belief_dimensions + belief_evidence FKs only.
--
-- Apply via:
--   psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f scripts/migrations/020_active_questions.sql

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ═══════════════════════════════════════════════════════════
-- Part 1: active_questions — outbound + response audit
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS active_questions (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dimension_id            INT REFERENCES belief_dimensions(id) ON DELETE RESTRICT,
  observation_type        TEXT NOT NULL,
  eig                     NUMERIC NOT NULL,
  rendered_ka             TEXT NOT NULL,
  rendered_en             TEXT NOT NULL,
  sent_at                 TIMESTAMPTZ,
  chat_id                 TEXT,
  week_iso                TEXT NOT NULL,
  response_received_at    TIMESTAMPTZ,
  response_raw            TEXT,
  response_parsed         JSONB,
  evidence_id             UUID REFERENCES belief_evidence(id) ON DELETE SET NULL,
  posterior_delta_kl      NUMERIC,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT active_questions_eig_nonneg CHECK (eig >= 0)
);

CREATE INDEX IF NOT EXISTS active_questions_week ON active_questions (week_iso);
CREATE INDEX IF NOT EXISTS active_questions_dimension_idx
  ON active_questions (dimension_id);
CREATE INDEX IF NOT EXISTS active_questions_evidence_idx
  ON active_questions (evidence_id);
CREATE INDEX IF NOT EXISTS active_questions_sent_at_idx
  ON active_questions (sent_at DESC);

COMMENT ON TABLE active_questions IS
  'Phase 7.4 ACTIVE: one row per EIG-ranked question selected for outbound. rendered_ka / rendered_en mirror the bilingual templates; response_parsed carries the ParsedResponse JSONB after wife replies; evidence_id back-links to the belief_evidence row produced by parsed_response_to_evidence().';

COMMENT ON COLUMN active_questions.eig IS
  'Expected Information Gain in nats. CHECK (eig >= 0) enforces non-negativity (numerical drift clamped at 0 in brain.active.eig).';

COMMENT ON COLUMN active_questions.posterior_delta_kl IS
  'KL divergence prior -> posterior. NULL initially; populated after update() is called on the evidence row.';

-- ═══════════════════════════════════════════════════════════
-- Part 2: active_rate_log — constitutional rule #11 enforcement
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS active_rate_log (
  week_iso        TEXT PRIMARY KEY,
  questions_sent  INT NOT NULL DEFAULT 0,
  cap             INT NOT NULL DEFAULT 3,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT active_rate_log_sent_nonneg
    CHECK (questions_sent >= 0),
  CONSTRAINT active_rate_log_within_cap
    CHECK (questions_sent <= cap),
  CONSTRAINT active_rate_log_cap_positive
    CHECK (cap > 0)
);

CREATE INDEX IF NOT EXISTS active_rate_log_updated_at_idx
  ON active_rate_log (updated_at DESC);

COMMENT ON TABLE active_rate_log IS
  'Phase 7.4 ACTIVE: weekly send counter. CHECK (questions_sent <= cap) is the DB-level enforcement of constitutional rule #11 (cap=3 per ISO week). Application-side enforcement lives in brain.active.rate_limiter.can_send_question().';

-- ═══════════════════════════════════════════════════════════
-- Part 3: RLS — match migrations 018/019 service_role + family-read pattern
-- ═══════════════════════════════════════════════════════════

ALTER TABLE active_questions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE active_rate_log    ENABLE ROW LEVEL SECURITY;

-- active_questions
DROP POLICY IF EXISTS active_questions_service_all ON active_questions;
DROP POLICY IF EXISTS active_questions_family_read ON active_questions;
CREATE POLICY active_questions_service_all ON active_questions
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY active_questions_family_read ON active_questions
  FOR SELECT TO authenticated USING (true);

-- active_rate_log (service-role only; family doesn't need to read counters)
DROP POLICY IF EXISTS active_rate_log_service_all ON active_rate_log;
CREATE POLICY active_rate_log_service_all ON active_rate_log
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ═══════════════════════════════════════════════════════════
-- Part 4: trigger — auto-stamp response_received_at when response_raw set
-- ═══════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION active_questions_stamp_received()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.response_raw IS NOT NULL
     AND (OLD.response_raw IS NULL OR OLD.response_raw <> NEW.response_raw)
     AND NEW.response_received_at IS NULL THEN
    NEW.response_received_at = NOW();
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS active_questions_response_stamp ON active_questions;
CREATE TRIGGER active_questions_response_stamp
  BEFORE UPDATE ON active_questions
  FOR EACH ROW EXECUTE FUNCTION active_questions_stamp_received();

-- ═══════════════════════════════════════════════════════════
-- Part 5: trigger — auto-stamp updated_at on active_rate_log
-- ═══════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION active_rate_log_touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS active_rate_log_updated_at ON active_rate_log;
CREATE TRIGGER active_rate_log_updated_at
  BEFORE UPDATE ON active_rate_log
  FOR EACH ROW EXECUTE FUNCTION active_rate_log_touch_updated_at();

COMMIT;

-- ═══════════════════════════════════════════════════════════
-- POST-APPLY SMOKE TEST (manual, NOT in this transaction)
-- ═══════════════════════════════════════════════════════════
--
-- 1. Confirm tables exist + RLS enabled:
--      psql "$SUPABASE_DB_URL" -c "\d active_questions"
--      psql "$SUPABASE_DB_URL" -c "\d active_rate_log"
--    Each output must show "Row security: enabled".
--
-- 2. Confirm tables empty:
--      SELECT count(*) FROM active_questions;   -- expect 0
--      SELECT count(*) FROM active_rate_log;    -- expect 0
--
-- 3. Confirm migrations 016 + 018 + 019 unaffected (regression):
--      SELECT count(*) FROM belief_dimensions;
--      SELECT count(*) FROM belief_evidence;
--      SELECT count(*) FROM scms;
--      SELECT count(*) FROM scenarios;
--
-- 4. Smoke-test cap CHECK:
--      INSERT INTO active_rate_log (week_iso, questions_sent, cap)
--        VALUES ('2026-W45', 4, 3);
--    Expect: ERROR — violates active_rate_log_within_cap. Rollback.
--
-- ═══════════════════════════════════════════════════════════
-- ROLLBACK (apply only if migration 020 must be reversed)
-- ═══════════════════════════════════════════════════════════
--
-- BEGIN;
-- DROP TRIGGER IF EXISTS active_questions_response_stamp ON active_questions;
-- DROP FUNCTION IF EXISTS active_questions_stamp_received();
-- DROP TRIGGER IF EXISTS active_rate_log_updated_at ON active_rate_log;
-- DROP FUNCTION IF EXISTS active_rate_log_touch_updated_at();
-- DROP TABLE IF EXISTS active_rate_log CASCADE;
-- DROP TABLE IF EXISTS active_questions CASCADE;
-- -- pgcrypto stays (used by migrations 016/018/019).
-- COMMIT;
