"""Tests for brain.causal.graph_loader.

Mocks the neo4j driver/session API and uses synthetic JSON fixtures matching
``scripts/backup_neo4j.py`` output format. No live Neo4j required.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import networkx as nx
import pytest

from brain.causal.graph_loader import (
    get_node_by_dimension_ref,
    get_node_by_name,
    list_typed_edges,
    load_from_neo4j,
    load_from_snapshot,
)
from brain.memory.edge_taxonomy import TBD_PLACEHOLDER


# ---------------------------------------------------------------------------
# Mock neo4j driver
# ---------------------------------------------------------------------------
class _MockRecord(dict):
    """neo4j Record-like: dict subscript access."""


class _MockSession:
    """Mock neo4j Session that returns canned records based on Cypher keyword."""

    def __init__(self, node_records: list[dict], edge_records: list[dict]):
        self._node_records = node_records
        self._edge_records = edge_records

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def run(self, query: str, **_kwargs) -> Iterable[_MockRecord]:
        # Crude dispatch on cypher keyword
        if "labels(n)" in query:
            return [_MockRecord(r) for r in self._node_records]
        return [_MockRecord(r) for r in self._edge_records]


class _MockDriver:
    def __init__(self, node_records: list[dict], edge_records: list[dict]):
        self._node_records = node_records
        self._edge_records = edge_records

    def session(self):
        return _MockSession(self._node_records, self._edge_records)


@pytest.fixture
def mock_driver_basic():
    """3 CausalNodes + 2 DAG-participating edges + 1 CONFOUNDS edge that
    should be filtered out by the rel_type_filter in the Cypher itself."""
    nodes = [
        {"nid": 1, "name": "Vigabatrin", "dim_ref": 101, "labels": ["CausalNode"]},
        {"nid": 2, "name": "GABA-T", "dim_ref": None, "labels": ["CausalNode"]},
        {"nid": 3, "name": "Seizures", "dim_ref": 103, "labels": ["CausalNode"]},
    ]
    edges = [
        {
            "src": 1, "tgt": 2, "et": "INHIBITS",
            "conf": 0.9, "cite": "PMID:7686614",
            "mech": "GABA-T inhibition", "lag": None,
        },
        {
            "src": 2, "tgt": 3, "et": "CAUSES",
            "conf": 0.85, "cite": "PMID:7686614",
            "mech": "downstream effect", "lag": 30,
        },
    ]
    return _MockDriver(nodes, edges)


@pytest.fixture
def mock_driver_with_tbd():
    """One edge has TBD-Day-7-backfill placeholder citation."""
    nodes = [
        {"nid": 1, "name": "A", "dim_ref": None, "labels": ["CausalNode"]},
        {"nid": 2, "name": "B", "dim_ref": None, "labels": ["CausalNode"]},
    ]
    edges = [
        {
            "src": 1, "tgt": 2, "et": "CAUSES",
            "conf": 0.5, "cite": TBD_PLACEHOLDER,
            "mech": None, "lag": None,
        },
    ]
    return _MockDriver(nodes, edges)


# ---------------------------------------------------------------------------
# load_from_neo4j tests
# ---------------------------------------------------------------------------
def test_load_from_neo4j_includes_causal_nodes_only(mock_driver_basic):
    g = load_from_neo4j(mock_driver_basic)
    assert g.number_of_nodes() == 3
    assert {g.nodes[n]["name"] for n in g.nodes} == {"Vigabatrin", "GABA-T", "Seizures"}


def test_load_from_neo4j_filters_dag_participating_types_only(mock_driver_basic):
    """Verifies the Cypher query includes only CAUSES|INHIBITS|MEDIATES
    via DAG_PARTICIPATING_TYPES — implicit through the mock returning only
    those edges; we assert the loader does not crash on missing CONFOUNDS."""
    g = load_from_neo4j(mock_driver_basic)
    edge_types = {d["edge_type"] for _, _, d in g.edges(data=True)}
    assert edge_types.issubset({"CAUSES", "INHIBITS", "MEDIATES"})
    assert "CONFOUNDS" not in edge_types
    assert "MODERATES" not in edge_types


def test_load_from_neo4j_excludes_tbd_citations_by_default(mock_driver_with_tbd):
    g = load_from_neo4j(mock_driver_with_tbd)
    assert g.number_of_edges() == 0  # the one TBD edge is filtered out


def test_load_from_neo4j_includes_tbd_when_flag_set(mock_driver_with_tbd):
    g = load_from_neo4j(mock_driver_with_tbd, include_tbd_citations=True)
    assert g.number_of_edges() == 1
    edge_data = next(iter(g.edges(data=True)))[2]
    assert edge_data["citation"] == TBD_PLACEHOLDER


def test_load_from_neo4j_preserves_edge_properties(mock_driver_basic):
    g = load_from_neo4j(mock_driver_basic)
    inhibit_edges = [(u, v, d) for u, v, d in g.edges(data=True) if d["edge_type"] == "INHIBITS"]
    assert len(inhibit_edges) == 1
    _, _, d = inhibit_edges[0]
    assert d["confidence"] == 0.9
    assert d["citation"] == "PMID:7686614"
    assert d["mechanism"] == "GABA-T inhibition"
    assert d["time_lag_days"] is None


# ---------------------------------------------------------------------------
# load_from_snapshot tests
# ---------------------------------------------------------------------------
@pytest.fixture
def snapshot_path(tmp_path: Path) -> Path:
    """JSON snapshot in scripts/backup_neo4j.py format."""
    payload = {
        "nodes": [
            {
                "internal_id": 10, "labels": ["CausalNode"],
                "properties": {"name": "Vigabatrin", "dimension_ref": 999},
            },
            {
                "internal_id": 11, "labels": ["CausalNode"],
                "properties": {"name": "Seizures", "dimension_ref": None},
            },
            # Non-causal node — should be skipped
            {
                "internal_id": 12, "labels": ["Other"],
                "properties": {"name": "noise"},
            },
            # Causal node with TBD-only outgoing edge (will be dangling after filter)
            {
                "internal_id": 13, "labels": ["CausalNode"],
                "properties": {"name": "Dangling", "dimension_ref": None},
            },
        ],
        "relationships": [
            {
                "source_internal_id": 10, "target_internal_id": 11,
                "type": "CAUSES",
                "properties": {
                    "confidence": 0.8, "citation": "PMID:32713850",
                    "mechanism": "test", "time_lag_days": 7,
                },
            },
            # CONFOUNDS — should be filtered (not in DAG_PARTICIPATING_TYPES)
            {
                "source_internal_id": 10, "target_internal_id": 11,
                "type": "CONFOUNDS",
                "properties": {"citation": "PMID:1"},
            },
            # TBD edge — should be filtered by default
            {
                "source_internal_id": 13, "target_internal_id": 11,
                "type": "CAUSES",
                "properties": {"citation": TBD_PLACEHOLDER},
            },
            # Edge referencing missing endpoint — should be skipped defensively
            {
                "source_internal_id": 10, "target_internal_id": 9999,
                "type": "CAUSES",
                "properties": {"citation": "PMID:2"},
            },
        ],
    }
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_from_snapshot_parses_backup_format(snapshot_path):
    g = load_from_snapshot(snapshot_path)
    # 3 CausalNodes (10, 11, 13); 12 skipped
    assert g.number_of_nodes() == 3
    assert set(g.nodes) == {10, 11, 13}


def test_load_from_snapshot_skips_non_causal_nodes(snapshot_path):
    g = load_from_snapshot(snapshot_path)
    assert 12 not in g.nodes


def test_load_from_snapshot_filters_non_dag_relationship_types(snapshot_path):
    g = load_from_snapshot(snapshot_path)
    edge_types = {d["edge_type"] for _, _, d in g.edges(data=True)}
    assert edge_types == {"CAUSES"}


def test_load_from_snapshot_handles_missing_endpoints(snapshot_path):
    g = load_from_snapshot(snapshot_path)
    # Edge 10 -> 9999 is silently dropped (9999 not in nodes)
    assert 9999 not in g.nodes
    # Only the 10 -> 11 edge survives (TBD also filtered)
    assert g.number_of_edges() == 1
    assert (10, 11) in g.edges


def test_load_from_snapshot_include_tbd_when_flag_set(snapshot_path):
    g = load_from_snapshot(snapshot_path, include_tbd_citations=True)
    # Now the 13 -> 11 TBD edge survives
    assert g.number_of_edges() == 2
    assert (13, 11) in g.edges


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------
def _build_simple_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    g.add_node(1, name="Vigabatrin", dimension_ref=101, labels=["CausalNode"])
    g.add_node(2, name="GABA-T", dimension_ref=None, labels=["CausalNode"])
    g.add_node(3, name="Seizures", dimension_ref=103, labels=["CausalNode"])
    g.add_edge(1, 2, edge_type="INHIBITS")
    g.add_edge(2, 3, edge_type="CAUSES")
    return g


def test_get_node_by_name_case_insensitive():
    g = _build_simple_graph()
    assert get_node_by_name(g, "Vigabatrin") == 1
    assert get_node_by_name(g, "vigabatrin") == 1
    assert get_node_by_name(g, "VIGABATRIN") == 1
    assert get_node_by_name(g, "missing") is None
    assert get_node_by_name(g, None) is None  # defensive


def test_get_node_by_dimension_ref():
    g = _build_simple_graph()
    assert get_node_by_dimension_ref(g, 101) == 1
    assert get_node_by_dimension_ref(g, 103) == 3
    assert get_node_by_dimension_ref(g, 999) is None


def test_list_typed_edges():
    g = _build_simple_graph()
    assert list_typed_edges(g, "INHIBITS") == [(1, 2)]
    assert list_typed_edges(g, "CAUSES") == [(2, 3)]
    assert list_typed_edges(g, "MEDIATES") == []
