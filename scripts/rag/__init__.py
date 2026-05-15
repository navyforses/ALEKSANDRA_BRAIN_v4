"""Phase 2 sub-phase 2C — single retrieval surface (MEM-05).

The only entry point agents are allowed to use:
    from scripts.rag.retrieve import retrieve

Direct imports of `qdrant_client` or `neo4j` from inside `agents/*` are
blocked by `scripts/rag/_lint_agents.py`. This package fans the query out to
Qdrant (semantic) + Graphiti/Neo4j (graph-walk) and merges the result.
"""
