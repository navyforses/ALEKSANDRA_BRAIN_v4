"""Tests for brain.common.formatter (Phase 7.5 Rule #4)."""

from __future__ import annotations

import pytest

from brain.common.formatter import (
    MissingCIError,
    format_recommendation_text,
    reject_output_without_ci,
)
from brain.common.schemas import Recommendation


def _rec(lang: str = "en") -> Recommendation:
    return Recommendation(
        subject="vigabatrin",
        expected_value=0.7,
        ci_low=0.55,
        ci_high=0.82,
        citation="PMID:7686614 vigabatrin",
        language=lang,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# format_recommendation_text
# ---------------------------------------------------------------------------
def test_format_renders_subject_value_and_ci():
    out = format_recommendation_text(_rec("en"), lang="en")
    assert out == "vigabatrin: 0.700 [0.550, 0.820]"


def test_format_ka_renders_mkhedruli_subject():
    rec = Recommendation(
        subject="ვიგაბატრინი",
        expected_value=0.7,
        ci_low=0.55,
        ci_high=0.82,
        citation="PMID:7686614 ვიგაბატრინი",
        language="ka",
    )
    out = format_recommendation_text(rec, lang="ka")
    assert out.startswith("ვიგაბატრინი:")
    assert "[0.550, 0.820]" in out


def test_format_rejects_unknown_lang():
    with pytest.raises(ValueError):
        format_recommendation_text(_rec("en"), lang="fr")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# reject_output_without_ci
# ---------------------------------------------------------------------------
def test_reject_passes_full_payload():
    payload = {
        "subject": "ok",
        "expected_value": 0.7,
        "ci_low": 0.55,
        "ci_high": 0.82,
    }
    # Must NOT raise.
    reject_output_without_ci(payload)


def test_reject_raises_on_expected_only():
    payload = {
        "subject": "naked",
        "expected_value": 0.7,
    }
    with pytest.raises(MissingCIError) as exc_info:
        reject_output_without_ci(payload)
    assert "Rule #4" in str(exc_info.value)
    assert "expected_value" in str(exc_info.value)


def test_reject_raises_on_predicted_only():
    payload = {
        "section": {
            "predicted_outcome": 0.42,
        },
    }
    with pytest.raises(MissingCIError):
        reject_output_without_ci(payload)


def test_reject_passes_with_alternative_ci_key_names():
    payload = {
        "expected_value": 0.7,
        "lower": 0.55,
        "upper": 0.82,
    }
    # `lower` + `upper` count as CI companions.
    reject_output_without_ci(payload)


def test_reject_walks_nested_lists():
    payload = {
        "rows": [
            {"expected_value": 0.7, "ci_low": 0.5, "ci_high": 0.9},
            {"expected_value": 0.4},  # naked
        ],
    }
    with pytest.raises(MissingCIError):
        reject_output_without_ci(payload)


def test_reject_rejects_non_dict():
    with pytest.raises(TypeError):
        reject_output_without_ci(["not", "a", "dict"])  # type: ignore[arg-type]
