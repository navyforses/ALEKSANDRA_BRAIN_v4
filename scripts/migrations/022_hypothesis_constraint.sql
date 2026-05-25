-- ═══════════════════════════════════════════════════════════
-- Migration 022 (SQL): Phase 7.5 Rule #9 — Hypothesis ≥3 sources constraint
-- ═══════════════════════════════════════════════════════════
--
-- Purely additive — adds ONE column (idempotent, IF NOT EXISTS) and
-- ONE CHECK constraint to the existing `hypotheses` table. The column
-- already exists in Phase 2.5+ databases; the IF NOT EXISTS clause makes
-- this migration safe on both pre-2.5 and post-2.5 schemas.
--
-- Rule #9: a hypothesis with status='confirmed' MUST cite at least 3
-- primary sources. The constraint is partial — hypotheses in any
-- non-confirmed state (e.g. 'proposed', 'investigating', 'rejected')
-- are unaffected. This matches the v7 evidence-grading philosophy: a
-- claim graduates from "interesting idea" to "confirmed" only when
-- multiple independent sources have been cited.
--
-- NOT VALID is used at constraint creation so existing rows in
-- production are not immediately validated. Shako can run
-- `ALTER TABLE hypotheses VALIDATE CONSTRAINT min_sources_when_confirmed`
-- in a follow-up window after he has audited and back-filled any rows
-- that would currently violate.
--
-- IDEMPOTENT: column ADD uses IF NOT EXISTS; constraint creation is
-- guarded by a DO-block that checks pg_constraint before ALTER.
--
-- HUMAN-APPROVAL GATE: do NOT apply until Shako has reviewed the
-- current confirmed-hypotheses row count and confirmed at least one
-- candidate row that would PASS the constraint exists (smoke test §2).
--
-- Apply via:
--   psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 \
--     -f scripts/migrations/022_hypothesis_constraint.sql

BEGIN;

-- ═══════════════════════════════════════════════════════════
-- Part 1: column — supporting_papers JSONB array (idempotent)
-- ═══════════════════════════════════════════════════════════

ALTER TABLE hypotheses
  ADD COLUMN IF NOT EXISTS supporting_papers JSONB DEFAULT '[]'::jsonb;

COMMENT ON COLUMN hypotheses.supporting_papers IS
  'Phase 7.5 Rule #9 — JSONB array of PMID strings (or compatible primary-source IDs) backing a confirmed hypothesis. Constraint min_sources_when_confirmed enforces array_length >= 3 ONLY when status = ''confirmed''.';

-- ═══════════════════════════════════════════════════════════
-- Part 2: partial CHECK — only confirmed hypotheses need ≥3 sources
-- ═══════════════════════════════════════════════════════════

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'min_sources_when_confirmed'
  ) THEN
    ALTER TABLE hypotheses
      ADD CONSTRAINT min_sources_when_confirmed
      CHECK (
        status != 'confirmed'
        OR jsonb_array_length(COALESCE(supporting_papers, '[]'::jsonb)) >= 3
      ) NOT VALID;
  END IF;
END
$$;

COMMENT ON CONSTRAINT min_sources_when_confirmed ON hypotheses IS
  'Phase 7.5 Rule #9 — confirmed hypotheses require >= 3 supporting_papers entries. NOT VALID at creation so existing rows are not immediately validated; run VALIDATE CONSTRAINT after back-fill review.';

COMMIT;

-- ═══════════════════════════════════════════════════════════
-- POST-APPLY SMOKE TEST (manual, NOT in this transaction)
-- ═══════════════════════════════════════════════════════════
--
-- 1. Confirm constraint exists:
--      psql "$SUPABASE_DB_URL" -c "\d hypotheses"
--    Expect: "Check constraints:" section lists min_sources_when_confirmed.
--
-- 2. Smoke-test (confirmed + 2 sources -> reject):
--      INSERT INTO hypotheses (title, status, supporting_papers)
--        VALUES ('smoke', 'confirmed', '["PMID:1","PMID:2"]'::jsonb);
--    Expect: ERROR — violates min_sources_when_confirmed.
--
-- 3. Smoke-test (confirmed + 3 sources -> accept):
--      INSERT INTO hypotheses (title, status, supporting_papers)
--        VALUES ('smoke', 'confirmed', '["PMID:1","PMID:2","PMID:3"]'::jsonb)
--        RETURNING id;
--    Expect: success.
--    Cleanup: DELETE FROM hypotheses WHERE title = 'smoke';
--
-- 4. Smoke-test (proposed + 0 sources -> accept):
--      INSERT INTO hypotheses (title, status, supporting_papers)
--        VALUES ('smoke2', 'proposed', '[]'::jsonb)
--        RETURNING id;
--    Expect: success. Cleanup: DELETE FROM hypotheses WHERE title='smoke2';
--
-- 5. Optional follow-up (only after Shako audits existing rows):
--      ALTER TABLE hypotheses VALIDATE CONSTRAINT min_sources_when_confirmed;
--    Will fail if any existing confirmed row has fewer than 3 supporting_papers.
--
-- ═══════════════════════════════════════════════════════════
-- ROLLBACK (apply only if migration 022 must be reversed)
-- ═══════════════════════════════════════════════════════════
--
-- BEGIN;
-- ALTER TABLE hypotheses DROP CONSTRAINT IF EXISTS min_sources_when_confirmed;
-- -- The column itself is left in place (data preservation).
-- COMMIT;
