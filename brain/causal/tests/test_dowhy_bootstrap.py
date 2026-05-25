"""Tests for brain.causal.dowhy_bootstrap — DoWhy CausalModel wrapper.

Only runs *identification* (cheap, deterministic) — no sampling estimators,
no estimate refutation. End-to-end identification on the reference SCM is
the deepest test.
"""

from __future__ import annotations

import networkx as nx
import pandas as pd
import pytest

from brain.causal.dowhy_bootstrap import (
    build_causal_model,
    identify_effect,
    synthetic_data_for_reference_scm,
)
from brain.causal.scm import SCM, SCMError, build_reference_scm


# ---------------------------------------------------------------------------
# build_causal_model error paths
# ---------------------------------------------------------------------------
def test_build_causal_model_rejects_missing_columns():
    scm = build_reference_scm()
    # Missing the outcome column
    bad_df = pd.DataFrame(
        {
            "Vigabatrin": [0.0, 1.0],
            "Age (months)": [3.0, 12.0],
            "GABA-T enzyme": [1.0, 0.3],
            "Neuroplasticity window": [0.86, 0.55],
        }
    )
    with pytest.raises(SCMError, match="missing required columns"):
        build_causal_model(scm, bad_df)


def test_build_causal_model_rejects_cyclic_graph():
    # Construct a deliberately cyclic graph and wrap in an SCM
    cyclic = nx.DiGraph()
    cyclic.add_node(1, name="A")
    cyclic.add_node(2, name="B")
    cyclic.add_edge(1, 2, edge_type="CAUSES")
    cyclic.add_edge(2, 1, edge_type="CAUSES")  # cycle
    scm = SCM(name="bad", treatment="A", outcome="B", graph=cyclic)
    df = pd.DataFrame({"A": [0.0, 1.0], "B": [1.0, 2.0]})
    with pytest.raises(SCMError, match="not a DAG"):
        build_causal_model(scm, df)


def test_build_causal_model_rejects_missing_graph():
    scm = SCM(name="x", treatment="T", outcome="Y", graph=None)
    df = pd.DataFrame({"T": [0.0, 1.0], "Y": [1.0, 2.0]})
    with pytest.raises(SCMError, match="graph is None"):
        build_causal_model(scm, df)


# ---------------------------------------------------------------------------
# build_causal_model happy path on reference SCM
# ---------------------------------------------------------------------------
def test_build_causal_model_with_reference_scm_succeeds():
    scm = build_reference_scm()
    df = synthetic_data_for_reference_scm(n=100)
    model = build_causal_model(scm, df)
    # CausalModel duck-typing — has identify_effect method
    assert hasattr(model, "identify_effect")


# ---------------------------------------------------------------------------
# identify_effect
# ---------------------------------------------------------------------------
def test_identify_effect_returns_structured_dict():
    scm = build_reference_scm()
    df = synthetic_data_for_reference_scm(n=100)
    model = build_causal_model(scm, df)
    result = identify_effect(model)
    assert set(result.keys()) >= {
        "estimand_type",
        "backdoor_variables",
        "instrumental_variables",
        "frontdoor_variables",
        "estimand_str",
    }
    assert isinstance(result["backdoor_variables"], list)


def test_identify_effect_finds_age_as_backdoor_variable():
    """Age is the only true confounder of Vigabatrin -> Seizure frequency in
    the reference SCM; DoWhy's backdoor identification should pick it up."""
    scm = build_reference_scm()
    df = synthetic_data_for_reference_scm(n=100)
    model = build_causal_model(scm, df)
    result = identify_effect(model)
    backdoor = result["backdoor_variables"]
    # DoWhy may return the variable name with spaces preserved
    assert any("age" in v.lower() for v in backdoor), (
        f"expected Age in backdoor set, got {backdoor!r}"
    )


# ---------------------------------------------------------------------------
# synthetic_data_for_reference_scm
# ---------------------------------------------------------------------------
def test_synthetic_data_has_expected_columns():
    df = synthetic_data_for_reference_scm(n=50)
    expected = {
        "Vigabatrin", "Seizure frequency", "Age (months)",
        "GABA-T enzyme", "Neuroplasticity window",
    }
    assert set(df.columns) == expected
    assert len(df) == 50


def test_synthetic_data_seed_is_deterministic():
    df1 = synthetic_data_for_reference_scm(n=50, random_seed=42)
    df2 = synthetic_data_for_reference_scm(n=50, random_seed=42)
    pd.testing.assert_frame_equal(df1, df2)


def test_synthetic_data_different_seeds_differ():
    df1 = synthetic_data_for_reference_scm(n=50, random_seed=1)
    df2 = synthetic_data_for_reference_scm(n=50, random_seed=2)
    # At least some Vigabatrin values must differ (treatment is stochastic)
    assert not df1["Vigabatrin"].equals(df2["Vigabatrin"])


def test_synthetic_data_vigabatrin_is_binary():
    df = synthetic_data_for_reference_scm(n=200)
    assert set(df["Vigabatrin"].unique()).issubset({0.0, 1.0})


def test_synthetic_data_seizure_freq_non_negative():
    df = synthetic_data_for_reference_scm(n=200)
    assert (df["Seizure frequency"] >= 0.0).all()


def test_synthetic_data_treatment_outcome_correlation_is_negative():
    """Vigabatrin should reduce seizure frequency on average. The marginal
    correlation may be biased by the Age confounder (older infants both
    more likely to be treated AND have higher baseline seizure freq), but
    the *conditional* correlation given Age should be clearly negative."""
    df = synthetic_data_for_reference_scm(n=500, random_seed=7)
    # Stratify on age tertile and check Vigabatrin coefficient sign within
    # the middle tertile (where both treated + untreated subjects exist)
    age = df["Age (months)"]
    q1, q2 = age.quantile([1 / 3, 2 / 3])
    mid = df[(age >= q1) & (age <= q2)]
    treated = mid[mid["Vigabatrin"] == 1.0]["Seizure frequency"].mean()
    untreated = mid[mid["Vigabatrin"] == 0.0]["Seizure frequency"].mean()
    # In the middle age stratum, treated should have lower seizure freq
    assert treated < untreated, (
        f"expected treated < untreated within mid-age stratum, "
        f"got treated={treated:.3f}, untreated={untreated:.3f}"
    )


# ---------------------------------------------------------------------------
# End-to-end reference pipeline
# ---------------------------------------------------------------------------
def test_end_to_end_reference_pipeline():
    """SCM -> data -> CausalModel -> identified estimand has Age in backdoor."""
    scm = build_reference_scm()
    assert "Age (months)" in scm.confounders  # SCM-level
    df = synthetic_data_for_reference_scm(n=200, random_seed=7)
    model = build_causal_model(scm, df)
    result = identify_effect(model)
    # DoWhy-level: Age should be identified as a backdoor variable too
    assert any("age" in v.lower() for v in result["backdoor_variables"])
    # estimand_str should be non-empty
    assert len(result["estimand_str"]) > 0
