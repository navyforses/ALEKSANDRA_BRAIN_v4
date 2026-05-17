-- ═══════════════════════════════════════════════════════════
-- Migration 010: delivery-table back-pointers → runs(id) — Phase 4 (OBS-02)
-- ═══════════════════════════════════════════════════════════
--
-- Adds a nullable FK column `originating_run_id UUID REFERENCES runs(id)`
-- to each of the three Phase 3/4 delivery tables: `alerts_log`,
-- `outreach_log`, `briefs`. Each row in those tables now records the
-- `runs` row that produced the delivery, so that the OBS-02 invariant
-- ("every delivered digest links to originating runs.id") can be
-- enforced and queried.
--
-- Why this migration follows migration 009:
--
--   Migration 009 added a FORWARD pointer `runs.digest_id` with a
--   strict trigger. That direction is structurally limited — a single
--   `runs` row can only carry one digest_id, so a run that produces
--   both a Telegram message AND a Notion archive page cannot link to
--   both deliveries. The verify_phase4 OBS-02 check (scaffolded Day 1)
--   was written against the BACKWARD direction: each delivery row
--   carries its own originating_run_id, and one run can have many
--   delivery rows pointing back to it (1:N).
--
--   Migration 009 stays applied — its strict trigger upgrade on
--   `runs` is a defense-in-depth win regardless of whether
--   `runs.digest_id` ever gets populated.
--
-- Append-only impact: zero. `originating_run_id` is written at INSERT
-- time on the delivery row and never updated. The existing CHECK
-- constraints (`phi_redacted = TRUE`) and RLS policies remain in force.
-- These tables are not under the `runs`-style append-only trigger,
-- so no trigger surgery is needed.
--
-- IDEMPOTENT: column adds use `IF NOT EXISTS`; index creations use
-- `IF NOT EXISTS`.
--
-- Rollback at the bottom of this file.
--
-- HUMAN-APPROVAL GATE: do NOT apply until Shako has reviewed
-- docs/PHASE_4_DAY6_MIGRATION_DIFF.md §"Migration 010 addendum".
--
-- Apply via:
--   psql $SUPABASE_DB_URL -f scripts/migrations/010_delivery_originating_run_id.sql

BEGIN;

-- ---------------------------------------------------------------------------
-- alerts_log — Telegram message audit (Phase 3 + Phase 4)
-- ---------------------------------------------------------------------------
ALTER TABLE alerts_log
  ADD COLUMN IF NOT EXISTS originating_run_id UUID;

-- Add the FK constraint separately so the IF NOT EXISTS pattern works.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'alerts_log_originating_run_id_fkey'
  ) THEN
    ALTER TABLE alerts_log
      ADD CONSTRAINT alerts_log_originating_run_id_fkey
      FOREIGN KEY (originating_run_id) REFERENCES runs(id)
      ON DELETE RESTRICT;
  END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_alerts_log_originating_run
  ON alerts_log(originating_run_id)
  WHERE originating_run_id IS NOT NULL;

COMMENT ON COLUMN alerts_log.originating_run_id IS
  'OBS-02: back-pointer to the runs row whose execution produced this Telegram delivery. NULL on legacy rows; populated at INSERT time on new rows by scripts.communicator.telegram_sender.';

-- ---------------------------------------------------------------------------
-- outreach_log — Gmail draft audit (Phase 3 + Phase 4)
-- ---------------------------------------------------------------------------
ALTER TABLE outreach_log
  ADD COLUMN IF NOT EXISTS originating_run_id UUID;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'outreach_log_originating_run_id_fkey'
  ) THEN
    ALTER TABLE outreach_log
      ADD CONSTRAINT outreach_log_originating_run_id_fkey
      FOREIGN KEY (originating_run_id) REFERENCES runs(id)
      ON DELETE RESTRICT;
  END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_outreach_log_originating_run
  ON outreach_log(originating_run_id)
  WHERE originating_run_id IS NOT NULL;

COMMENT ON COLUMN outreach_log.originating_run_id IS
  'OBS-02: back-pointer to the runs row whose execution produced this Gmail draft. NULL on legacy rows; populated at INSERT time on new rows by scripts.communicator.outreach_drafter and gmail_digest.';

-- ---------------------------------------------------------------------------
-- briefs — Weekly Brief audit (Phase 3 + Phase 4)
-- ---------------------------------------------------------------------------
ALTER TABLE briefs
  ADD COLUMN IF NOT EXISTS originating_run_id UUID;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'briefs_originating_run_id_fkey'
  ) THEN
    ALTER TABLE briefs
      ADD CONSTRAINT briefs_originating_run_id_fkey
      FOREIGN KEY (originating_run_id) REFERENCES runs(id)
      ON DELETE RESTRICT;
  END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_briefs_originating_run
  ON briefs(originating_run_id)
  WHERE originating_run_id IS NOT NULL;

COMMENT ON COLUMN briefs.originating_run_id IS
  'OBS-02: back-pointer to the runs row whose execution produced this Weekly Brief. NULL on legacy rows; populated at INSERT time on new rows by scripts.communicator.weekly_brief.';

COMMIT;

-- ═══════════════════════════════════════════════════════════
-- ROLLBACK (apply only if migration 010 must be reversed)
-- ═══════════════════════════════════════════════════════════
--
-- BEGIN;
--
-- DROP INDEX IF EXISTS idx_briefs_originating_run;
-- ALTER TABLE briefs DROP CONSTRAINT IF EXISTS briefs_originating_run_id_fkey;
-- ALTER TABLE briefs DROP COLUMN IF EXISTS originating_run_id;
--
-- DROP INDEX IF EXISTS idx_outreach_log_originating_run;
-- ALTER TABLE outreach_log DROP CONSTRAINT IF EXISTS outreach_log_originating_run_id_fkey;
-- ALTER TABLE outreach_log DROP COLUMN IF EXISTS originating_run_id;
--
-- DROP INDEX IF EXISTS idx_alerts_log_originating_run;
-- ALTER TABLE alerts_log DROP CONSTRAINT IF EXISTS alerts_log_originating_run_id_fkey;
-- ALTER TABLE alerts_log DROP COLUMN IF EXISTS originating_run_id;
--
-- COMMIT;
