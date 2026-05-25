"""Tests for brain.causal.estimators — DoWhy effect-estimator wrapper.

Uses the reference SCM (Vigabatrin -> Seizure frequency) + 300-row synthetic
data for deterministic, PHI-free assertions. The marginal causal effect of
Vigabatrin is structurally negative (Vigabatrin lowers seizure frequency),
so every well-identified estimate must come out negative.
"""

from __future__ import annotations

import warnings

import pytest
from pydantic import ValidationError

# Silence the well-known DoWhy / pyparsing / statsmodels deprecation noise
warnings.filterwarnings("ignore", category=DeprecationWarning)

from brain.causal.dowhy_bootstrap import (
    build_causal_model,
    identify_effect,
    synthetic_data_for_reference_scm,
)
from brain.causal.estimators import (
    EstimateResult,
    EstimationError,
    estimate_effect,
)
from brain.causal.scm import build_reference_scm


# ---------------------------------------------------------------------------
# Fixture helper
# ---------------------------------------------------------------------------
def _build_reference_model(n: int = 300, seed: int = 7):
    scm = build_reference_scm()
    df = synthetic_data_for_reference_scm(n=n, random_seed=seed)
    model = build_causal_model(scm, df)
    estimand = identify_effect(model)
    return model, estimand


# ---------------------------------------------------------------------------
# linear_regression
# ---------------------------------------------------------------------------
def test_linear_regression_returns_negative_effect_on_reference_scm():
    model, estimand = _build_reference_model()
    result = estimate_effect(model, estimand, "linear_regression",
                             units="seizures/day")
    assert isinstance(result, EstimateResult)
    assert result.method == "linear_regression"
    assert result.units == "seizures/day"
    # Vigabatrin reduces seizures structurally: effect must be < 0
    assert result.effect < 0.0, (
        f"expected negative ATE for Vigabatrin -> Seizure freq, "
        f"got {result.effect}"
    )
    assert result.n_samples == 300
    # CI brackets the point estimate
    assert result.ci_low is not None and result.ci_high is not None
    assert result.ci_low <= result.effect <= result.ci_high


# ---------------------------------------------------------------------------
# propensity_score_matching
# ---------------------------------------------------------------------------
def test_psm_returns_negative_effect_on_reference_scm():
    model, estimand = _build_reference_model()
    result = estimate_effect(model, estimand, "propensity_score_matching")
    assert result.method == "propensity_score_matching"
    assert result.effect < 0.0
    # PSM ATE on this DGP should be in roughly the [-1.5, -0.1] window
    assert -1.5 <= result.effect <= -0.1


# ---------------------------------------------------------------------------
# instrumental_variable — refused when no IV present
# ---------------------------------------------------------------------------
def test_iv_raises_estimation_error_when_no_instrument_in_graph():
    model, estimand = _build_reference_model()
    # Reference SCM has empty instrumental_variables
    assert estimand["instrumental_variables"] == []
    with pytest.raises(EstimationError, match="no instrumental variables"):
        estimate_effect(model, estimand, "instrumental_variable")


# ---------------------------------------------------------------------------
# confidence_level widens CI
# ---------------------------------------------------------------------------
def test_higher_confidence_level_widens_ci():
    model, estimand = _build_reference_model()
    r95 = estimate_effect(model, estimand, "linear_regression",
                          confidence_level=0.95)
    r99 = estimate_effect(model, estimand, "linear_regression",
                          confidence_level=0.99)
    assert r95.ci_low is not None and r95.ci_high is not None
    assert r99.ci_low is not None and r99.ci_high is not None
    width_95 = r95.ci_high - r95.ci_low
    width_99 = r99.ci_high - r99.ci_low
    assert width_99 > width_95, (
        f"expected 99%-CI wider than 95%-CI, got "
        f"width_95={width_95:.6f}, width_99={width_99:.6f}"
    )


# ---------------------------------------------------------------------------
# Method enum validation — unknown method rejected
# ---------------------------------------------------------------------------
def test_unknown_method_raises_estimation_error():
    model, estimand = _build_reference_model()
    with pytest.raises(EstimationError, match="unknown estimator method"):
        # Bypass Literal type-check intentionally
        estimate_effect(model, estimand, "bogus_method")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Pydantic extra=forbid
# ---------------------------------------------------------------------------
def test_estimate_result_rejects_extra_fields():
    with pytest.raises(ValidationError):
        EstimateResult(  # type: ignore[call-arg]
            method="linear_regression",
            effect=-0.5,
            ci_low=-0.7,
            ci_high=-0.3,
            n_samples=300,
            identified_estimand_str="E[Y|do(T)]",
            extra_field="not allowed",
        )


# ---------------------------------------------------------------------------
# Confidence-level out-of-range
# ---------------------------------------------------------------------------
def test_invalid_confidence_level_raises():
    model, estimand = _build_reference_model()
    with pytest.raises(EstimationError, match="confidence_level"):
        estimate_effect(model, estimand, "linear_regression",
                        confidence_level=1.5)


# ---------------------------------------------------------------------------
# Snapshot stability — effect is rounded to 6 decimals
# ---------------------------------------------------------------------------
def test_effect_is_rounded_to_six_decimals():
    model, estimand = _build_reference_model()
    result = estimate_effect(model, estimand, "linear_regression")
    # round(x, 6) means at most 6 decimal places after the dot
    s = f"{result.effect:.10f}".rstrip("0")
    # Allow trailing dot if value is integer-ish
    decimal_part = s.split(".")[1] if "." in s else ""
    assert len(decimal_part) <= 6, f"effect not rounded to 6 decimals: {result.effect}"
