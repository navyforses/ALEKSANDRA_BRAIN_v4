"""Phase 2 sub-phase 2C — cross-disease hypothesis generator.

GoT-lite: a 4-step Sonnet 4.5 pipeline (decompose -> retrieve -> evaluate ->
prune) over the entities + facts produced by Graphiti in sub-phase 2B. The
full Adaptive Graph of Thoughts MCP vendor is deferred to Phase 3 — at 200
entities our chain-of-evidence is shallow enough that the lighter pipeline
yields equivalent quality without the maintenance burden of vendoring a
single-maintainer upstream.
"""
