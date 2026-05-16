-- ═══════════════════════════════════════════════════════════
-- Migration 008: Phase 3 tables + base-schema RLS tighten
-- ═══════════════════════════════════════════════════════════
--
-- This migration does three things:
--
-- 1. Tightens RLS on the ten base tables defined in scripts/schema.sql.
--    The pre-existing policy `"Service role full access" FOR ALL USING (true)`
--    has no `TO` clause, so it applies to PUBLIC (including the anon role).
--    Replaces each with two correctly-scoped policies: service-role full
--    access + authenticated read. Mirrors the pattern from migrations
--    001/003/004/005.
--    Affected tables: papers, therapies, pathways, brain_regions,
--    hypotheses, contacts, relationships, clinical_trials, ingestion_log,
--    discovery_reports.
--
-- 2. Adds three new Phase 3 tables: outreach_log, alerts_log, briefs.
--    Every row in each requires `phi_redacted = true` via CHECK constraint
--    so a buggy app cannot persist a non-redacted communicator output.
--
-- 3. Extends `contacts` with progressive-reveal consent flags + outreach
--    bookkeeping fields (consent_full_name, consent_doctor_names,
--    consent_hospital_names, outreach_language, last_contacted_at,
--    outreach_count).
--
-- IDEMPOTENT: every CREATE uses IF NOT EXISTS or DROP IF EXISTS first.
--
-- Apply via: psql $SUPABASE_DB_URL -f scripts/migrations/008_phase3_tables_and_rls.sql
--
-- NOTE: This migration must NOT run until Shako has reviewed the SQL diff.
-- Phase 3 Manager protocol requires explicit human-OK gate before psql.

BEGIN;

-- ═══════════════════════════════════════════════════════════
-- Part 1: RLS tighten on ten base-schema tables
-- ═══════════════════════════════════════════════════════════
--
-- Pattern per table:
--   DROP POLICY "Service role full access" ON <t>;
--   CREATE POLICY <t>_service_all ON <t> FOR ALL TO service_role ...;
--   CREATE POLICY <t>_family_read ON <t> FOR SELECT TO authenticated ...;

-- papers
DROP POLICY IF EXISTS "Service role full access" ON papers;
DROP POLICY IF EXISTS papers_service_all ON papers;
DROP POLICY IF EXISTS papers_family_read ON papers;
CREATE POLICY papers_service_all ON papers
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY papers_family_read ON papers
  FOR SELECT TO authenticated USING (true);

-- therapies
DROP POLICY IF EXISTS "Service role full access" ON therapies;
DROP POLICY IF EXISTS therapies_service_all ON therapies;
DROP POLICY IF EXISTS therapies_family_read ON therapies;
CREATE POLICY therapies_service_all ON therapies
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY therapies_family_read ON therapies
  FOR SELECT TO authenticated USING (true);

-- pathways
DROP POLICY IF EXISTS "Service role full access" ON pathways;
DROP POLICY IF EXISTS pathways_service_all ON pathways;
DROP POLICY IF EXISTS pathways_family_read ON pathways;
CREATE POLICY pathways_service_all ON pathways
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY pathways_family_read ON pathways
  FOR SELECT TO authenticated USING (true);

-- brain_regions
DROP POLICY IF EXISTS "Service role full access" ON brain_regions;
DROP POLICY IF EXISTS brain_regions_service_all ON brain_regions;
DROP POLICY IF EXISTS brain_regions_family_read ON brain_regions;
CREATE POLICY brain_regions_service_all ON brain_regions
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY brain_regions_family_read ON brain_regions
  FOR SELECT TO authenticated USING (true);

-- hypotheses
DROP POLICY IF EXISTS "Service role full access" ON hypotheses;
DROP POLICY IF EXISTS hypotheses_service_all ON hypotheses;
DROP POLICY IF EXISTS hypotheses_family_read ON hypotheses;
CREATE POLICY hypotheses_service_all ON hypotheses
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY hypotheses_family_read ON hypotheses
  FOR SELECT TO authenticated USING (true);

-- contacts
DROP POLICY IF EXISTS "Service role full access" ON contacts;
DROP POLICY IF EXISTS contacts_service_all ON contacts;
DROP POLICY IF EXISTS contacts_family_read ON contacts;
CREATE POLICY contacts_service_all ON contacts
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY contacts_family_read ON contacts
  FOR SELECT TO authenticated USING (true);

-- relationships
DROP POLICY IF EXISTS "Service role full access" ON relationships;
DROP POLICY IF EXISTS relationships_service_all ON relationships;
DROP POLICY IF EXISTS relationships_family_read ON relationships;
CREATE POLICY relationships_service_all ON relationships
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY relationships_family_read ON relationships
  FOR SELECT TO authenticated USING (true);

-- clinical_trials
DROP POLICY IF EXISTS "Service role full access" ON clinical_trials;
DROP POLICY IF EXISTS clinical_trials_service_all ON clinical_trials;
DROP POLICY IF EXISTS clinical_trials_family_read ON clinical_trials;
CREATE POLICY clinical_trials_service_all ON clinical_trials
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY clinical_trials_family_read ON clinical_trials
  FOR SELECT TO authenticated USING (true);

