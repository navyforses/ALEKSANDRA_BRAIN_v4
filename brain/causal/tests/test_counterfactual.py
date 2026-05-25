"""Tests for brain.causal.counterfactual — structural linear extrapolation.

Reference SCM: Vigabatrin -> Seizure frequency (via GABA-T), with Age and
Neuroplasticity as confounders / mediators. Counterfactual semantics under
the structural linear surrogate must respect the sign:

    do(Vigabatrin=1) -> lower Seizure frequency
    do(Vigabatrin=0) -> higher Seizure frequency
"""

from __future__ import annotations

import warnings

import networkx as nx
import pytest

warnings.filterwarnings("ignore", category=DeprecationWarning)

from brain.causal.counterfactual import counterfactual_predict
from brain.causal.dowhy_bootstrap import synthetic_data_for_reference_scm
from brain.causal.scm import SCM, SCMError, build_reference_scm


# ---------------------------------------------------------------------------
# Sign sanity — do(treatment=1) reduces seizure freq
# ---------------------------------------------------------------------------
def test_do_vigabatrin_on_lowers_predicted_seizure_freq():
    scm = build_reference_scm()
    df = synthetic_data_for_reference_scm(n=300, random_seed=7)
    factual = {
        "Vigabatrin": 0.0,
        "Age (months)": 10.0,
        "GABA-T enzyme": 1.0,
        "Neuroplasticity window": 0.61,
        "Seizure frequency": 2.0,
    }
    treated = counterfactual_predict(
        scm,
        factual=factual,
        intervention={"Vigabatrin": 1.0, "GABA-T enzyme": 0.3},
        outcome="Seizure frequency",
        data=df,
    )
    untreated = counterfactual_predict(
        scm,
        factual=factual,
        intervention={"Vigabatrin": 0.0, "GABA-T enzyme": 1.0},
        outcome="Seizure frequency",
        data=df,
    )
    assert treated["predicted_outcome"] < untreated["predicted_outcome"], (
        f"expected do(Vigabatrin=1) -> lower predicted seizures than do(Vigabatrin=0); "
        f"got treated={treated}, untreated={untreated}"
    )
    assert treated["method"] == "structural_linear_extrapolation"


# ---------------------------------------------------------------------------
# Empty intervention -> ValueError
# ---------------------------------------------------------------------------
def test_empty_intervention_raises_value_error():
    scm = build_reference_scm()
    df = synthetic_data_for_reference_scm(n=100, random_seed=7)
    factual = {"Vigabatrin": 0.0, "Seizure frequency": 2.0}
    with pytest.raises(ValueError, match="non-empty"):
        counterfactual_predict(
            scm,
            factual=factual,
            intervention={},
            outcome="Seizure frequency",
            data=df,
        )


# ---------------------------------------------------------------------------
# Unknown variable in intervention -> ValueError
# ---------------------------------------------------------------------------
def test_unknown_variable_in_intervention_raises():
    scm = build_reference_scm()
    df = synthetic_data_for_reference_scm(n=100, random_seed=7)
    factual = {"Vigabatrin": 0.0, "Seizure frequency": 2.0}
    with pytest.raises(ValueError, match="not a node in scm.graph"):
        counterfactual_predict(
            scm,
            factual=factual,
            intervention={"Antimatter exposure": 99.0},
            outcome="Seizure frequency",
            data=df,
        )


# ---------------------------------------------------------------------------
# Unknown variable in factual -> ValueError
# ---------------------------------------------------------------------------
def test_unknown_variable_in_factual_raises():
    scm = build_reference_scm()
    df = synthetic_data_for_reference_scm(n=100, random_seed=7)
    factual = {"Unicorn count": 5.0}
    with pytest.raises(ValueError, match="not a node in scm.graph"):
        counterfactual_predict(
            scm,
            factual=factual,
            intervention={"Vigabatrin": 1.0},
            outcome="Seizure frequency",
            data=df,
        )


# ---------------------------------------------------------------------------
# Predicted outcome is finite + method tag
# ---------------------------------------------------------------------------
def test_predicted_outcome_is_finite():
    scm = build_reference_scm()
    df = synthetic_data_for_reference_scm(n=200, random_seed=7)
    result = counterfactual_predict(
        scm,
        factual={
            "Vigabatrin": 0.0,
            "Age (months)": 8.0,
            "Seizure frequency": 2.1,
        },
        intervention={"Vigabatrin": 1.0, "GABA-T enzyme": 0.3},
        outcome="Seizure frequency",
        data=df,
    )
    import math
    assert math.isfinite(result["predicted_outcome"])
    assert math.isfinite(result["delta_vs_factual"])
    assert result["method"] == "structural_linear_extrapolation"


# ---------------------------------------------------------------------------
# outcome mismatch with scm.outcome -> ValueError
# ---------------------------------------------------------------------------
def test_outcome_mismatch_raises_value_error():
    scm = build_reference_scm()
    df = synthetic_data_for_reference_scm(n=100, random_seed=7)
    with pytest.raises(ValueError, match="does not match scm.outcome"):
        counterfactual_predict(
            scm,
            factual={"Vigabatrin": 0.0},
            intervention={"Vigabatrin": 1.0},
            outcome="GABA-T enzyme",
            data=df,
        )


# ---------------------------------------------------------------------------
# Cyclic graph rejection
# ---------------------------------------------------------------------------
def test_cyclic_scm_graph_rejected():
    cyclic = nx.DiGraph()
    cyclic.add_node(1, name="A")
    cyclic.add_node(2, name="B")
    cyclic.add_edge(1, 2)
    cyclic.add_edge(2, 1)
    scm = SCM(name="cyc", treatment="A", outcome="B", graph=cyclic)
    import pandas as pd
    df = pd.DataFrame({"A": [0.0, 1.0], "B": [1.0, 2.0]})
    with pytest.raises(SCMError, match="not a DAG"):
        counterfactual_predict(
            scm,
            factual={"A": 0.0},
            intervention={"A": 1.0},
            outcome="B",
            data=df,
        )
