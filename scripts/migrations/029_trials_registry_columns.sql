-- 029_trials_registry_columns.sql — Phase E wave 1 DDL.
-- Make clinical_trials registry-aware so EU CTIS + UK ISRCTN trials (which have
-- NO NCT id) can live alongside ClinicalTrials.gov rows without polluting the
-- NCT namespace. Mirrors the research doc (docs/CLINICAL_TRIALS_SOURCES_RESEARCH.md
-- "Schema change → Option A").
--
-- Before: clinical_trials is keyed only on nct_id (UNIQUE). A CTIS/ISRCTN trial
-- has no NCT number, so it could not upsert without abusing the nct_id column.
--
-- After (all ADDITIVE — no column is dropped or retyped):
--   * registry      TEXT     'ctgov' | 'ctis' | 'isrctn'  (the id namespace)
--   * registry_id   TEXT     native id (nct_id / ctNumber / ISRCTN number)
--   * secondary_ids TEXT[]   sibling-registry ids for cross-registry dedup
--                            (e.g. {'NCT06...','ISRCTN61218504','EudraCT...'})
--   * ux_trials_registry  partial UNIQUE INDEX on (registry, registry_id)
--                         WHERE registry IS NOT NULL — the new natural key for
--                         non-NCT registries; ctgov rows keep upserting on nct_id.
--
-- Backfill: existing rows are all ctgov, so set registry='ctgov' and
-- registry_id=nct_id WHERE registry IS NULL (idempotent — re-running is a no-op
-- because the WHERE clause matches nothing the second time).
--
-- Idempotent-by-guard: every statement uses IF NOT EXISTS (columns + index) and
-- the backfill UPDATE is naturally idempotent, so re-running this SQL is safe.
-- The orchestrator (029_trials_registry_columns.py) additionally checks
-- information_schema and prints before/after.
--
-- Why RLS survives: ADD COLUMN and CREATE INDEX do NOT drop row-level-security
-- policies (same reasoning as migrations 012 / 017 / 028). No column is retyped,
-- so there is nothing for a USING clause to break.
--
-- SAFE TO APPLY LIVE: clinical_trials is fully reconstructable by re-running the
-- matcher from evidence_ledger + R2 (the backup JSON in 029_trials_backup.json is
-- an extra safety net captured before any DDL).
--
-- Apply via the orchestrator (recommended, guarded):
--   PYTHONUTF8=1 .venv/Scripts/python.exe \
--     -m scripts.migrations.029_trials_registry_columns --apply
-- or by hand:
--   psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 \
--     -f scripts/migrations/029_trials_registry_columns.sql

BEGIN;

-- ── registry: which register this row came from. NULL is allowed transiently
--    (pre-backfill) but the partial unique index below only constrains non-NULL.
ALTER TABLE clinical_trials
  ADD COLUMN IF NOT EXISTS registry TEXT;

-- ── registry_id: the registry-native id. For ctgov this equals nct_id; for CTIS
--    it is the ctNumber; for ISRCTN it is the ISRCTN number.
ALTER TABLE clinical_trials
  ADD COLUMN IF NOT EXISTS registry_id TEXT;

-- ── secondary_ids: sibling-registry ids surfaced by the source (CTIS
--    secondaryIdentifyingNumbers, ISRCTN externalRefs). Drives cross-registry
--    dedup (ACUMEN appears in CTIS AND ISRCTN).
ALTER TABLE clinical_trials
  ADD COLUMN IF NOT EXISTS secondary_ids TEXT[];

-- ── Backfill existing (all-ctgov) rows. Idempotent: WHERE registry IS NULL
--    matches nothing on a second run.
UPDATE clinical_trials
  SET registry = 'ctgov',
      registry_id = nct_id
  WHERE registry IS NULL;

-- ── New natural key for non-NCT registries. Partial so legacy/ctgov-only rows
--    (which set registry='ctgov', registry_id=nct_id during backfill) and any
--    future NULL-registry row never collide.
CREATE UNIQUE INDEX IF NOT EXISTS ux_trials_registry
  ON clinical_trials (registry, registry_id)
  WHERE registry IS NOT NULL;

-- ── Broaden the evidence_ledger allow-list CHECK constraints so the new registry
--    fetchers can write provenance rows. This is ADDITIVE (it only widens an
--    allow-list) — no existing value is removed, so every prior row still
--    satisfies the new constraint. Drop-and-re-add is the only way to alter a
--    CHECK; both are inside this transaction so it is atomic.
ALTER TABLE evidence_ledger DROP CONSTRAINT IF EXISTS evidence_ledger_source_type_chk;
ALTER TABLE evidence_ledger ADD CONSTRAINT evidence_ledger_source_type_chk
  CHECK (source_type = ANY (ARRAY[
    'pubmed', 'ctgov', 'biorxiv', 'medrxiv', 'crawl4ai', 'firecrawl',
    'ctis', 'isrctn'
  ]));

ALTER TABLE evidence_ledger DROP CONSTRAINT IF EXISTS evidence_ledger_retrieval_method_chk;
ALTER TABLE evidence_ledger ADD CONSTRAINT evidence_ledger_retrieval_method_chk
  CHECK (retrieval_method = ANY (ARRAY[
    'eutils', 'ctgov_v2_rest', 'rss', 'crawl4ai', 'firecrawl',
    'ctis_public_api', 'isrctn_query_api'
  ]));

COMMIT;

-- Smoke check (run after apply, outside the transaction):
--   SELECT column_name, data_type FROM information_schema.columns
--     WHERE table_name='clinical_trials'
--       AND column_name IN ('registry','registry_id','secondary_ids');
--   SELECT registry, count(*) FROM clinical_trials GROUP BY registry;
--   SELECT indexname FROM pg_indexes
--     WHERE tablename='clinical_trials' AND indexname='ux_trials_registry';
-- Expected: registry TEXT, registry_id TEXT, secondary_ids ARRAY; every existing
--           row registry='ctgov'; ux_trials_registry index present.
