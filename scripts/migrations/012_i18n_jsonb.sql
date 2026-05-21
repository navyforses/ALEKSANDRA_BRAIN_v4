-- scripts/migrations/012_i18n_jsonb.sql
-- ═══════════════════════════════════════════════════════════════════════════
-- Migration 012: I18N — convert 6 family-visible TEXT columns to JSONB {en, ka}
-- and reshape briefs.sections body fields. Preserves RLS from migration 008.
-- ═══════════════════════════════════════════════════════════════════════════
--
-- Phase 6 — Bilingual System (i18n)
-- Requirements: I18N-05 (TEXT→JSONB), I18N-09 (ka = en for existing rows)
-- Source pattern: 06-RESEARCH.md "Pattern 5" (verified against PostgreSQL 15 docs)
-- Locked decisions: 06-CONTEXT.md D-04 (no inverted indexes) · D-03 (whole-JSONB reads)
--
-- Affected tables and columns:
--   aleksandra_timeline.title          TEXT NOT NULL → JSONB NOT NULL
--   aleksandra_timeline.description    TEXT nullable → JSONB nullable
--   hypotheses.title                   TEXT NOT NULL → JSONB NOT NULL
--   hypotheses.description             TEXT NOT NULL → JSONB NOT NULL
--   therapies.name                     TEXT NOT NULL → JSONB NOT NULL
--   therapies.evidence_summary         TEXT nullable → JSONB nullable
--   briefs.sections                    JSONB (TYPE unchanged) — body fields reshaped
--
-- Why RLS survives: PostgreSQL `ALTER TABLE ... ALTER COLUMN ... TYPE` does NOT
-- drop row-level-security policies; it only drops indexes whose definition
-- physically references the column's old TYPE. The 4 target columns have NO
-- indexes — verified pre-flight (see scripts/migrations/012_rollback/_preflight.txt
-- once Plan 06-07 populates it from live `\d <table>` output). Migration 008's
-- service_role-all + authenticated-read policies stay attached automatically.
--
-- Idempotency: this migration is NOT idempotent at SQL level — re-running
-- ALTER COLUMN TYPE jsonb on an already-JSONB column raises a syntax error
-- (the USING expression references `title` as if it were TEXT, but `title`
-- is JSONB the second time). Rollback path is via the .pre012.dump artifacts.
-- Plan 06-07's runbook smoke check confirms first-run success before commit.
--
-- Pre-migration rollback artifacts (created by Plan 06-07 from live data):
--   scripts/migrations/012_rollback/aleksandra_timeline.pre012.dump
--   scripts/migrations/012_rollback/hypotheses.pre012.dump
--   scripts/migrations/012_rollback/therapies.pre012.dump
--   scripts/migrations/012_rollback/briefs.pre012.dump
--   scripts/migrations/012_rollback/{aleksandra_timeline,hypotheses,therapies,briefs}.policies.pre.txt
--
-- HUMAN-APPROVAL GATE: do NOT apply until Shako has reviewed this diff and
-- runs scripts/migrations/012_runbook.md in a maintenance window.
--
-- Apply via:
--   psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f scripts/migrations/012_i18n_jsonb.sql
--
-- Full operator procedure (preflight + apply + smoke + rollback):
--   scripts/migrations/012_runbook.md

BEGIN;

-- ═══════════════════════════════════════════════════════════════════════════
-- aleksandra_timeline: title (NOT NULL), description (nullable) → JSONB
-- ═══════════════════════════════════════════════════════════════════════════
-- USING jsonb_build_object('en', col, 'ka', col) mirrors the existing English
-- text into BOTH locale slots. CONTEXT.md D-04 / SPEC I18N-09: existing rows
-- get ka = en until a future maintenance backfill phase translates them.
-- For the nullable `description`, wrap in CASE so SQL NULL stays NULL (the
-- bare jsonb_build_object would emit `{"en": null, "ka": null}` JSONB).

ALTER TABLE aleksandra_timeline
  ALTER COLUMN title TYPE jsonb
    USING jsonb_build_object('en', title, 'ka', title),
  ALTER COLUMN description TYPE jsonb
    USING CASE
      WHEN description IS NULL THEN NULL
      ELSE jsonb_build_object('en', description, 'ka', description)
    END;

-- NOT NULL on `title` is preserved automatically — jsonb_build_object never
-- returns SQL NULL when given non-NULL inputs, so every existing row produces
-- a non-NULL JSONB value and the constraint stays satisfied.

-- ═══════════════════════════════════════════════════════════════════════════
-- hypotheses: title (NOT NULL), description (NOT NULL) → JSONB
-- ═══════════════════════════════════════════════════════════════════════════

ALTER TABLE hypotheses
  ALTER COLUMN title TYPE jsonb
    USING jsonb_build_object('en', title, 'ka', title),
  ALTER COLUMN description TYPE jsonb
    USING jsonb_build_object('en', description, 'ka', description);

-- ═══════════════════════════════════════════════════════════════════════════
-- therapies: name (NOT NULL), evidence_summary (nullable) → JSONB
-- ═══════════════════════════════════════════════════════════════════════════

