"""Phase 2 sub-phase 2A — chunking + embedding pipeline.

Modules
-------
- extractor   format-aware text extraction from R2 artifacts (PubMed XML,
              CT.gov JSON, bio/medRxiv RSS, Crawl4AI markdown)
- chunker     LangChain RecursiveCharacterTextSplitter wrapper
- embedder    fastembed BAAI/bge-small-en-v1.5 + Qdrant upsert
- process_ledger orchestrator: ledger row -> R2 fetch -> extract -> chunk
              -> embed -> Supabase paper_chunks INSERT
"""
