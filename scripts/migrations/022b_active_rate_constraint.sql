-- ═══════════════════════════════════════════════════════════
-- Migration 022b (SQL): Phase 7.5 Rule #11 — Question rate cap trigger
-- ═══════════════════════════════════════════════════════════
--
-- Purely additive — adds ONE CHECK constraint + ONE function + ONE
-- trigger to the existing `active_rate_log` table (created in migration
-- 020). The migration 020 table already carries an
-- `active_rate_log_within_cap` CHECK constraint; this migration adds a
-- second, more explicit `questions_within_cap` CHECK (duplicate in
-- spirit but with the constitutional-rule name in the error message)
-- AND a BEFORE INSERT OR UPDATE trigger that raises with errcode 23514
-- so the application layer can intercept the rule-violation specifically.
--
-- Rule #11: max 3 questions to the wife per ISO week. The cap is
-- defended at THREE layers (defense in depth):
--   1. Application: brain/active/rate_limiter.can_send_question()
--   2. DB CHECK constraint (migration 020 + this migration)
--   3. DB TRIGGER (this migration) — raises with the rule-named error
--      string so audit logs can grep for "Rule #11" specifically.
--
-- IDEMPOTENT: constraint creation is guarded by a DO-block that
-- checks pg_constraint; trigger is replaced via standard
-- DROP TRIGGER IF EXISTS / CREATE TRIGGER pattern.
--
-- HUMAN-APPROVAL GATE: do NOT apply until Shako has confirmed
-- migration 020 already applied (this migration ALTERs that table's
-- triggers list).
--
-- Apply via:
--   psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 \
--     -f scripts/migrations/022b_active_rate_constraint.sql

BEGIN;

-- ═══════════════════════════════════════════════════════════
-- Part 1: explicit CHECK constraint (idempotent)
-- ═══════════════════════════════════════════════════════════

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'questions_within_cap'
  ) THEN
    ALTER TABLE active_rate_log
      ADD CONSTRAINT questions_within_cap
      CHECK (questions_sent <= COALESCE(cap, 3));
  END IF;
END
$$;

COMMENT ON CONSTRAINT questions_within_cap ON active_rate_log IS
  'Phase 7.5 Rule #11 — duplicate of migration 020 active_rate_log_within_cap with the constitutional-rule name in the constraint identifier. Allows audit logs to grep for "Rule #11" specifically.';

-- ═══════════════════════════════════════════════════════════
-- Part 2: trigger function — raise with rule-named error string
-- ═══════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION enforce_active_rate_cap()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.questions_sent > COALESCE(NEW.cap, 3) THEN
    RAISE EXCEPTION
      'Phase 7.5 Rule #11: weekly question cap of % exceeded for week %',
      COALESCE(NEW.cap, 3),
      NEW.week_iso
      USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION enforce_active_rate_cap() IS
  'Phase 7.5 Rule #11 — explicit cap enforcer with constitutional-rule message. Complements the CHECK constraint with a human-readable raise string.';

-- ═══════════════════════════════════════════════════════════
-- Part 3: BEFORE INSERT OR UPDATE trigger
-- ═══════════════════════════════════════════════════════════

DROP TRIGGER IF EXISTS active_rate_cap_enforce ON active_rate_log;

CREATE TRIGGER active_rate_cap_enforce
  BEFORE INSERT OR UPDATE ON active_rate_log
  FOR EACH ROW
  EXECUTE FUNCTION enforce_active_rate_cap();

COMMENT ON TRIGGER active_rate_cap_enforce ON active_rate_log IS
  'Phase 7.5 Rule #11 enforcement — fires BEFORE INSERT OR UPDATE; the constraint check fires AFTER row build. Trigger catches the violation early with a clearer error.';

COMMIT;

-- ═══════════════════════════════════════════════════════════
-- POST-APPLY SMOKE TEST (manual, NOT in this transaction)
-- ═══════════════════════════════════════════════════════════
--
-- 1. Confirm constraint + trigger exist:
--      psql "$SUPABASE_DB_URL" -c "\d active_rate_log"
--    Expect both "Check constraints:" and "Triggers:" mention them.
--
-- 2. Smoke-test cap breach (UPDATE form):
--      INSERT INTO active_rate_log (week_iso, questions_sent, cap)
--        VALUES ('2026-W50-test', 0, 3)
--        ON CONFLICT (week_iso) DO NOTHING;
--      UPDATE active_rate_log SET questions_sent = 4
--        WHERE week_iso = '2026-W50-test';
--    Expect: ERROR — "Phase 7.5 Rule #11: weekly question cap of 3 exceeded".
--
-- 3. Smoke-test in-cap (UPDATE form):
--      UPDATE active_rate_log SET questions_sent = 3
--        WHERE week_iso = '2026-W50-test';
--    Expect: success.
--    Cleanup: DELETE FROM active_rate_log WHERE week_iso = '2026-W50-test';
--
-- ═══════════════════════════════════════════════════════════
-- ROLLBACK (apply only if migration 022b must be reversed)
-- ═══════════════════════════════════════════════════════════
--
-- BEGIN;
-- DROP TRIGGER IF EXISTS active_rate_cap_enforce ON active_rate_log;
-- DROP FUNCTION IF EXISTS enforce_active_rate_cap();
-- ALTER TABLE active_rate_log DROP CONSTRAINT IF EXISTS questions_within_cap;
-- -- Migration 020's active_rate_log_within_cap constraint remains.
-- COMMIT;
