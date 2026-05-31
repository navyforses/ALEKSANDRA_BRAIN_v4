"""Phase 7.1 Days 8-9 — Causal-schema-aware Graphiti adapter.

Replaces Phase 2's default Graphiti edge-writing with our 5-type Pearl SCM
taxonomy. Every edge write passes through edge_taxonomy.validate_edge_for_write()
BEFORE hitting Neo4j; no edge can land that violates the 7 invariants.

This module is the single trust boundary between Phase 2's Graphiti episodes
and Phase 7.1's causal graph. The pre-Phase-7.1 code path (Graphiti add_episode)
continues to work for backwards compatibility but emits a DeprecationWarning.

Live Neo4j integration is verified post-Shako-apply via verify_phase_7_1.py.
"""

from __future__ import annotations

import warnings
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from brain.memory.edge_taxonomy import (
    CausalEdge,
    CausalEdgeError,  # noqa: F401  — re-export so callers catch via this module
    CausalEdgeType,  # noqa: F401  — re-export for type annotations
    compute_edge_hash,
    is_citation_complete,
    validate_edge_for_write,
)


class CausalNeo4jAdapter:
    """Wraps a neo4j driver/session for Phase 7.1 causal-edge writes.

    Contract:
      - Every public write method runs validate_edge_for_write() first
      - Lookups are closures over the active session — no module-level state
      - Cypher uses parameterized queries (no string interpolation of user input)
      - Edge type is interpolated only after CausalEdgeType enum validation
        so the only possible values are the 5 known constants
    """

    def __init__(self, driver: Any) -> None:
        """Args: neo4j GraphDatabase driver instance (real or mock)."""
        self._driver = driver

    def write_causal_edge(self, edge: CausalEdge) -> dict[str, Any]:
        """Pre-flight validate + write a single causal edge. Returns audit dict.

        Order:
            1. Open session
            2. Build lookups against live DB
            3. validate_edge_for_write() — raises CausalEdgeError on violation
            4. CREATE cypher
            5. Return audit envelope
        """
        with self._driver.session() as session:
            existing_edges_lookup = _make_existing_edges_lookup(session)
            node_exists_lookup = _make_node_exists_lookup(session)
            edge_exists_by_hash_lookup = _make_edge_exists_by_hash_lookup(session)
            current_dag_edges = _fetch_dag_edges(session)

            # Pre-flight: any invariant violation raises before we touch the graph
            validate_edge_for_write(
                edge,
                existing_edges_lookup=existing_edges_lookup,
                node_exists_lookup=node_exists_lookup,
                edge_exists_by_hash_lookup=edge_exists_by_hash_lookup,
                all_edges_for_dag_check=current_dag_edges,
            )

            # Edge type is interpolated (Neo4j doesn't param-bind rel types),
            # but it is guaranteed to be one of the 5 enum values at this point.
            cypher = f"""
                MATCH (s) WHERE id(s) = $src
                MATCH (t) WHERE id(t) = $tgt
                CREATE (s)-[r:{edge.edge_type.value} {{
                    confidence: $confidence,
                    citation: $citation,
                    mechanism: $mechanism,
                    time_lag_days: $time_lag_days,
                    via_node: $via_node,
                    also_confounds: $also_confounds,
                    moderates_edge: $moderates_edge,
                    classified_by: $classified_by,
                    classified_rationale: $classified_rationale,
                    legacy_type: $legacy_type,
                    written_at: datetime()
                }}]->(t)
                RETURN id(r) AS edge_id
            """
            result = session.run(
                cypher,
                src=edge.source_id,
                tgt=edge.target_id,
                confidence=edge.confidence,
                citation=edge.citation,
                mechanism=edge.mechanism,
                time_lag_days=edge.time_lag_days,
                via_node=edge.via_node,
                also_confounds=edge.also_confounds,
                moderates_edge=edge.moderates_edge,
                classified_by=edge.classified_by,
                classified_rationale=edge.classified_rationale,
                legacy_type=edge.legacy_type,
            )
            new_id = result.single()["edge_id"]

        return {
            "edge_id": new_id,
            "edge_type": edge.edge_type.value,
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "citation_complete": is_citation_complete(edge.citation),
            "written_at": datetime.now(timezone.utc).isoformat(),
        }

    def delete_edge(self, edge_id: int | str) -> bool:
        """Delete an edge by id. Returns True if deleted, False if not found."""
        with self._driver.session() as session:
            result = session.run(
                "MATCH ()-[r]-() WHERE id(r) = $rid "
                "WITH r, count(r) AS c "
                "DELETE r RETURN c",
                rid=edge_id,
            )
            record = result.single()
            return bool(record) and record["c"] > 0