-- ingestion_log
DROP POLICY IF EXISTS "Service role full access" ON ingestion_log;
DROP POLICY IF EXISTS ingestion_log_service_all ON ingestion_log;
DROP POLICY IF EXISTS ingestion_log_family_read ON ingestion_log;
CREATE POLICY ingestion_log_service_all ON ingestion_log
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY ingestion_log_family_read ON ingestion_log
  FOR SELECT TO authenticated USING (true);

-- discovery_reports
DROP POLICY IF EXISTS "Service role full access" ON discovery_reports;
DROP POLICY IF EXISTS discovery_reports_service_all ON discovery_reports;
DROP POLICY IF EXISTS discovery_reports_family_read ON discovery_reports;
CREATE POLICY discovery_reports_service_all ON discovery_reports
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY discovery_reports_family_read ON discovery_reports
  FOR SELECT TO authenticated USING (true);

-- ═══════════════════════════════════════════════════════════
-- Part 2: Extend contacts with consent + outreach bookkeeping
-- ═══════════════════════════════════════════════════════════

ALTER TABLE contacts
  ADD COLUMN IF NOT EXISTS consent_full_name        BOOLEAN     NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS consent_doctor_names     BOOLEAN     NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS consent_hospital_names   BOOLEAN     NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS outreach_language        TEXT        NOT NULL DEFAULT 'en',
  ADD COLUMN IF NOT EXISTS last_contacted_at        TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS outreach_count           INTEGER     NOT NULL DEFAULT 0;

COMMENT ON COLUMN contacts.consent_full_name IS
  'Phase 3 progressive-reveal: when TRUE the redactor may include "Aleksandra Jincharadze" in outreach to this contact. Default FALSE (use "A.J., 8-month-old infant with severe HIE" instead).';
COMMENT ON COLUMN contacts.consent_doctor_names IS
  'Phase 3 progressive-reveal: when TRUE the redactor may name BMC/Duke/Wisconsin clinicians in outreach to this contact. Default FALSE (use "a clinician").';
COMMENT ON COLUMN contacts.consent_hospital_names IS
  'Phase 3 progressive-reveal: when TRUE the redactor may name BMC, Duke, Wisconsin in outreach to this contact. Default FALSE (use "a U.S. hospital").';
COMMENT ON COLUMN contacts.outreach_language IS
  'Phase 3 outreach default language for this contact. One of en, fr, ka.';

-- ═══════════════════════════════════════════════════════════
-- Part 3: outreach_log — every researcher/clinician outreach draft
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS outreach_log (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Recipient
  contact_id          UUID NOT NULL REFERENCES contacts(id) ON DELETE RESTRICT,

  -- Draft content
  subject             TEXT NOT NULL,
  body                TEXT NOT NULL,
  language            TEXT NOT NULL DEFAULT 'en',

  -- Provenance
  trigger_event_id    UUID,
  trigger_kind        TEXT,     -- 'hypothesis_confirmed', 'paper_match', 'follow_up', etc.
  evidence_refs       TEXT[],   -- PMID/DOI/NCT/URL strings

  -- Confidence + scoring
  confidence          NUMERIC(3,2),  -- 0.00 .. 1.00

  -- PHI safety gate (CHECK enforces redactor was called before insert)
  phi_redacted        BOOLEAN NOT NULL DEFAULT FALSE,
  phi_redactions_count INTEGER NOT NULL DEFAULT 0,

  -- Gmail integration
  gmail_draft_id      TEXT,            -- non-null after Gmail draft API success
  drafted_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Manual send tracking
  sent_at             TIMESTAMPTZ,     -- non-null only after Shako sends from Gmail
  sent_by             TEXT,            -- 'shako_manual' for months 1-6; later 'auto_routine'

  CONSTRAINT outreach_log_must_redact
    CHECK (phi_redacted = TRUE),
  CONSTRAINT outreach_log_language_chk
    CHECK (language IN ('en', 'fr', 'ka')),
  CONSTRAINT outreach_log_confidence_range
    CHECK (confidence IS NULL OR (confidence >= 0.00 AND confidence <= 1.00))
);

CREATE INDEX IF NOT EXISTS outreach_log_contact_idx
  ON outreach_log (contact_id, drafted_at DESC);

CREATE INDEX IF NOT EXISTS outreach_log_drafted_idx
  ON outreach_log (drafted_at DESC);

CREATE INDEX IF NOT EXISTS outreach_log_unsent_idx
  ON outreach_log (drafted_at DESC) WHERE sent_at IS NULL;

COMMENT ON TABLE outreach_log IS
  'Phase 3 CGM-04: every researcher/clinician outreach draft. Gmail draft IDs only; sent_at populates only after Shako manually sends. CHECK constraint enforces phi_redacted=TRUE at row insert time.';

ALTER TABLE outreach_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS outreach_log_service_all ON outreach_log;
DROP POLICY IF EXISTS outreach_log_family_read ON outreach_log;
CREATE POLICY outreach_log_service_all ON outreach_log
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY outreach_log_family_read ON outreach_log
  FOR SELECT TO authenticated USING (true);

