-- 028_trials_bilingual_fulltext.sql
-- Make clinical_trials store FULL ClinicalTrials.gov data, bilingual JSONB {en, ka}
-- for the family-facing fields — exactly like papers (migrations 017 / 026 / 027).
--
-- Before: clinical_trials.title / brief_summary / eligibility_criteria are TEXT
-- (English only, and brief_summary/eligibility_criteria were only thin synthetic
-- strings the Phase A matcher built from payload_metadata). The /ka/research/trials
-- surface therefore shows English, and the cards lack the full study detail that
-- already lives in R2 (the FULL ctgov study JSON uploaded by fetch_ctgov.py).
--
-- After:
--   * title                TEXT     -> JSONB {en, ka}   (NOT NULL, en mirrored to ka)
--   * brief_summary        TEXT     -> JSONB {en, ka}   (nullable; NULL stays NULL)
--   * eligibility_criteria TEXT     -> JSONB {en, ka}   (nullable; NULL stays NULL)
--   * detailed_description JSONB    ADD (nullable; bilingual {en, ka})
--   * conditions           JSONB    ADD (nullable; array of EN condition strings)
-- The viewer's flatten(value, locale) already renders {en, ka} and falls back
-- across locales, so the Georgian site shows the ka slot once it is backfilled by
-- the matcher (scripts/trials/eligibility_matcher.py).
--
-- Idempotent-by-guard: the orchestrator (028_trials_bilingual_fulltext.py) checks
-- information_schema and SKIPS the three ALTER COLUMN TYPE statements when the
-- columns are already jsonb, so re-running is safe. The ADD COLUMN statements use
-- IF NOT EXISTS. The USING clauses mirror the existing English string into BOTH
-- locale slots for title (so the Georgian site is never blank pre-backfill) and
-- wrap nullable columns as {"en": <text>, "ka": <text>} only when non-NULL.
--
-- Why RLS survives: same reasoning as migrations 012 / 017 — ALTER COLUMN TYPE
-- does NOT drop row-level-security policies, only indexes whose expression
-- physically depends on the old type. clinical_trials has no trigram indexes on
-- these columns (see scripts/schema.sql L455-507), so there is nothing to drop /
-- recreate here.
--
-- SAFE TO APPLY LIVE: clinical_trials is fully reconstructable by re-running the
-- matcher from evidence_ledger + R2 (the backup JSON in
-- 028_trials_backup.json is an extra safety net captured before any DDL).
--
-- Apply via the orchestrator (recommended, guarded):
--   PYTHONUTF8=1 .venv/Scripts/python.exe \
--     -m scripts.migrations.028_trials_bilingual_fulltext --apply
-- or by hand:
--   psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 \
--     -f scripts/migrations/028_trials_bilingual_fulltext.sql

BEGIN;

-- ── title (NOT NULL) → JSONB {en, ka} — mirror en into ka so the Georgian site
--    is never blank before the translation backfill runs.
ALTER TABLE clinical_trials
  ALTER COLUMN title TYPE jsonb
    USING jsonb_build_object('en', title, 'ka', title);

-- ── brief_summary (nullable) → JSONB {en, ka}; CASE preserves SQL NULL.
ALTER TABLE clinical_trials
  ALTER COLUMN brief_summary TYPE jsonb
    USING CASE
            WHEN brief_summary IS NULL THEN NULL
            ELSE jsonb_build_object('en', brief_summary, 'ka', brief_summary)
          END;

-- ── eligibility_criteria (nullable) → JSONB {en, ka}; CASE preserves SQL NULL.
ALTER TABLE clinical_trials
  ALTER COLUMN eligibility_criteria TYPE jsonb
    USING CASE
            WHEN eligibility_criteria IS NULL THEN NULL
            ELSE jsonb_build_object('en', eligibility_criteria, 'ka', eligibility_criteria)
          END;

-- ── detailed_description — full ctgov descriptionModule.detailedDescription,
--    bilingual {en, ka}. New column (was not in the Phase A matcher at all).
ALTER TABLE clinical_trials
  ADD COLUMN IF NOT EXISTS detailed_description jsonb;

-- ── conditions — ctgov conditionsModule.conditions (array of EN strings). Short
--    medical terms; kept English (no translation), stored as a JSONB array.
ALTER TABLE clinical_trials
  ADD COLUMN IF NOT EXISTS conditions jsonb;

COMMIT;

-- Smoke check (run after apply, outside the transaction):
--   SELECT 'title' AS col, pg_typeof(title) FROM clinical_trials LIMIT 1;
--   SELECT 'brief_summary' AS col, pg_typeof(brief_summary) FROM clinical_trials LIMIT 1;
--   SELECT 'eligibility_criteria' AS col, pg_typeof(eligibility_criteria)
--     FROM clinical_trials LIMIT 1;
--   SELECT column_name, data_type FROM information_schema.columns
--     WHERE table_name='clinical_trials'
--       AND column_name IN ('detailed_description','conditions');
-- Expected: title/brief_summary/eligibility_criteria/detailed_description/conditions
--           all pg_typeof = jsonb.
