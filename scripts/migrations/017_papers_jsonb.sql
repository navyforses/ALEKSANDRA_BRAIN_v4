-- scripts/migrations/017_papers_jsonb.sql
-- ═══════════════════════════════════════════════════════════════════════════
-- Migration 017: I18N — convert papers.title + papers.abstract TEXT → JSONB
--                {en, ka} so research-paper content is bilingual at storage
--                time, not on-demand at display time.
-- ═══════════════════════════════════════════════════════════════════════════
--
-- Phase 7 prep — Bilingual Research Corpus
-- Extends the Phase 6 i18n contract (migration 012) to the `papers` table,
-- which holds raw scraped research papers from PubMed / ClinicalTrials.gov /
-- preprints. These were left English-only by Phase 6 (only derivative content
-- — hypotheses, therapies, briefs — became bilingual at that time).
--
-- Affected columns:
--   papers.title     TEXT NOT NULL → JSONB NOT NULL  (en mirrored to ka)
--   papers.abstract  TEXT nullable → JSONB nullable  (en mirrored to ka)
--
-- Existing rows: ka = en mirror (same pattern as migration 012). The actual
-- en→ka translation is performed by scripts/migrations/017_backfill_papers_ka.py
-- in a follow-up maintenance window, using the same sonnet-4-6 +
-- defensive-content-access pattern hard-won in migrations 014/015.
--
-- INDEX HANDLING:
-- Two trigram GIN indexes physically reference these columns' TEXT type:
--   idx_papers_title_trgm    ON papers USING GIN (title gin_trgm_ops)
--   idx_papers_abstract_trgm ON papers USING GIN (abstract gin_trgm_ops)
-- ALTER COLUMN TYPE jsonb would drop them automatically (a column-type change
-- always drops dependent expression indexes). We drop them explicitly first
-- so the SQL is honest about the intent, then recreate trgm indexes on the
-- ->>'en' subkey so case-insensitive substring search keeps working against
-- the English half of the corpus. (Spider/Analyzer queries hit ->>'en'.)
--
-- Why RLS survives: same reasoning as migration 012 — ALTER COLUMN TYPE does
-- NOT drop row-level-security policies, only indexes whose expression
-- physically depends on the old type.
--
-- Idempotency: NOT idempotent. Re-running ALTER COLUMN TYPE jsonb on an
-- already-JSONB column raises an error (the USING expression references
-- the column as TEXT). Pre-flight: run the smoke check in the runbook to
-- confirm pg_typeof returns `text` before applying.
--
-- HUMAN-APPROVAL GATE: do NOT apply until Shako has reviewed this diff and
-- the runbook is followed in a maintenance window.
--
-- Apply via:
--   psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f scripts/migrations/017_papers_jsonb.sql

BEGIN;

-- ═══════════════════════════════════════════════════════════════════════════
-- Step 1 — drop the trigram GIN indexes that reference the TEXT columns
-- ═══════════════════════════════════════════════════════════════════════════

DROP INDEX IF EXISTS idx_papers_title_trgm;
DROP INDEX IF EXISTS idx_papers_abstract_trgm;

-- ═══════════════════════════════════════════════════════════════════════════
-- Step 2 — papers.title (NOT NULL) + papers.abstract (nullable) → JSONB
-- ═══════════════════════════════════════════════════════════════════════════
-- jsonb_build_object mirrors the existing English text into BOTH locale slots.
-- For the nullable `abstract`, CASE preserves SQL NULL so the column stays
-- nullable in the strict sense (rather than emitting `{"en": null, "ka": null}`).

ALTER TABLE papers
  ALTER COLUMN title TYPE jsonb
    USING jsonb_build_object('en', title, 'ka', title),
  ALTER COLUMN abstract TYPE jsonb
    USING CASE
      WHEN abstract IS NULL THEN NULL
      ELSE jsonb_build_object('en', abstract, 'ka', abstract)
    END;

-- ═══════════════════════════════════════════════════════════════════════════
-- Step 3 — recreate the trigram GIN indexes on the ->>'en' subkey
-- ═══════════════════════════════════════════════════════════════════════════
-- Spider / Analyzer / search UI all query against the English text. The
-- Georgian half is for display only; nobody types Georgian search queries
-- against the research corpus (clinical jargon is English-native).

CREATE INDEX idx_papers_title_trgm
  ON papers USING GIN ((title->>'en') gin_trgm_ops);

CREATE INDEX idx_papers_abstract_trgm
  ON papers USING GIN ((abstract->>'en') gin_trgm_ops);

COMMIT;

-- Smoke check (run after apply, outside the transaction):
--   SELECT 'papers.title' AS col, pg_typeof(title) FROM papers LIMIT 1;
--   SELECT 'papers.abstract' AS col, pg_typeof(abstract) FROM papers LIMIT 1;
--   SELECT count(*) AS mirrored
--     FROM papers WHERE title->>'en' = title->>'ka';
--   SELECT count(*) AS total FROM papers;
-- Expected: both pg_typeof = jsonb, `mirrored` = `total`.
