"""Phase 2 sub-phase 2B — Graphiti entity extraction to Neo4j.

Modules
-------
- graphiti_client  Singleton Graphiti instance wired to Neo4j + Claude Haiku 4.5
- ingest_paper     Per-paper episode ingestion (one ledger row -> one or
                   more Graphiti episodes)
- batch_ingest     Iterate evidence_ledger + kv_state.graphiti_processed
                   flag for crash-safe resume
"""
