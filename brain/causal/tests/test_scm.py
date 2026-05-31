"""Tests for brain.causal.scm — SCM Pydantic spec + auto-builder + reference.

No live Neo4j; no live DoWhy estimation.
"""

from __future__ import annotations

import networkx as nx
import pytest

from brain.causal.scm import (
    SCM,
    SCMError,
    build_reference_scm,
    build_scm_from_graph,
)


# ---------------------------------------------------------------------------
# Graph fixtures
# ---------------------------------------------------------------------------
def _simple_confounded_graph() -> nx.DiGraph:
    """Z -> T -> Y; Z -> Y (Z is a confounder)."""
    g = nx.DiGraph()
    g.add_node(1, name="T", dimension_ref=None, labels=["CausalNode"])
    g.add_node(2, name="Y", dimension_ref=None, labels=["CausalNode"])
    g.add_node(3, name="Z", dimension_ref=None, labels=["CausalNode"])
    g.add_edge(3, 1, edge_type="CAUSES", citation="PMID:1")
    g.add_edge(1, 2, edge_type="CAUSES", citation="PMID:2")
    g.add_edge(3, 2, edge_type="CAUSES", citation="PMID:3")
    return g


def _mediated_graph() -> nx.DiGraph:
    """T -> M -> Y (M is a mediator)."""
    g = nx.DiGraph()
    g.add_node(1, name="T", dimension_ref=None, labels=["CausalNode"])
    g.add_node(2, name="M", dimension_ref=None, labels=["CausalNode"])
    g.add_node(3, name="Y", dimension_ref=None, labels=["CausalNode"])
    g.add_edge(1, 2, edge_type="CAUSES", citation="PMID:1")
    g.add_edge(2, 3, edge_type="CAUSES", citation="PMID:2")
    return g


def _disconnected_graph() -> nx.DiGraph:
    """T and Y in separate components."""
    g = nx.DiGraph()
    g.add_node(1, name="T", dimension_ref=None, labels=["CausalNode"])
    g.add_node(2, name="Y", dimension_ref=None, labels=["CausalNode"])
    return g


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------
def test_build_scm_rejects_missing_treatment_node():
    g = _simple_confounded_graph()
    with pytest.raises(SCMError, match="treatment"):
        build_scm_from_graph(g, treatment_name="nonexistent", outcome_name="Y")


def test_build_scm_rejects_missing_outcome_node():
    g = _simple_confounded_graph()
    with pytest.raises(SCMError, match="outcome"):
        build_scm_from_graph(g, treatment_name="T", outcome_name="nonexistent")


def test_scm_to_dowhy_graph_string_requires_graph():
    scm = SCM(name="x", treatment="T", outcome="Y", graph=None)
    with pytest.raises(SCMError, match="graph is None"):
        scm.to_dowhy_graph_string()


# ---------------------------------------------------------------------------
# DoWhy string
# ---------------------------------------------------------------------------
def test_scm_emits_dowhy_graph_string():
    scm = build_scm_from_graph(
        _simple_confounded_graph(), treatment_name="T", outcome_name="Y"
    )
    s = scm.to_dowhy_graph_string()
    assert s.startswith("digraph {")
    assert s.endswith("}")
    assert '"T" -> "Y"' in s
    assert '"Z" -> "T"' in s
    assert '"Z" -> "Y"' in s


# ---------------------------------------------------------------------------
# Confounder & mediator extraction
# ---------------------------------------------------------------------------
def test_build_scm_identifies_common_ancestor_confounders():
    scm = build_scm_from_graph(
        _simple_confounded_graph(), treatment_name="T", outcome_name="Y"
    )
    assert "Z" in scm.confounders


def test_build_scm_identifies_mediators_on_path():
    scm = build_scm_from_graph(
        _mediated_graph(), treatment_name="T", outcome_name="Y"
    )
    assert "M" in scm.mediators


def test_build_scm_excludes_treatment_from_confounders():
    scm = build_scm_from_graph(
        _simple_confounded_graph(), treatment_name="T", outcome_name="Y"
    )
    assert "T" not in scm.confounders


def test_build_scm_handles_treatment_outcome_with_no_path():
    """Disconnected components — no confounders, no mediators."""
    scm = build_scm_from_graph(
        _disconnected_graph(), treatment_name="T", outcome_name="Y"
    )
    assert scm.confounders == []
    assert scm.mediators == []


# ---------------------------------------------------------------------------
# Reference SCM
# ---------------------------------------------------------------------------
def test_build_reference_scm_returns_vigabatrin_to_seizure():
    scm = build_reference_scm()
    assert scm.treatment == "Vigabatrin"
    assert scm.outcome == "Seizure frequency"
    assert scm.name == "reference_vigabatrin_seizure"
    assert scm.graph is not None
    assert scm.graph.number_of_nodes() == 5


def test_reference_scm_has_age_as_confounder():
    scm = build_reference_scm()
    # Age is common ancestor of Vigabatrin (via direct edge) and Seizure frequency
    assert "Age (months)" in scm.confounders


def test_reference_scm_has_gaba_t_as_mediator():
    scm = build_reference_scm()
    # GABA-T is on path Vigabatrin -> GABA-T -> Seizure frequency
    assert "GABA-T enzyme" in scm.mediators


def test_reference_scm_dowhy_graph_string_includes_all_5_nodes():
    scm = build_reference_scm()
    s = scm.to_dowhy_graph_string()
    for node_name in [
        "Vigabatrin", "Seizure frequency", "Age (months)",
        "GABA-T enzyme", "Neuroplasticity window",
    ]:
        assert f'"{node_name}"' in s


def test_reference_scm_graph_is_acyclic():
    scm = build_reference_scm()
    assert nx.is_directed_acyclic_graph(scm.graph) is True


def test_reference_scm_default_name_when_not_supplied():
    g = _simple_confounded_graph()
    scm = build_scm_from_graph(g, treatment_name="T", outcome_name="Y")
    assert scm.name == "T_to_Y"


def test_scm_rejects_extra_fields():
    """Pydantic config extra='forbid' prevents typos."""
    with pytest.raises(Exception):
        SCM(name="x", treatment="T", outcome="Y", badfield="boom")


def test_scm_requires_non_empty_name():
    with pytest.raises(Exception):
        SCM(name="", treatment="T", outcome="Y")


def test_scm_requires_non_empty_treatment_and_outcome():
    with pytest.raises(Exception):
        SCM(name="x", treatment="", outcome="Y")
    with pytest.raises(Exception):
        SCM(name="x", treatment="T", outcome="")