ALTER TABLE therapies
  ALTER COLUMN name TYPE jsonb
    USING jsonb_build_object('en', name, 'ka', name),
  ALTER COLUMN evidence_summary TYPE jsonb
    USING CASE
      WHEN evidence_summary IS NULL THEN NULL
      ELSE jsonb_build_object('en', evidence_summary, 'ka', evidence_summary)
    END;

-- ═══════════════════════════════════════════════════════════════════════════
-- briefs.sections: reshape each text body field to {en, ka}
-- ═══════════════════════════════════════════════════════════════════════════
--
-- briefs.sections is ALREADY JSONB (defined in 008_phase3_tables_and_rls.sql).
-- The existing shape is the BriefSections.to_dict() output:
--   {
--     "week_start":    "...",
--     "week_end":      "...",
--     "generated_at":  "...",
--     "summary_lines": [str, ...],
--     "papers":        [{title, citation_id, ingested_at, relevance_score}, ...],
--     "hypotheses":    [{title, status, confidence, reviewed_at, supporting}, ...],
--     "therapies":     [{name, therapy_type, aleksandra_status, evidence_in_hie}, ...],
--     "outreach":      [{subject, language, drafted_at, sent_at, contact_label, confidence}, ...],
--     "questions":     [{id, question, context, asked_at, status}, ...],
--     "citations":     [str, ...]
--   }
--
-- Phase 6 reshape: every family-visible string body becomes {en, ka}:
--   summary_lines[i]            string  → {en: line, ka: line}
--   papers[i].title             string  → {en, ka}
--   hypotheses[i].title         string  → {en, ka}
--   therapies[i].name           string  → {en, ka}
--   outreach[i].subject         string  → {en, ka}
--   questions[i].question       string  → {en, ka}
--   questions[i].context        string  → {en, ka}
--
-- Left untouched (not family-visible prose):
--   citations[]      — PMID/DOI/NCT identifiers
--   citation_id      — identifier
--   week_start / week_end / generated_at / drafted_at / sent_at / asked_at
--   reviewed_at / ingested_at
--   relevance_score / confidence
--   status / aleksandra_status / language / therapy_type / evidence_in_hie

UPDATE briefs
SET sections = (
  WITH s AS (SELECT sections AS j)
  SELECT
    jsonb_build_object(
      'week_start',   s.j->'week_start',
      'week_end',     s.j->'week_end',
      'generated_at', s.j->'generated_at',
      'summary_lines',
        COALESCE(
          (SELECT jsonb_agg(jsonb_build_object('en', x, 'ka', x))
             FROM jsonb_array_elements_text(s.j->'summary_lines') x),
          '[]'::jsonb),
      'papers',
        COALESCE(
          (SELECT jsonb_agg(elem || jsonb_build_object(
              'title', jsonb_build_object('en', elem->>'title', 'ka', elem->>'title')))
             FROM jsonb_array_elements(s.j->'papers') elem),
          '[]'::jsonb),
      'hypotheses',
        COALESCE(
          (SELECT jsonb_agg(elem || jsonb_build_object(
              'title', jsonb_build_object('en', elem->>'title', 'ka', elem->>'title')))
             FROM jsonb_array_elements(s.j->'hypotheses') elem),
          '[]'::jsonb),
      'therapies',
        COALESCE(
          (SELECT jsonb_agg(elem || jsonb_build_object(
              'name', jsonb_build_object('en', elem->>'name', 'ka', elem->>'name')))
             FROM jsonb_array_elements(s.j->'therapies') elem),
          '[]'::jsonb),
      'outreach',
        COALESCE(
          (SELECT jsonb_agg(elem || jsonb_build_object(
              'subject', jsonb_build_object('en', elem->>'subject', 'ka', elem->>'subject')))
             FROM jsonb_array_elements(s.j->'outreach') elem),
          '[]'::jsonb),
      'questions',
        COALESCE(
          (SELECT jsonb_agg(elem
              || jsonb_build_object('question', jsonb_build_object('en', elem->>'question', 'ka', elem->>'question'))
              || jsonb_build_object('context',  jsonb_build_object('en', elem->>'context',  'ka', elem->>'context')))
             FROM jsonb_array_elements(s.j->'questions') elem),
          '[]'::jsonb),
      'citations', s.j->'citations'
    )
  FROM s
);

COMMIT;

-- ═══════════════════════════════════════════════════════════════════════════
-- Post-apply smoke (run as separate queries via scripts/migrations/012_runbook.md):
--
--   SELECT pg_typeof(title) FROM aleksandra_timeline LIMIT 1;
--   -- expected: jsonb
--
--   SELECT id, title->>'en', title->>'ka' FROM aleksandra_timeline LIMIT 5;
--   -- expected: identical en/ka values (I18N-09)
--
--   SELECT polname FROM pg_policy WHERE polrelid = 'aleksandra_timeline'::regclass;
--   -- expected: aleksandra_timeline_family_read,
--   --           aleksandra_timeline_service_write,
--   --           aleksandra_timeline_service_update  (migration 002 preserved)
--
-- See scripts/migrations/012_runbook.md for the complete 7-step procedure.
