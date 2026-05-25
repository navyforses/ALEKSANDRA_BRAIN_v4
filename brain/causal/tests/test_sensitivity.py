"""Tests for brain.causal.sensitivity — refutation wrapper.

Uses the reference SCM + 300-row synthetic data; runs DoWhy's
random_common_cause and placebo_treatment_refuter on a linear estimate
and asserts the typed report shape + sensible PASS verdicts.
"""

from __future__ import annotations

import warnings

import pytest
from pydantic import ValidationError

warnings.filterwarnings("ignore", category=DeprecationWarning)

from brain.causal.dowhy_bootstrap import (
    build_causal_model,
    synthetic_data_for_reference_scm,
)
from brain.causal.scm import build_reference_scm
from brain.causal.sensitivity import (
    RefutationError,
    RefutationReport,
    refute_estimate,
    refute_estimate_all,
)


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------
def _model_and_estimate(n: int = 300, seed: int = 7):
    scm = build_reference_scm()
    df = synthetic_data_for_reference_scm(n=n, random_seed=seed)
    model = build_causal_model(scm, df)
    raw_estimand = model.identify_effect(proceed_when_unidentifiable=True)
    estimate = model.estimate_effect(
        raw_estimand,
        method_name="backdoor.linear_regression",
        confidence_intervals=True,
        test_significance=False,
    )
    return model, raw_estimand, estimate


# ---------------------------------------------------------------------------
# random_common_cause
# ---------------------------------------------------------------------------
def test_random_common_cause_returns_refutation_report():
    model, estimand, estimate = _model_and_estimate()
    report = refute_estimate(model, estimand, estimate, "random_common_cause")
    assert isinstance(report, RefutationReport)
    assert report.refuter == "random_common_cause"
    # On the reference SCM a well-identified linear estimate should be
    # robust to adding one random common cause -> passed=True
    assert report.passed is True, (
        f"expected random_common_cause to PASS on reference SCM, "
        f"got interpretation={report.interpretation!r}"
    )


# ---------------------------------------------------------------------------
# placebo_treatment_refuter
# ---------------------------------------------------------------------------
def test_placebo_returns_refutation_report():
    model, estimand, estimate = _model_and_estimate()
    report = refute_estimate(
        model, estimand, estimate, "placebo_treatment_refuter"
    )
    assert isinstance(report, RefutationReport)
    assert report.refuter == "placebo_treatment_refuter"
    # DoWhy returns new_effect ~ 0.0 for placebo on a real treatment ->
    # |new| < 0.2 * |orig| should hold
    assert report.passed is True, (
        f"expected placebo refuter to PASS on reference SCM, "
        f"got interpretation={report.interpretation!r}"
    )


# ---------------------------------------------------------------------------
# Unknown refuter rejected
# ---------------------------------------------------------------------------
def test_unknown_refuter_raises_refutation_error():
    model, estimand, estimate = _model_and_estimate()
    with pytest.raises(RefutationError, match="unknown refuter"):
        refute_estimate(
            model, estimand, estimate, "made_up_refuter"  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# refute_estimate_all
# ---------------------------------------------------------------------------
def test_refute_estimate_all_returns_two_reports():
    model, estimand, estimate = _model_and_estimate()
    reports = refute_estimate_all(model, estimand, estimate)
    assert isinstance(reports, list)
    assert len(reports) == 2
    refuters_seen = {r.refuter for r in reports}
    assert refuters_seen == {"random_common_cause", "placebo_treatment_refuter"}


# ---------------------------------------------------------------------------
# Pydantic extra=forbid
# ---------------------------------------------------------------------------
def test_refutation_report_rejects_extra_fields():
    with pytest.raises(ValidationError):
        RefutationReport(  # type: ignore[call-arg]
            refuter="random_common_cause",
            original_effect=-0.5,
            new_effect=-0.51,
            p_value=1.0,
            passed=True,
            interpretation="ok",
            unexpected="nope",
        )


# ---------------------------------------------------------------------------
# Refutation report carries interpretation string
# ---------------------------------------------------------------------------
def test_refutation_report_interpretation_non_empty():
    model, estimand, estimate = _model_and_estimate()
    report = refute_estimate(model, estimand, estimate, "random_common_cause")
    assert len(report.interpretation) > 0
    assert "random_common_cause" in report.interpretation
