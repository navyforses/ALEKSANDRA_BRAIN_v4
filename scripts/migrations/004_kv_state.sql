-- ═══════════════════════════════════════════════════════════
-- Migration 004: kv_state — Phase 1 (PRC-04, PRC-05 gating state)
-- ═══════════════════════════════════════════════════════════
--
-- Small key-value store for cross-run perception-layer state:
--
--   - crawl_fail:<sha256_url>      JSONB { "count": N, "last_at": "..." }
--   - firecrawl_spend:<YYYY-MM>    JSONB { "usd": 0.45, "calls": 9 }
--
-- Originally the design called for Cloudflare KV here. Using Supabase
-- instead keeps every Phase 1 stateful piece in one place (single
-- backup story, one credential to rotate) and the cron frequency
-- (4/day) is far below anything where KV's edge latency matters.
--
-- Apply via: python -m scripts.migrate --only 004_kv_state

BEGIN;

CREATE TABLE IF NOT EXISTS kv_state (
  key         TEXT PRIMARY KEY,
  value       JSONB NOT NULL,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE kv_state IS
  'Phase 1 perception-layer key-value state. Holds crawl_fail counters and firecrawl_spend totals so gap_filler.py and fetch_firecrawl.py can gate calls across cron runs.';

ALTER TABLE kv_state ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS kv_state_family_read ON kv_state;
CREATE POLICY kv_state_family_read ON kv_state
  FOR SELECT
  TO authenticated
  USING (true);

DROP POLICY IF EXISTS kv_state_service_write ON kv_state;
CREATE POLICY kv_state_service_write ON kv_state
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

COMMIT;
