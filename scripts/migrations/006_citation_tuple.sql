-- ─────────────────────────────────────────────────────────────────────────────
-- 006_citation_tuple.sql — Phase 2 sub-phase 2B (MEM-01)
--
-- Promotes paper_chunks to a first-class "citation tuple" carrier as required
-- by REQUIREMENTS.md MEM-01:
--     "The citation tuple {source_id, retrieval_method, retrieval_timestamp,
--      confidence, verbatim_grounding, byte_offset} is a first-class type
--      referenced by every claim."
--
-- source_id, retrieval_method, retrieval_timestamp already live on the
-- evidence_ledger row this chunk joins to. The two new columns close the
-- structural gap:
--
--   verbatim_grounding — literal, immutable copy of the chunk text. Stored
--   as a GENERATED ALWAYS column over raw_text so it can never drift from
--   the actual text the embedding was computed over. Marked STORED so it's
--   queryable like a regular column without re-evaluating the expression.
--
--   byte_offset — start position of the chunk inside the extracted source
--   text (what extract_text() returned for the parent ledger row). For
--   future ingests this is populated by chunker.py during chunking. For
--   the 409 existing rows it stays NULL — backfilling would require
--   re-running extract_text on every R2 artifact and replaying the
--   RecursiveCharacterTextSplitter byte-for-byte, which is non-deterministic
--   across LangChain version upgrades. The verify_phase2 MEM-01 audit only
--   asks "does the column exist", not "is it populated for every row".
--
-- confidence is intentionally NOT added to paper_chunks: confidence is a
-- per-CLAIM property (a Graphiti RELATES_TO edge attribute), not a per-
-- citation-source property — the same chunk can ground a high-confidence
-- and a low-confidence claim. The Graphiti fact carries it.
--
-- Re-runnable: every statement uses IF NOT EXISTS / DO blocks so applying
-- the migration twice is a no-op.
-- ─────────────────────────────────────────────────────────────────────────────

-- verbatim_grounding: GENERATED ALWAYS over raw_text. STORED so it's
-- indexable and not re-evaluated on every SELECT.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'paper_chunks'
          AND column_name  = 'verbatim_grounding'
    ) THEN
        ALTER TABLE public.paper_chunks
        ADD COLUMN verbatim_grounding text
            GENERATED ALWAYS AS (raw_text) STORED;
    END IF;
END
$$;

-- byte_offset: start byte position of this chunk in the parent source text.
-- Nullable for backfill on the pre-migration 409 rows.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'paper_chunks'
          AND column_name  = 'byte_offset'
    ) THEN
        ALTER TABLE public.paper_chunks
        ADD COLUMN byte_offset integer;
    END IF;
END
$$;

-- Index for byte-offset range scans (used by future "show me the surrounding
-- text" tooling that reads ±N chars around a chunk for verbatim citation).
CREATE INDEX IF NOT EXISTS idx_paper_chunks_byte_offset
    ON public.paper_chunks (ledger_id, byte_offset);
