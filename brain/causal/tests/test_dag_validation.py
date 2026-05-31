"""Tests for brain.causal.dag_validation.

Uses purely synthetic NetworkX DiGraphs — no neo4j, no DoWhy.
"""

from __future__ import annotations

import networkx as nx
import pytest

from brain.causal.dag_validation import (
    DAGReport,
    build_dag_report,
    format_report,
)
from brain.memory.edge_taxonomy import TBD_PLACEHOLDER


def _empty_graph() -> nx.DiGraph:
    return nx.DiGraph()


def _acyclic_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    g.add_node(1, name="A", dimension_ref=10, labels=["CausalNode"])
    g.add_node(2, name="B", dimension_ref=None, labels=["CausalNode"])
    g.add_node(3, name="C", dimension_ref=20, labels=["CausalNode"])
    g.add_edge(1, 2, edge_type="CAUSES", citation="PMID:1")
    g.add_edge(2, 3, edge_type="INHIBITS", citation="PMID:2")
    return g


def _cyclic_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    for nid in (1, 2, 3):
        g.add_node(nid, name=f"N{nid}", dimension_ref=None, labels=["CausalNode"])
    g.add_edge(1, 2, edge_type="CAUSES", citation="PMID:1")
    g.add_edge(2, 3, edge_type="CAUSES", citation="PMID:2")
    g.add_edge(3, 1, edge_type="CAUSES", citation="PMID:3")
    return g


# ---------------------------------------------------------------------------
# Empty + acyclic baseline
# ---------------------------------------------------------------------------
def test_dag_report_on_empty_graph():
    report = build_dag_report(_empty_graph())
    assert report.node_count == 0
    assert report.edge_count == 0
    assert report.is_acyclic is True  # vacuously
    assert report.cycle_examples == []
    assert report.weakly_connected_components == 0
    assert report.largest_wcc_size == 0
    assert report.dangling_node_count == 0
    assert report.edge_type_counts == {}
    assert report.citation_complete_count == 0
    assert report.citation_complete_rate == 0.0
    assert report.tbd_backlog_count == 0
    assert report.dimension_ref_populated_rate == 0.0


def test_dag_report_acyclic_pass():
    report = build_dag_report(_acyclic_graph())
    assert report.is_acyclic is True
    assert report.cycle_examples == []
    assert report.node_count == 3
    assert report.edge_count == 2


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------
def test_dag_report_catches_simple_cycle():
    report = build_dag_report(_cyclic_graph())
    assert report.is_acyclic is False
    assert len(report.cycle_examples) >= 1
    # First cycle should have 3 nodes
    assert len(report.cycle_examples[0]) == 3


# ---------------------------------------------------------------------------
# Connectivity
# ---------------------------------------------------------------------------
def test_dag_report_counts_wccs():
    g = _acyclic_graph()
    # Add an isolated 2-node component
    g.add_node(10, name="X", dimension_ref=None, labels=["CausalNode"])
    g.add_node(11, name="Y", dimension_ref=None, labels=["CausalNode"])
    g.add_edge(10, 11, edge_type="CAUSES", citation="PMID:99")
    report = build_dag_report(g)
    assert report.weakly_connected_components == 2
    assert report.largest_wcc_size == 3  # original A-B-C chain


def test_dag_report_finds_dangling_nodes():
    g = _acyclic_graph()
    # Dangling nodes
    g.add_node(99, name="orphan", dimension_ref=None, labels=["CausalNode"])
    g.add_node(100, name="orphan2", dimension_ref=None, labels=["CausalNode"])
    report = build_dag_report(g)
    assert report.dangling_node_count == 2
    assert set(report.dangling_node_names) == {"orphan", "orphan2"}


# ---------------------------------------------------------------------------
# Edge-type distribution + citation completeness
# ---------------------------------------------------------------------------
def test_dag_report_edge_type_distribution():
    g = _acyclic_graph()
    report = build_dag_report(g)
    assert report.edge_type_counts == {"CAUSES": 1, "INHIBITS": 1}


def test_dag_report_citation_completeness_excludes_tbd():
    g = nx.DiGraph()
    g.add_node(1, name="A", dimension_ref=None, labels=["CausalNode"])
    g.add_node(2, name="B", dimension_ref=None, labels=["CausalNode"])
    g.add_node(3, name="C", dimension_ref=None, labels=["CausalNode"])
    g.add_edge(1, 2, edge_type="CAUSES", citation="PMID:1")
    g.add_edge(2, 3, edge_type="CAUSES", citation=TBD_PLACEHOLDER)
    report = build_dag_report(g)
    assert report.citation_complete_count == 1
    assert report.citation_complete_rate == 0.5
    assert report.tbd_backlog_count == 1


def test_dag_report_tbd_backlog_counted_separately():
    g = nx.DiGraph()
    g.add_node(1, name="A", dimension_ref=None, labels=["CausalNode"])
    g.add_node(2, name="B", dimension_ref=None, labels=["CausalNode"])
    g.add_edge(1, 2, edge_type="CAUSES", citation=TBD_PLACEHOLDER)
    report = build_dag_report(g)
    # TBD does NOT count toward completion
    assert report.citation_complete_count == 0
    assert report.tbd_backlog_count == 1


# ---------------------------------------------------------------------------
# dimension_ref population
# ---------------------------------------------------------------------------
def test_dag_report_dimension_ref_rate():
    g = _acyclic_graph()  # 2 of 3 nodes have dimension_ref set (10, 20)
    report = build_dag_report(g)
    assert report.dimension_ref_populated_count == 2
    assert report.dimension_ref_populated_rate == pytest.approx(2 / 3)


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
def test_format_report_renders_human_readable():
    report = build_dag_report(_acyclic_graph())
    text = format_report(report)
    assert "DAG Quality Report" in text
    assert "Nodes:" in text
    assert "Edges:" in text
    assert "Acyclic:" in text
    assert "True" in text
    # Cycle line should NOT appear for acyclic graph
    assert "Cycle examples" not in text


def test_format_report_renders_cycle_line_when_cyclic():
    report = build_dag_report(_cyclic_graph())
    text = format_report(report)
    assert "Cycle examples" in text