# ---------------------------------------------------------------------------
# Live-session lookup factories
# ---------------------------------------------------------------------------
def _make_existing_edges_lookup(session: Any) -> Callable[[Any, Any, str], bool]:
    """Return a closure: (source_id, target_id, edge_type) -> bool."""

    def lookup(source_id: Any, target_id: Any, edge_type: str) -> bool:
        result = session.run(
            f"MATCH (s)-[r:{edge_type}]->(t) "
            f"WHERE id(s) = $src AND id(t) = $tgt "
            f"RETURN count(r) AS c",
            src=source_id,
            tgt=target_id,
        )
        return result.single()["c"] > 0

    return lookup


def _make_node_exists_lookup(session: Any) -> Callable[[Any], bool]:
    """Return a closure: (node_id) -> bool."""

    def lookup(node_id: Any) -> bool:
        result = session.run(
            "MATCH (n) WHERE id(n) = $nid RETURN count(n) AS c", nid=node_id
        )
        return result.single()["c"] > 0

    return lookup


def _make_edge_exists_by_hash_lookup(session: Any) -> Callable[[str], bool]:
    """Return a closure: (edge_hash) -> bool.

    Walks every edge in the graph and compares its sha256[:16] hash.
    Acceptable for Phase 7.1 (~few hundred edges); revisit if the graph
    grows past ~10K edges (add a persistent edge_hash property + index).
    """

    def lookup(edge_hash: str) -> bool:
        result = session.run(
            "MATCH (s)-[r]->(t) RETURN id(s) AS s, id(t) AS t, type(r) AS et"
        )
        for record in result:
            if (
                compute_edge_hash(record["s"], record["t"], record["et"])
                == edge_hash
            ):
                return True
        return False

    return lookup


def _fetch_dag_edges(session: Any) -> list[tuple[Any, Any, str]]:
    """Fetch all current CAUSES/INHIBITS/MEDIATES edges for DAG-cycle check.

    CONFOUNDS + MODERATES are meta-edges and don't participate in the DAG.
    """
    result = session.run(
        "MATCH (s)-[r:CAUSES|INHIBITS|MEDIATES]->(t) "
        "RETURN id(s) AS src, id(t) AS tgt, type(r) AS et"
    )
    return [(rec["src"], rec["tgt"], rec["et"]) for rec in result]


# ---------------------------------------------------------------------------
# Backwards-compat shim — Phase 2 code paths
# ---------------------------------------------------------------------------
def add_episode_deprecated(*args: Any, **kwargs: Any) -> None:
    """Phase 2 Graphiti add_episode shim — refuses writes, points to new API."""
    warnings.warn(
        "Graphiti add_episode is deprecated post-Phase-7.1. "
        "Use CausalNeo4jAdapter.write_causal_edge() with a typed CausalEdge.",
        DeprecationWarning,
        stacklevel=2,
    )
    raise NotImplementedError(
        "Phase 7.1 removes Graphiti default edge writing. "
        "Use brain.memory.causal_adapter.CausalNeo4jAdapter for all edge writes."
    )


__all__ = [
    "CausalNeo4jAdapter",
    "add_episode_deprecated",
]
