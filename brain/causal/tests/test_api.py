"""Tests for brain.causal.api — handler-level contract for do() + counterfactual.

These tests exercise the pure-function handlers (no HTTP, no FastAPI).
They confirm:

    - Request / response Pydantic models round-trip via model_dump /
      model_validate (this is the serialisation surface any framework
      adapter will exercise).
    - handle_do_query returns negative effect on the reference SCM
      and refuses treatment/outcome mismatches.
    - handle_counterfactual_query delegates correctly and rejects
      unknown variables.
"""

from __future__ import annotations

import warnings

import pytest
from pydantic import ValidationError

warnings.filterwarnings("ignore", category=DeprecationWarning)

from brain.causal.api import (
    CounterfactualRequest,
    CounterfactualResponse,
    DoQueryRequest,
    DoQueryResponse,
    handle_counterfactual_query,
    handle_do_query,
)
from brain.causal.dowhy_bootstrap import synthetic_data_for_reference_scm
from brain.causal.scm import build_reference_scm


# ---------------------------------------------------------------------------
# do-query — happy path on reference SCM
# ---------------------------------------------------------------------------
def test_handle_do_query_returns_negative_effect_in_window():
    scm = build_reference_scm()
    df = synthetic_data_for_reference_scm(n=300, random_seed=7)
    req = DoQueryRequest(
        scm_name="reference_vigabatrin_seizure",
        treatment="Vigabatrin",
        treatment_value=1.0,
        outcome="Seizure frequency",
        method="linear_regression",
        confidence_level=0.95,
        units="seizures/day",
    )
    resp = handle_do_query(req, scm=scm, data=df)
    assert isinstance(resp, DoQueryResponse)
    assert resp.method == "linear_regression"
    # Vigabatrin reduces seizures: spec calls for -1.5 .. -0.1
    assert -1.5 <= resp.effect <= -0.1, (
        f"expected effect in [-1.5, -0.1], got {resp.effect}"
    )
    assert resp.units == "seizures/day"
    assert resp.n_samples == 300
    assert resp.ci_low is not None and resp.ci_high is not None
    assert resp.ci_low <= resp.effect <= resp.ci_high
    assert len(resp.identified_estimand) > 0


# ---------------------------------------------------------------------------
# do-query — treatment / outcome mismatch
# ---------------------------------------------------------------------------
def test_handle_do_query_rejects_treatment_mismatch():
    scm = build_reference_scm()
    df = synthetic_data_for_reference_scm(n=50, random_seed=7)
    req = DoQueryRequest(
        scm_name="reference_vigabatrin_seizure",
        treatment="GABA-T enzyme",  # not scm.treatment
        treatment_value=0.3,
        outcome="Seizure frequency",
    )
    with pytest.raises(ValueError, match="treatment"):
        handle_do_query(req, scm=scm, data=df)


def test_handle_do_query_rejects_outcome_mismatch():
    scm = build_reference_scm()
    df = synthetic_data_for_reference_scm(n=50, random_seed=7)
    req = DoQueryRequest(
        scm_name="reference_vigabatrin_seizure",
        treatment="Vigabatrin",
        treatment_value=1.0,
        outcome="GABA-T enzyme",  # not scm.outcome
    )
    with pytest.raises(ValueError, match="outcome"):
        handle_do_query(req, scm=scm, data=df)


# ---------------------------------------------------------------------------
# counterfactual handler — happy path
# ---------------------------------------------------------------------------
def test_handle_counterfactual_returns_finite_outcome():
    scm = build_reference_scm()
    df = synthetic_data_for_reference_scm(n=200, random_seed=7)
    req = CounterfactualRequest(
        scm_name="reference_vigabatrin_seizure",
        factual={
            "Vigabatrin": 0.0,
            "Age (months)": 10.0,
            "Seizure frequency": 2.1,
        },
        intervention={"Vigabatrin": 1.0, "GABA-T enzyme": 0.3},
        outcome="Seizure frequency",
    )
    resp = handle_counterfactual_query(req, scm=scm, data=df)
    assert isinstance(resp, CounterfactualResponse)
    import math
    assert math.isfinite(resp.predicted_outcome)
    assert math.isfinite(resp.delta_vs_factual)
    assert resp.method == "structural_linear_extrapolation"


# ---------------------------------------------------------------------------
# Counterfactual unknown variable in intervention
# ---------------------------------------------------------------------------
def test_counterfactual_request_unknown_variable_raises():
    scm = build_reference_scm()
    df = synthetic_data_for_reference_scm(n=100, random_seed=7)
    req = CounterfactualRequest(
        scm_name="reference_vigabatrin_seizure",
        factual={"Vigabatrin": 0.0},
        intervention={"Nonexistent variable": 1.0},
        outcome="Seizure frequency",
    )
    with pytest.raises(ValueError, match="not a node in scm.graph"):
        handle_counterfactual_query(req, scm=scm, data=df)


# ---------------------------------------------------------------------------
# Round-trip serialization
# ---------------------------------------------------------------------------
def test_do_query_models_roundtrip():
    req = DoQueryRequest(
        scm_name="reference_vigabatrin_seizure",
        treatment="Vigabatrin",
        treatment_value=1.0,
        outcome="Seizure frequency",
        method="propensity_score_matching",
        confidence_level=0.9,
        units="seizures/day",
    )
    dumped = req.model_dump()
    rebuilt = DoQueryRequest.model_validate(dumped)
    assert rebuilt == req

    resp = DoQueryResponse(
        effect=-0.5,
        ci_low=-0.7,
        ci_high=-0.3,
        units="seizures/day",
        method="linear_regression",
        n_samples=200,
        identified_estimand="E[Y|do(T=1)]",
        refutation={"random_common_cause": "passed"},
    )
    dumped_r = resp.model_dump()
    rebuilt_r = DoQueryResponse.model_validate(dumped_r)
    assert rebuilt_r == resp


def test_counterfactual_models_roundtrip():
    req = CounterfactualRequest(
        scm_name="reference_vigabatrin_seizure",
        factual={"Vigabatrin": 0.0, "Age (months)": 10.0},
        intervention={"Vigabatrin": 1.0},
        outcome="Seizure frequency",
    )
    rebuilt = CounterfactualRequest.model_validate(req.model_dump())
    assert rebuilt == req

    resp = CounterfactualResponse(
        predicted_outcome=1.42,
        delta_vs_factual=-0.58,
        method="structural_linear_extrapolation",
    )
    rebuilt_r = CounterfactualResponse.model_validate(resp.model_dump())
    assert rebuilt_r == resp


# ---------------------------------------------------------------------------
# Extra-field rejection on request models
# ---------------------------------------------------------------------------
def test_do_query_request_rejects_extras():
    with pytest.raises(ValidationError):
        DoQueryRequest(  # type: ignore[call-arg]
            scm_name="x",
            treatment="t",
            treatment_value=1.0,
            outcome="y",
            bogus_field="nope",
        )
