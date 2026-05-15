-- ═══════════════════════════════════════════════════════════
-- Migration 003: evidence_ledger — Phase 1 (PRC-07)
-- ═══════════════════════════════════════════════════════════
--
-- Provenance ledger for every external document ingested by the
-- perception layer (PubMed, ClinicalTrials.gov, bioRxiv, medRxiv,
-- Crawl4AI, Firecrawl). Each row pins one (source, mode) tuple to
-- a content-hash and an R2 raw-artifact URL — the five provenance
-- fields PRC-07 requires:
--   source_id, retrieval_method, retrieval_timestamp,
--   content_hash, raw_artifact_url
--
-- Append-friendly (no triggers blocking UPDATE/DELETE) so we can
-- correct metadata, but uniqueness on (source_id, source_type, mode)
-- prevents duplicate ingestion.
--
-- Apply via: python -m scripts.migrate

BEGIN;

-- ---------------------------------------------------------------------------
-- evidence_ledger
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evidence_ledger (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Five provenance fields (PRC-07)
  source_id            TEXT NOT NULL,                       -- PMID | NCT-id | DOI | content-hash for crawl4ai/firecrawl
  source_type          TEXT NOT NULL,                       -- pubmed | ctgov | biorxiv | medrxiv | crawl4ai | firecrawl
  retrieval_method     TEXT NOT NULL,                       -- eutils | ctgov_v2_rest | rss | crawl4ai | firecrawl
  retrieval_timestamp  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  content_hash         TEXT NOT NULL,                       -- SHA256 hex digest of raw payload
  raw_artifact_url     TEXT NOT NULL,                       -- s3://aleksandra-brain-storage/<source_type>/<source_id>.<ext>

  -- Branching + provenance metadata
  mode                 TEXT NOT NULL DEFAULT 'positive',    -- positive | negative (PRC-06)
  query                TEXT,                                -- which query string surfaced this record (nullable for negative-branch & gap-filler)
  payload_metadata     JSONB,                               -- title, authors, journal, publication_date, abstract excerpt, full_text_url, has_full_text

  -- Bookkeeping
  ingested_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Enum-like validation (TEXT + CHECK so we can extend without ALTER TYPE)
  CONSTRAINT evidence_ledger_source_type_chk CHECK (
    source_type IN ('pubmed', 'ctgov', 'biorxiv', 'medrxiv', 'crawl4ai', 'firecrawl')
  ),
  CONSTRAINT evidence_ledger_retrieval_method_chk CHECK (
    retrieval_method IN ('eutils', 'ctgov_v2_rest', 'rss', 'crawl4ai', 'firecrawl')
  ),
  CONSTRAINT evidence_ledger_mode_chk CHECK (
    mode IN ('positive', 'negative')
  )
);

-- Deduplication: same source_id can appear in both positive and negative branches.
CREATE UNIQUE INDEX IF NOT EXISTS evidence_ledger_dedup_idx
  ON evidence_ledger (source_id, source_type, mode);

-- Recent-first queries (used by gap_filler.py to find abstract-only rows in last 6h).
CREATE INDEX IF NOT EXISTS evidence_ledger_retrieval_timestamp_idx
  ON evidence_ledger (retrieval_timestamp DESC);

-- Hash lookups (used by R2 idempotency check).
CREATE INDEX IF NOT EXISTS evidence_ledger_content_hash_idx
  ON evidence_ledger (content_hash);

-- Source-type filtering (used by verify_phase1.py).
CREATE INDEX IF NOT EXISTS evidence_ledger_source_type_idx
  ON evidence_ledger (source_type);

COMMENT ON TABLE evidence_ledger IS
  'PRC-07 provenance ledger. One row per (source_id, source_type, mode) — pins the five provenance fields required by Phase 1: source_id, retrieval_method, retrieval_timestamp, content_hash, raw_artifact_url. Append-friendly, RLS family-read service-write.';

-- ---------------------------------------------------------------------------
-- Row-level security: family-only read; service role only write (FND-05)
-- ---------------------------------------------------------------------------
ALTER TABLE evidence_ledger ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS evidence_ledger_family_read ON evidence_ledger;
CREATE POLICY evidence_ledger_family_read ON evidence_ledger
  FOR SELECT
  TO authenticated
  USING (true);

DROP POLICY IF EXISTS evidence_ledger_service_write ON evidence_ledger;
CREATE POLICY evidence_ledger_service_write ON evidence_ledger
  FOR INSERT
  TO service_role
  WITH CHECK (true);

-- anon: no access at all (default since no policy granted)

COMMIT;
