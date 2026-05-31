"""Tests for brain.causal.cross_link — causal estimate -> belief evidence.

All tests run in DRY_RUN mode (SUPABASE_DB_URL unset), proving the
code-complete-without-infra contract: the cross-link computes the
deterministic ``evidence_hash`` and returns
``"DRY_RUN:<evidence_hash>"`` without ever touching Postgres.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pytest

from brain.belief.persistence import compute_evidence_hash
from brain.causal.cross_link import (
    _build_value_payload,
    _confidence_from_estimate,
    record_causal_estimate_as_evidence,
)
from brain.causal.estimators import EstimateResult


# ---------------------------------------------------------------------------
# Fixture — a tight + a loose EstimateResult
# ---------------------------------------------------------------------------
def _tight_estimate() -> EstimateResult:
    return EstimateResult(
        method="linear_regression",
        effect=-0.85,
        ci_low=-0.92,
        ci_high=-0.76,
        n_samples=300,
        identified_estimand_str="E[Y|do(T=1)]",
        units="seizures/day",
    )


def _loose_estimate() -> EstimateResult:
    return EstimateResult(
        method="linear_regression",
        effect=-0.85,
        ci_low=-3.0,
        ci_high=2.5,
        n_samples=300,
        identified_estimand_str="E[Y|do(T=1)]",
        units="seizures/day",
    )


def _no_ci_estimate() -> EstimateResult:
    return EstimateResult(
        method="propensity_score_matching",
        effect=-0.5,
        ci_low=None,
        ci_high=None,
        n_samples=100,
        identified_estimand_str="E[Y|do(T=1)]",
        units=None,
    )


# ---------------------------------------------------------------------------
# DRY_RUN sentinel — no SUPABASE_DB_URL
# ---------------------------------------------------------------------------
def test_dry_run_returns_sentinel_without_supabase_url(monkeypatch):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    out = record_causal_estimate_as_evidence(
        estimate=_tight_estimate(),
        target_dimension_id=42,
        source_ref="scm:reference/linear_regression",
        observed_at=datetime(2026, 5, 25, 12, 0, tzinfo=timezone.utc),
    )
    assert out.startswith("DRY_RUN:")
    # 64-hex SHA-256
    assert len(out) == len("DRY_RUN:") + 64


# ---------------------------------------------------------------------------
# Evidence hash matches direct compute_evidence_hash call
# ---------------------------------------------------------------------------
def test_evidence_hash_matches_direct_compute(monkeypatch):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    est = _tight_estimate()
    expected_value = _build_value_payload(est)
    expected_hash = compute_evidence_hash(
        7, "causal_estimate", "scm:ref/X", expected_value
    )
    out = record_causal_estimate_as_evidence(
        estimate=est,
        target_dimension_id=7,
        source_ref="scm:ref/X",
        observed_at=datetime(2026, 5, 25, tzinfo=timezone.utc),
    )
    assert out == f"DRY_RUN:{expected_hash}"


# ---------------------------------------------------------------------------
# Confidence inversely related to CI width
# ---------------------------------------------------------------------------
def test_confidence_inversely_related_to_ci_width():
    tight = _tight_estimate()
    loose = _loose_estimate()
    c_tight = _confidence_from_estimate(tight, confidence_floor=0.4)
    c_loose = _confidence_from_estimate(loose, confidence_floor=0.4)
    assert c_tight > c_loose, (
        f"expected tighter CI -> higher confidence; "
        f"got tight={c_tight}, loose={c_loose}"
    )


# ---------------------------------------------------------------------------
# None CI clamps to confidence_floor
# ---------------------------------------------------------------------------
def test_none_ci_clamps_to_confidence_floor():
    est = _no_ci_estimate()
    c = _confidence_from_estimate(est, confidence_floor=0.4)
    assert c == 0.4
    c_high_floor = _confidence_from_estimate(est, confidence_floor=0.7)
    assert c_high_floor == 0.7


# ---------------------------------------------------------------------------
# Value dict is JSON-serializable (no numpy scalars)
# ---------------------------------------------------------------------------
def test_value_payload_is_pure_json_serializable():
    est = _tight_estimate()
    value = _build_value_payload(est)
    # Must round-trip through json.dumps without `default=` fallback
    s = json.dumps(value)
    rebuilt = json.loads(s)
    assert rebuilt["effect"] == -0.85
    assert rebuilt["ci_low"] == -0.92
    assert rebuilt["ci_high"] == -0.76
    assert rebuilt["method"] == "linear_regression"
    assert rebuilt["n_samples"] == 300
    assert rebuilt["units"] == "seizures/day"
    # Types: every numeric must be a plain Python float / int
    assert isinstance(value["effect"], float)
    assert isinstance(value["ci_low"], float)
    assert isinstance(value["ci_high"], float)
    assert isinstance(value["n_samples"], int)


# ---------------------------------------------------------------------------
# Out-of-range confidence_floor rejected
# ---------------------------------------------------------------------------
def test_invalid_confidence_floor_raises(monkeypatch):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    with pytest.raises(ValueError, match="confidence_floor"):
        record_causal_estimate_as_evidence(
            estimate=_tight_estimate(),
            target_dimension_id=1,
            source_ref="x",
            observed_at=datetime(2026, 5, 25, tzinfo=timezone.utc),
            confidence_floor=1.5,
        )
