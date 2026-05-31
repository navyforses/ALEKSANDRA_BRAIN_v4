-- ═══════════════════════════════════════════════════════════
-- Migration 023 (SQL): Phase 7.5 Meta — Constitutional Overrides Table
-- ═══════════════════════════════════════════════════════════
--
-- Purely additive — creates ONE new table for the v7 constitutional
-- escape-hatch audit ledger. Every override of any of the 13 rules
-- writes one row here with rule_number, justification, actor, and
-- a 24-hour auto-expiry.
--
-- RLS pattern matches migrations 018/019/020: service_role full +
-- authenticated read. The wife-facing UI (Phase 7.6 frontend) reads
-- this table to surface active overrides; only Shako (service-role)
-- can INSERT.
--
-- IDEMPOTENT: CREATE TABLE IF NOT EXISTS; policies DROP+CREATE.
--
-- HUMAN-APPROVAL GATE: do NOT apply until Shako has confirmed the
-- pre-flight backup (023_runbook.md §0). Independent of migrations
-- 016/018/019/020 — references no existing table FKs.
--
-- Apply via:
--   psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 \
--     -f scripts/migrations/023_constitutional_overrides.sql

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ═══════════════════════════════════════════════════════════
-- Part 1: table
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS constitutional_overrides (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_number         INT NOT NULL,
  reason              TEXT NOT NULL,
  overridden_by       TEXT NOT NULL,
  expires_at          TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours'),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  notified_wife_at    TIMESTAMPTZ,

  CONSTRAINT constitutional_overrides_rule_range
    CHECK (rule_number BETWEEN 1 AND 13),
  CONSTRAINT constitutional_overrides_reason_min_length
    CHECK (length(reason) >= 20),
  CONSTRAINT constitutional_overrides_expires_after_created
    CHECK (expires_at > created_at)
);

CREATE INDEX IF NOT EXISTS constitutional_overrides_active_idx
  ON constitutional_overrides (rule_number, expires_at)
  WHERE expires_at > NOW();

CREATE INDEX IF NOT EXISTS constitutional_overrides_created_at_idx
  ON constitutional_overrides (created_at DESC);

COMMENT ON TABLE constitutional_overrides IS
  'Phase 7.5 meta — audit ledger for every escape-hatch use of any of the 13 constitutional rules. Rows are immutable from the application layer; rule violations are temporarily allowed for the 24-hour window then automatically lapse. The notified_wife_at column timestamps the Telegram notification (Phase 7.6 will wire the live notify; Phase 7.5 stubs it).';

COMMENT ON COLUMN constitutional_overrides.rule_number IS
  '1..13 — see docs/PHASE_7_5_ESCAPE_HATCHES.md for the rule -> hatch mapping.';

COMMENT ON COLUMN constitutional_overrides.reason IS
  'Justification text. CHECK (length >= 20) enforces the no-empty-excuse rule.';

COMMENT ON COLUMN constitutional_overrides.expires_at IS
  'Auto-expiry timestamp. Default = created_at + 24h. The partial index constitutional_overrides_active_idx covers only non-expired rows.';

-- ═══════════════════════════════════════════════════════════
-- Part 2: RLS — service_role full + family_read
-- ═══════════════════════════════════════════════════════════

ALTER TABLE constitutional_overrides ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS constitutional_overrides_service_all ON constitutional_overrides;
DROP POLICY IF EXISTS constitutional_overrides_family_read ON constitutional_overrides;

CREATE POLICY constitutional_overrides_service_all
  ON constitutional_overrides
  FOR ALL TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY constitutional_overrides_family_read
  ON constitutional_overrides
  FOR SELECT TO authenticated
  USING (true);

COMMIT;

-- ═══════════════════════════════════════════════════════════
-- POST-APPLY SMOKE TEST (manual, NOT in this transaction)
-- ═══════════════════════════════════════════════════════════
--
-- 1. Confirm table exists + RLS enabled:
--      psql "$SUPABASE_DB_URL" -c "\d constitutional_overrides"
--    Expect: "Row security: enabled".
--
-- 2. Confirm empty:
--      SELECT count(*) FROM constitutional_overrides;  -- expect 0
--
-- 3. Smoke-test (smoke insert + auto-expiry):
--      INSERT INTO constitutional_overrides
--        (rule_number, reason, overridden_by)
--        VALUES (9, 'smoke test — confirmed-hypothesis backfill window', 'shako')
--        RETURNING id, expires_at - created_at AS ttl;
--    Expect: ttl ~24:00:00.
--    Cleanup: DELETE FROM constitutional_overrides
--             WHERE reason LIKE 'smoke test%';
--
-- 4. Smoke-test (rule out-of-range -> reject):
--      INSERT INTO constitutional_overrides
--        (rule_number, reason, overridden_by)
--        VALUES (14, 'should fail constraint check 1-13', 'shako');
--    Expect: ERROR — violates constitutional_overrides_rule_range.
--
-- 5. Smoke-test (reason too short -> reject):
--      INSERT INTO constitutional_overrides
--        (rule_number, reason, overridden_by)
--        VALUES (1, 'short', 'shako');
--    Expect: ERROR — violates constitutional_overrides_reason_min_length.
--
-- ═══════════════════════════════════════════════════════════
-- ROLLBACK (apply only if migration 023 must be reversed)
-- ═══════════════════════════════════════════════════════════
--
-- BEGIN;
-- DROP TABLE IF EXISTS constitutional_overrides CASCADE;
-- -- pgcrypto retained (used by migrations 016/018/019/020).
-- COMMIT;
