-- ═══════════════════════════════════════════════════════════
-- Migration 001: runs ledger (append-only) — Phase 0 (OBS-01)
-- ═══════════════════════════════════════════════════════════
--
-- Adds the `runs` table required by Phase 0 (OBS-01). Append-only
-- by trigger — UPDATE and DELETE are rejected, INSERT is allowed.
--
-- Apply after scripts/schema.sql via scripts/migrate.sh.

BEGIN;

-- ---------------------------------------------------------------------------
-- runs — append-only ledger of every agent run, cron tick, and kill-switch
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS runs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- What ran
  kind TEXT NOT NULL,                          -- agent_run | cron_tick | kill_switch | fire_drill
  agent_id TEXT,                               -- spider | analyzer | hypothesis | repurposing | communicator | null
  workflow_id TEXT,                            -- n8n workflow id when applicable
  patient_context_version TEXT,                -- which Aleksandra context doc was active (CGM-10)

  -- When
  start_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  end_time   TIMESTAMPTZ,
  duration_seconds INTEGER GENERATED ALWAYS AS
    (EXTRACT(EPOCH FROM (end_time - start_time))::INTEGER) STORED,

  -- Cost
  token_cost NUMERIC(10, 4) DEFAULT 0,         -- USD spent on Anthropic in this run
  tokens_input  INTEGER DEFAULT 0,
  tokens_output INTEGER DEFAULT 0,

  -- Outcome
  exit_status TEXT NOT NULL DEFAULT 'in_progress',
  -- in_progress | completed | failed | killed_by_panic_stop | killed_by_budget_gate
  -- | killed_by_max_iter | killed_by_max_tokens | killed_by_timeout
  exit_reason TEXT,                            -- free-form on failure
  draft_link TEXT,                             -- URL of the produced draft, if any (e.g. Notion page)

  -- Provenance back-reference
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_runs_kind         ON runs(kind);
CREATE INDEX IF NOT EXISTS idx_runs_agent        ON runs(agent_id);
CREATE INDEX IF NOT EXISTS idx_runs_start_time   ON runs(start_time DESC);
CREATE INDEX IF NOT EXISTS idx_runs_exit_status  ON runs(exit_status);

COMMENT ON TABLE runs IS
  'OBS-01 append-only ledger. Every agent run, cron tick, kill-switch, and fire drill writes one row. UPDATE and DELETE are rejected by trigger.';

-- ---------------------------------------------------------------------------
-- Append-only enforcement (OBS-01)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION block_runs_mutation()
RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'runs is append-only: % rejected', TG_OP
    USING ERRCODE = 'P0001';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS runs_no_update ON runs;
CREATE TRIGGER runs_no_update
  BEFORE UPDATE ON runs
  FOR EACH ROW
  EXECUTE FUNCTION block_runs_mutation();

DROP TRIGGER IF EXISTS runs_no_delete ON runs;
CREATE TRIGGER runs_no_delete
  BEFORE DELETE ON runs
  FOR EACH ROW
  EXECUTE FUNCTION block_runs_mutation();

-- ---------------------------------------------------------------------------
-- Row-level security: family-only read; service role only write (FND-05)
-- ---------------------------------------------------------------------------
ALTER TABLE runs ENABLE ROW LEVEL SECURITY;

-- Authenticated family member: read all
DROP POLICY IF EXISTS runs_family_read ON runs;
CREATE POLICY runs_family_read ON runs
  FOR SELECT
  TO authenticated
  USING (true);

-- Service role only: insert (agents, n8n, panic_stop)
DROP POLICY IF EXISTS runs_service_write ON runs;
CREATE POLICY runs_service_write ON runs
  FOR INSERT
  TO service_role
  WITH CHECK (true);

-- anon: no access at all (default since no policy granted)

COMMIT;

-- ---------------------------------------------------------------------------
-- Sanity check — run the four assertions Phase 0 success criterion #6 wants
-- ---------------------------------------------------------------------------
-- INSERT INTO runs (kind, agent_id, exit_status) VALUES ('agent_run', 'spider', 'completed');
-- UPDATE runs SET exit_status = 'failed';     -- should raise: runs is append-only
-- DELETE FROM runs;                           -- should raise: runs is append-only
