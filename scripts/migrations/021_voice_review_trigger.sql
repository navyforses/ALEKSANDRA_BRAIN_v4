-- ═══════════════════════════════════════════════════════════
-- Migration 021 (SQL): Phase 7.5 Rule #2 — Voice ingest review trigger
-- ═══════════════════════════════════════════════════════════
--
-- Purely additive — adds ONE function + ONE trigger to the existing
-- `intake_drops` table (created in migration 011). No ALTER on existing
-- columns, no DROP except for the trigger itself (idempotent replacement
-- pattern).
--
-- Rule #2: voice transcripts (Whisper, Telegram voice messages, ambient
-- recordings) carry irreducible STT uncertainty; the system MUST flag
-- every voice-origin intake_drops row for human review before any
-- downstream agent treats the text as authoritative. The application
-- layer (brain/intake/voice_note.py) already sets `requires_review=true`
-- voluntarily; this trigger makes the constraint physical so a future
-- code path cannot bypass it by writing `requires_review=false` directly.
--
-- IDEMPOTENT: DROP TRIGGER IF EXISTS + CREATE TRIGGER (standard
-- replacement pattern). CREATE OR REPLACE FUNCTION for the function body.
--
-- HUMAN-APPROVAL GATE: do NOT apply until Shako has run the pre-flight
-- backup (021_runbook.md §0). Migrating 011-era intake_drops rows is
-- unaffected — the trigger fires on BEFORE INSERT only, never on
-- existing rows.
--
-- Apply via:
--   psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f scripts/migrations/021_voice_review_trigger.sql

BEGIN;

-- ═══════════════════════════════════════════════════════════
-- Part 1: function — set requires_review=true for voice sources
-- ═══════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION set_voice_review_required()
RETURNS TRIGGER AS $$
BEGIN
  -- Voice STT carries irreducible uncertainty; force-flag for human review.
  -- The trigger only fires WHEN source matches a voice channel (see Part 2).
  NEW.requires_review := true;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION set_voice_review_required() IS
  'Phase 7.5 Rule #2 — voice ingest always flagged for human review. Anthropic Constitutional AI pattern: physical enforcement in the DB layer makes the rule un-bypassable from the application layer.';

-- ═══════════════════════════════════════════════════════════
-- Part 2: trigger — BEFORE INSERT on intake_drops, source IN (voice...)
-- ═══════════════════════════════════════════════════════════

DROP TRIGGER IF EXISTS voice_review_required ON intake_drops;

CREATE TRIGGER voice_review_required
  BEFORE INSERT ON intake_drops
  FOR EACH ROW
  WHEN (NEW.source IN ('voice', 'whisper', 'telegram_voice'))
  EXECUTE FUNCTION set_voice_review_required();

COMMENT ON TRIGGER voice_review_required ON intake_drops IS
  'Phase 7.5 Rule #2 enforcement — any voice-origin row gets requires_review=true at the DB layer, regardless of what the application writer passes in.';

COMMIT;

-- ═══════════════════════════════════════════════════════════
-- POST-APPLY SMOKE TEST (manual, NOT in this transaction)
-- ═══════════════════════════════════════════════════════════
--
-- 1. Confirm trigger exists:
--      psql "$SUPABASE_DB_URL" -c "\d intake_drops"
--    Expect: "Triggers:" section lists voice_review_required.
--
-- 2. Smoke-test: insert a voice row WITHOUT requires_review and confirm
--    the trigger overrides:
--      INSERT INTO intake_drops (source, payload, requires_review)
--        VALUES ('voice', '{"transcript":"smoke test"}'::jsonb, false)
--        RETURNING source, requires_review;
--    Expect: requires_review = true (trigger fired).
--
-- 3. Confirm text-source rows still honour the application value:
--      INSERT INTO intake_drops (source, payload, requires_review)
--        VALUES ('text', '{"body":"smoke test"}'::jsonb, false)
--        RETURNING source, requires_review;
--    Expect: requires_review = false (trigger did NOT fire).
--
-- 4. Cleanup: DELETE FROM intake_drops WHERE payload @> '{"transcript":"smoke test"}'::jsonb;
--             DELETE FROM intake_drops WHERE payload @> '{"body":"smoke test"}'::jsonb;
--
-- ═══════════════════════════════════════════════════════════
-- ROLLBACK (apply only if migration 021 must be reversed)
-- ═══════════════════════════════════════════════════════════
--
-- BEGIN;
-- DROP TRIGGER IF EXISTS voice_review_required ON intake_drops;
-- DROP FUNCTION IF EXISTS set_voice_review_required();
-- COMMIT;
