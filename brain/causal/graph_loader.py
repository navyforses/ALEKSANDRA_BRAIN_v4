"""Phase 7.2 Day 2 — Neo4j CausalNode + edges -> NetworkX DiGraph adapter.

Reads the Phase 7.1 causal graph (568 CausalNode + ~250-300 typed causal edges)
and emits a NetworkX DiGraph ready for DoWhy ``CausalModel(graph=...)`` consumption.

Two input modes:
    1. Live Neo4j:    ``load_from_neo4j(driver) -> nx.DiGraph``
    2. JSON snapshot: ``load_from_snapshot(path) -> nx.DiGraph``
       (consumes scripts/backup_neo4j.py output format)

DAG_PARTICIPATING_TYPES filter is applied — CONFOUNDS + MODERATES are
meta-edges (latent common cause / effect-modifier) and intentionally
excluded from the structural DAG passed to DoWhy.

Phase 7.1 carry-forward #2 contract: ``include_tbd_citations`` defaults to
False so that ``TBD-Day-7-backfill`` placeholder edges (no real provenance)
do not silently leak into downstream estimands. Set True only for diagnostics.

Reference:
    - Pearl, _Causality_ 2nd ed., 2009, §1.4 (DAGs as causal models).
    - DoWhy graph input contract:
      https://www.pywhy.org/dowhy/v0.11.1/user_guide/modeling_causal_relations/index.html
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import networkx as nx

from brain.memory.edge_taxonomy import DAG_PARTICIPATING_TYPES, TBD_PLACEHOLDER


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
def load_from_neo4j(driver, *, include_tbd_citations: bool = False) -> nx.DiGraph:
    """Build NetworkX DiGraph from live Neo4j CausalNodes + DAG-participating edges.

    Args:
        driver: ``neo4j.GraphDatabase`` driver instance (must support
            ``driver.session()`` context manager).
        include_tbd_citations: if False (default), exclude edges with
            ``citation == 'TBD-Day-7-backfill'``  (Phase 7.1 carry-forward
            #2 — these are placeholder, not real evidence and must NOT
            participate in production identify_effect / estimate flows).

    Returns:
        ``nx.DiGraph`` with
            node attrs: ``{name, dimension_ref, labels}``
            edge attrs: ``{edge_type, confidence, citation, mechanism, time_lag_days}``
    """
    graph = nx.DiGraph()
    with driver.session() as session:
        # Nodes — pull all CausalNodes
        node_result = session.run(
            "MATCH (n:CausalNode) "
            "RETURN id(n) AS nid, n.name AS name, "
            "n.dimension_ref AS dim_ref, labels(n) AS labels"
        )
        for record in node_result:
            graph.add_node(
                record["nid"],
                name=record["name"],
                dimension_ref=record["dim_ref"],
                labels=list(record["labels"]),
            )

        # Edges — DAG-participating types only (CAUSES, INHIBITS, MEDIATES)
        rel_type_filter = "|".join(sorted(DAG_PARTICIPATING_TYPES))
        edge_result = session.run(
            f"MATCH (s:CausalNode)-[r:{rel_type_filter}]->(t:CausalNode) "
            "RETURN id(s) AS src, id(t) AS tgt, type(r) AS et, "
            "r.confidence AS conf, r.citation AS cite, "
            "r.mechanism AS mech, r.time_lag_days AS lag"
        )
        for record in edge_result:
            citation = record["cite"]
            if not include_tbd_citations and citation == TBD_PLACEHOLDER:
                continue
            # Defensive: both endpoints must already be in the node set
            src_id, tgt_id = record["src"], record["tgt"]
            if src_id not in graph.nodes or tgt_id not in graph.nodes:
                continue
            graph.add_edge(
                src_id,
                tgt_id,
                edge_type=record["et"],
                confidence=record["conf"],
                citation=citation,
                mechanism=record["mech"],
                time_lag_days=record["lag"],
            )
    return graph


def load_from_snapshot(
    path: Path | str, *, include_tbd_citations: bool = False
) -> nx.DiGraph:
    """Build NetworkX DiGraph from a ``scripts/backup_neo4j.py`` JSON snapshot.

    Snapshot format (from ``scripts/backup_neo4j.py``)::

        {
          "nodes": [
            {"internal_id": int, "labels": [str], "properties": dict}, ...
          ],
          "relationships": [
            {"source_internal_id": int, "target_internal_id": int,
             "type": str, "properties": dict}, ...
          ]
        }

    Args:
        path: filesystem path to the JSON snapshot.
        include_tbd_citations: see :func:`load_from_neo4j`.
    """
    path = Path(path)
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    graph = nx.DiGraph()

    # Nodes — CausalNode-labelled only
    for node in snapshot.get("nodes", []):
        labels = node.get("labels", []) or []
        if "CausalNode" not in labels:
            continue
        props = node.get("properties", {}) or {}
        graph.add_node(
            node["internal_id"],
            name=props.get("name"),
            dimension_ref=props.get("dimension_ref"),
            labels=list(labels),
        )

    # Edges — DAG-participating types only, both endpoints must be CausalNodes
    for rel in snapshot.get("relationships", []):
        rel_type = rel.get("type")
        if rel_type not in DAG_PARTICIPATING_TYPES:
            continue
        src_id = rel.get("source_internal_id")
        tgt_id = rel.get("target_internal_id")
        if src_id not in graph.nodes or tgt_id not in graph.nodes:
            continue
        props = rel.get("properties", {}) or {}
        citation = props.get("citation")
        if not include_tbd_citations and citation == TBD_PLACEHOLDER:
            continue
        graph.add_edge(
            src_id,
            tgt_id,
            edge_type=rel_type,
            confidence=props.get("confidence"),
            citation=citation,
            mechanism=props.get("mechanism"),
            time_lag_days=props.get("time_lag_days"),
        )
    return graph


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------
def get_node_by_name(graph: nx.DiGraph, name: str) -> Optional[int]:
    """Return node id where node.name == name (case-insensitive exact match).

    Returns None if no node matches.
    """
    if name is None:
        return None
    target = name.lower()
    for nid, attrs in graph.nodes(data=True):
        node_name = attrs.get("name")
        if node_name is not None and node_name.lower() == target:
            return nid
    return None


def get_node_by_dimension_ref(graph: nx.DiGraph, dim_id: int) -> Optional[int]:
    """Return node id where node.dimension_ref == dim_id.

    Used for belief <-> causal cross-link traversal (see
    brain/memory/cross_link.py for the write side).
    """
    for nid, attrs in graph.nodes(data=True):
        if attrs.get("dimension_ref") == dim_id:
            return nid
    return None


def list_typed_edges(graph: nx.DiGraph, edge_type: str) -> list[tuple]:
    """Return all (src, tgt) tuples where edge.edge_type == edge_type."""
    return [
        (u, v)
        for u, v, data in graph.edges(data=True)
        if data.get("edge_type") == edge_type
    ]


__all__ = [
    "get_node_by_dimension_ref",
    "get_node_by_name",
    "list_typed_edges",
    "load_from_neo4j",
    "load_from_snapshot",
]
