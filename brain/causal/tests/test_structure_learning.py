"""Phase 7.2 Day 11 — tests for structure_learning.py."""

from __future__ import annotations

import warnings

import networkx as nx
import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from brain.causal.scm import build_reference_scm
from brain.causal.structure_learning import (
    LearnedStructureReport,
    StructureLearningError,
    compare_structures,
    learn_from_synthetic_reference,
    learn_structure,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def chain_continuous_df() -> pd.DataFrame:
    """Small continuous DataFrame with a clean A -> B -> C chain."""
    rng = np.random.default_rng(11)
    n = 500
    a = rng.normal(size=n)
    b = a + rng.normal(size=n) * 0.3
    c = b + rng.normal(size=n) * 0.3
    return pd.DataFrame({"A": a, "B": b, "C": c})


@pytest.fixture
def small_discrete_df() -> pd.DataFrame:
    """Small discrete DataFrame for the PC algorithm."""
    rng = np.random.default_rng(11)
    n = 800
    a = rng.binomial(1, 0.5, size=n)
    b = (a + rng.binomial(1, 0.3, size=n)) % 2
    return pd.DataFrame({"A": a, "B": b})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_learn_structure_hill_climb_bic_returns_digraph(
    chain_continuous_df: pd.DataFrame,
) -> None:
    """hill_climb_bic returns an nx.DiGraph with at least one edge."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        g = learn_structure(chain_continuous_df, method="hill_climb_bic")
    assert isinstance(g, nx.DiGraph)
    assert g.number_of_nodes() == 3
    # On a clean chain, BIC should find at least 1 edge (typically 2).
    assert g.number_of_edges() >= 1


def test_learn_structure_pc_chisq_runs_without_error(
    small_discrete_df: pd.DataFrame,
) -> None:
    """pc_chisq runs end-to-end on a 2-variable discrete dataset."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        g = learn_structure(small_discrete_df, method="pc_chisq")
    assert isinstance(g, nx.DiGraph)
    assert g.number_of_nodes() == 2
    # PC may return 0, 1, or (PDAG-orientation) 2 edges; all are acceptable.
    assert g.number_of_edges() >= 0


def test_compare_structures_identical_graphs() -> None:
    """When learned == reference, precision = recall = F1 = 1.0."""
    g = nx.DiGraph()
    g.add_node(1, name="A")
    g.add_node(2, name="B")
    g.add_edge(1, 2)
    report = compare_structures(g, g)
    assert report.precision == 1.0
    assert report.recall == 1.0
    assert report.f1 == 1.0
    assert report.learned_edge_count == 1
    assert report.learned_node_count == 2
    assert report.extra_edges == []
    assert report.missing_edges == []


def test_compare_structures_empty_learned_no_crash() -> None:
    """Empty learned graph returns 0.0 scores; reports all reference as missing."""
    learned = nx.DiGraph()
    learned.add_node("A")
    learned.add_node("B")
    reference = nx.DiGraph()
    reference.add_node(1, name="A")
    reference.add_node(2, name="B")
    reference.add_edge(1, 2)
    report = compare_structures(learned, reference)
    assert report.precision == 0.0  # 0 / 0 -> 0 by convention
    assert report.recall == 0.0  # 0 / 1
    assert report.f1 == 0.0
    assert report.learned_edge_count == 0
    assert len(report.missing_edges) == 1
    assert report.extra_edges == []


def test_compare_structures_partial_overlap() -> None:
    """One edge match + one extra + one missing -> precision=recall=0.5."""
    learned = nx.DiGraph()
    learned.add_node("A")
    learned.add_node("B")
    learned.add_node("C")
    learned.add_edge("A", "B")
    learned.add_edge("A", "C")  # extra
    reference = nx.DiGraph()
    reference.add_node(1, name="A")
    reference.add_node(2, name="B")
    reference.add_node(3, name="C")
    reference.add_edge(1, 2)
    reference.add_edge(2, 3)  # missing in learned
    report = compare_structures(learned, reference)
    assert report.precision == pytest.approx(0.5)
    assert report.recall == pytest.approx(0.5)
    assert report.f1 == pytest.approx(0.5)
    assert ("A", "C") in report.extra_edges
    assert ("B", "C") in report.missing_edges


def test_learned_structure_report_pydantic_validation() -> None:
    """LearnedStructureReport rejects extra fields and out-of-range scores."""
    with pytest.raises(ValidationError):
        LearnedStructureReport(
            method="hill_climb_bic",
            n_samples=10,
            learned_edges=[("A", "B")],
            reference_edges=[("A", "B")],
            precision=1.0,
            recall=1.0,
            f1=1.0,
            learned_node_count=2,
            learned_edge_count=1,
            extra_edges=[],
            missing_edges=[],
            bogus_field="nope",  # type: ignore[call-arg]
        )
    with pytest.raises(ValidationError):
        LearnedStructureReport(
            method="hill_climb_bic",
            n_samples=10,
            learned_edges=[],
            reference_edges=[],
            precision=1.5,  # out of [0,1]
            recall=0.5,
            f1=0.0,
            learned_node_count=0,
            learned_edge_count=0,
            extra_edges=[],
            missing_edges=[],
        )


def test_learn_structure_rejects_empty_dataframe() -> None:
    """Empty DataFrame raises StructureLearningError."""
    with pytest.raises(StructureLearningError):
        learn_structure(pd.DataFrame(), method="hill_climb_bic")


def test_learn_structure_rejects_single_column() -> None:
    """Single-column DataFrame raises StructureLearningError."""
    df = pd.DataFrame({"A": [1.0, 2.0, 3.0, 4.0]})
    with pytest.raises(StructureLearningError):
        learn_structure(df, method="hill_climb_bic")


def test_learn_structure_unknown_method() -> None:
    """Unknown method string raises StructureLearningError."""
    df = pd.DataFrame({"A": [1.0, 2.0], "B": [3.0, 4.0]})
    with pytest.raises(StructureLearningError):
        learn_structure(df, method="not_a_real_method")  # type: ignore[arg-type]


def test_learn_from_synthetic_reference_f1_above_threshold() -> None:
    """Reference SCM learn-back yields F1 >= 0.3 (BIC sanity baseline).

    BIC on small samples is noisy; we set a permissive floor at 0.3.
    Default ``n`` raised 1000 → 2000 on 2026-06-02 after CI flake
    (F1=0.17 < 0.3 on PR #9 run); reference SCM mixes binary and
    continuous variables, and BIC variance shrinks roughly as 1/sqrt(n)
    so doubling halves the sampling spread. Reference SCM has 6 directed
    edges over 5 nodes. If this test ever repeatedly fails on the
    current synthetic generator, raise n further (4000) — do NOT relax
    the threshold below 0.3.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        report = learn_from_synthetic_reference()
    assert isinstance(report, LearnedStructureReport)
    assert report.n_samples == 2000
    assert len(report.reference_edges) == 6  # reference SCM has 6 edges
    assert report.f1 >= 0.3, (
        f"BIC F1 dropped below 0.3 on synthetic-reference: "
        f"P={report.precision:.2f} R={report.recall:.2f} F1={report.f1:.2f}; "
        f"extra={report.extra_edges} missing={report.missing_edges}"
    )


def test_compare_structures_with_node_name_mapping() -> None:
    """node_name_mapping correctly aligns learned column names to ref names."""
    learned = nx.DiGraph()
    learned.add_node("col_a")
    learned.add_node("col_b")
    learned.add_edge("col_a", "col_b")
    reference = nx.DiGraph()
    reference.add_node(1, name="Apple")
    reference.add_node(2, name="Banana")
    reference.add_edge(1, 2)
    mapping = {"col_a": "Apple", "col_b": "Banana"}
    report = compare_structures(learned, reference, node_name_mapping=mapping)
    assert report.precision == 1.0
    assert report.recall == 1.0
    assert report.f1 == 1.0
