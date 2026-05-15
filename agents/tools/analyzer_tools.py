"""
analyzer_tools.py — Phase 2 Analyzer agent tools.

Two thin wrappers for the entity-extraction pipeline:

  run_graphiti(ledger_id)  → invokes scripts.extraction.ingest_paper for one
      ledger row (Graphiti add_episode with the MEM-06 ontology). Returns
      counter dict including episodes_created and errors.

  neo4j_stats()            → counts current Entity / RELATES_TO / Episodic /
      MENTIONS in the hie_research group_id plus typed-label breakdown.
"""

from __future__ import annotations

import asyncio
import json
import os

from crewai.tools import tool
from neo4j import GraphDatabase

from scripts.ledger import load_env


@tool("run_graphiti")
def run_graphiti(ledger_id: str) -> str:
    """Ingest one evidence_ledger row into Graphiti as an Episode. Uses the
    MEM-06 ontology (Drug / Gene / Pathway / BrainRegion / Disease / Treatment
    / Biomarker / Trial). Idempotent: kv_state.graphiti_processed:<id> skips
    a fully-processed paper unless force=True. Returns JSON counter dict."""
    from scripts.extraction.ingest_paper import ingest_paper_as_episode

    load_env()
    counters = asyncio.run(ingest_paper_as_episode(ledger_id, force=False))
    return json.dumps(counters)


@tool("neo4j_stats")
def neo4j_stats() -> str:
    """Return current Neo4j graph stats: entity/relationship counts overall
    and broken down by ontology type (Drug/Disease/Gene/etc.)."""
    load_env()
    drv = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
    )
    with drv.session() as s:
        ent = s.run(
            "MATCH (n:Entity {group_id:'hie_research'}) RETURN count(n) AS c"
        ).single()["c"]
        rel = s.run(
            "MATCH ()-[r:RELATES_TO]->() WHERE r.group_id='hie_research' "
            "RETURN count(r) AS c"
        ).single()["c"]
        epi = s.run(
            "MATCH (n:Episodic {group_id:'hie_research'}) RETURN count(n) AS c"
        ).single()["c"]
        mentions = s.run(
            "MATCH ()-[r:MENTIONS]->() WHERE r.group_id='hie_research' "
            "RETURN count(r) AS c"
        ).single()["c"]
        typed: dict[str, int] = {}
        for type_name in (
            "Drug",
            "Disease",
            "Treatment",
            "Trial",
            "Biomarker",
            "Gene",
            "Pathway",
            "BrainRegion",
        ):
            typed[type_name] = s.run(
                f"MATCH (n:Entity:{type_name} {{group_id:'hie_research'}}) "
                "RETURN count(n) AS c"
            ).single()["c"]
    drv.close()
    return json.dumps(
        {
            "entities": ent,
            "relationships": rel,
            "episodes": epi,
            "mentions": mentions,
            "typed": typed,
        }
    )


__all__ = ["run_graphiti", "neo4j_stats"]