-- ═══════════════════════════════════════════════════════════
-- Part 4: alerts_log — every tier router decision
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS alerts_log (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Classification
  tier              TEXT NOT NULL,
  event_kind        TEXT NOT NULL,
  confidence        NUMERIC(3,2),

  -- Payload + outcome
  payload           JSONB NOT NULL DEFAULT '{}'::jsonb,
  delivered_at      TIMESTAMPTZ,        -- non-null only when actually delivered
  blocked_reason    TEXT,                -- non-null only when tier='T0'

  -- PHI safety gate
  phi_redacted      BOOLEAN NOT NULL DEFAULT FALSE,

  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT alerts_log_tier_chk
    CHECK (tier IN ('T0','T1','T2','T3','T4')),
  CONSTRAINT alerts_log_confidence_range
    CHECK (confidence IS NULL OR (confidence >= 0.00 AND confidence <= 1.00)),
  CONSTRAINT alerts_log_must_redact
    CHECK (phi_redacted = TRUE)
);

CREATE INDEX IF NOT EXISTS alerts_log_tier_idx
  ON alerts_log (tier, COALESCE(delivered_at, created_at) DESC);

CREATE INDEX IF NOT EXISTS alerts_log_kind_idx
  ON alerts_log (event_kind, created_at DESC);

-- T1 cap enforcement index: tier_router.py queries
--   SELECT count(*) FROM alerts_log WHERE tier='T1' AND delivered_at >= today_start
-- and this partial index keeps that query cheap.
CREATE INDEX IF NOT EXISTS alerts_log_t1_today_idx
  ON alerts_log (delivered_at DESC) WHERE tier = 'T1' AND delivered_at IS NOT NULL;

COMMENT ON TABLE alerts_log IS
  'Phase 3 CGM-03: deterministic tier router output. T0 means blocked (PHI leak, banned phrase, source round-trip fail); T1-T4 are urgency tiers. tier_router.py enforces the 1/day T1 cap by counting today''s delivered T1 rows.';

ALTER TABLE alerts_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS alerts_log_service_all ON alerts_log;
DROP POLICY IF EXISTS alerts_log_family_read ON alerts_log;
CREATE POLICY alerts_log_service_all ON alerts_log
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY alerts_log_family_read ON alerts_log
  FOR SELECT TO authenticated USING (true);

-- ═══════════════════════════════════════════════════════════
-- Part 5: briefs — weekly PDF render bookkeeping
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS briefs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- One brief per week (UTC week-start)
  brief_week      DATE NOT NULL UNIQUE,

  -- R2 artifact + structured sections
  pdf_r2_path     TEXT NOT NULL,        -- e.g. briefs/2026-05-24.pdf
  sections        JSONB NOT NULL,       -- {summary, papers, hypotheses, ...}

  -- PHI safety gate
  phi_redacted    BOOLEAN NOT NULL DEFAULT FALSE,

  generated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Delivery tracking
  delivered_telegram_at TIMESTAMPTZ,
  delivered_email_at    TIMESTAMPTZ,

  CONSTRAINT briefs_must_redact
    CHECK (phi_redacted = TRUE)
);

CREATE INDEX IF NOT EXISTS briefs_week_idx
  ON briefs (brief_week DESC);

COMMENT ON TABLE briefs IS
  'Phase 3 CGM-05: weekly brief PDF bookkeeping. One row per week. sections jsonb keeps a structured copy so the brief is queryable even if the PDF is later removed from R2.';

ALTER TABLE briefs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS briefs_service_all ON briefs;
DROP POLICY IF EXISTS briefs_family_read ON briefs;
CREATE POLICY briefs_service_all ON briefs
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY briefs_family_read ON briefs
  FOR SELECT TO authenticated USING (true);

COMMIT;

-- ═══════════════════════════════════════════════════════════
-- POST-APPLY SMOKE TEST (manual, NOT in this transaction)
-- ═══════════════════════════════════════════════════════════
-- After psql -f finishes, run from a shell:
--
--   curl -s -H "apikey: $SUPABASE_ANON_KEY" \
--     "$SUPABASE_URL/rest/v1/papers?select=id&limit=1"
--   # Expected: HTTP 401 OR empty body 200 — NEVER a row
--
--   curl -s -H "apikey: $SUPABASE_ANON_KEY" \
--     "$SUPABASE_URL/rest/v1/contacts?select=id&limit=1"
--   # Expected: HTTP 401 OR empty body 200
--
--   curl -s -H "apikey: $SUPABASE_ANON_KEY" \
--     "$SUPABASE_URL/rest/v1/hypotheses?select=id&limit=1"
--   # Expected: HTTP 401 OR empty body 200
--
--   curl -s -H "apikey: $SUPABASE_ANON_KEY" \
--     "$SUPABASE_URL/rest/v1/outreach_log?select=id&limit=1"
--   # Expected: HTTP 401 OR empty body 200
--
-- All four anon checks should refuse to return rows. If any returns a row,
-- the RLS tighten FAILED and Migration 008 should be rolled back via the
-- inverse migration script before continuing Phase 3.
