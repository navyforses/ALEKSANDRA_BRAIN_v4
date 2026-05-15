-- ═══════════════════════════════════════════════════════════
-- Migration 005: paper_chunks — Phase 2 (KNW-01)
-- ═══════════════════════════════════════════════════════════
--
-- Chunked text for every paper that lives in evidence_ledger. The
-- ledger row is the provenance contract (PRC-07); paper_chunks is the
-- queryable representation that feeds Qdrant embeddings (KNW-02) and
-- Graphiti entity extraction (KNW-03).
--
-- One ledger row -> N chunks. Each chunk has its own SHA256-derived
-- Qdrant point id (embedding_id) so chunk-level retrievability works
-- before the embedding job finishes.
--
-- Apply via: python -m scripts.migrate --only 005_paper_chunks

BEGIN;

CREATE TABLE IF NOT EXISTS paper_chunks (
  id           UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Provenance link back to the ledger row
  ledger_id    UUID NOT NULL REFERENCES evidence_ledger(id) ON DELETE CASCADE,
  source_type  TEXT NOT NULL,   -- denormalised from ledger for fast filtering
  source_id    TEXT NOT NULL,   -- denormalised

  -- Chunk content
  chunk_index  INT  NOT NULL,
  raw_text     TEXT NOT NULL,
  char_count   INT  NOT NULL,
  chunk_type   TEXT NOT NULL DEFAULT 'text',  -- text | abstract | table_caption | section_header

  -- Embedding bookkeeping
  embedding_id TEXT,                          -- Qdrant point id (UUID); NULL until embedded
  embedded_at  TIMESTAMPTZ,

  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT paper_chunks_chunk_type_chk CHECK (
    chunk_type IN ('text', 'abstract', 'table_caption', 'section_header')
  )
);

-- One row per (ledger_id, chunk_index) — re-runs are idempotent.
CREATE UNIQUE INDEX IF NOT EXISTS paper_chunks_dedup_idx
  ON paper_chunks (ledger_id, chunk_index);

CREATE INDEX IF NOT EXISTS paper_chunks_ledger_idx
  ON paper_chunks (ledger_id);

CREATE INDEX IF NOT EXISTS paper_chunks_embedding_idx
  ON paper_chunks (embedding_id);

CREATE INDEX IF NOT EXISTS paper_chunks_source_idx
  ON paper_chunks (source_type, source_id);

CREATE INDEX IF NOT EXISTS paper_chunks_unembedded_idx
  ON paper_chunks (ledger_id) WHERE embedding_id IS NULL;

COMMENT ON TABLE paper_chunks IS
  'Phase 2 KNW-01: per-paper text chunks for embedding (KNW-02) and entity extraction (KNW-03). FK to evidence_ledger preserves provenance; embedding_id stays NULL until the fastembed batch upserts to Qdrant.';

-- RLS: family read / service-role write — same posture as evidence_ledger
ALTER TABLE paper_chunks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS paper_chunks_family_read ON paper_chunks;
CREATE POLICY paper_chunks_family_read ON paper_chunks
  FOR SELECT
  TO authenticated
  USING (true);

DROP POLICY IF EXISTS paper_chunks_service_write ON paper_chunks;
CREATE POLICY paper_chunks_service_write ON paper_chunks
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

COMMIT;
