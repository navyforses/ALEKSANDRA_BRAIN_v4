"""Tests for brain.common.schemas (Phase 7.5 Rule #3 + #5)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from brain.common.schemas import (
    ALLOWED_CITATION_MARKERS,
    BilingualRecommendation,
    Recommendation,
)


# ---------------------------------------------------------------------------
# Recommendation - citation marker (Rule #3)
# ---------------------------------------------------------------------------
def test_recommendation_with_pubmed_url_passes():
    rec = Recommendation(
        subject="vigabatrin therapy",
        expected_value=0.7,
        ci_low=0.55,
        ci_high=0.82,
        citation="https://pubmed.ncbi.nlm.nih.gov/7686614/",
        language="en",
    )
    assert rec.subject == "vigabatrin therapy"
    assert rec.ci_low <= rec.ci_high


def test_recommendation_with_pmid_prefix_passes():
    rec = Recommendation(
        subject="cord blood infusion",
        expected_value=0.4,
        ci_low=0.2,
        ci_high=0.6,
        citation="PMID:32713850 - cord blood eligibility window",
        language="en",
    )
    assert "PMID:" in rec.citation


def test_recommendation_without_citation_marker_fails():
    with pytest.raises(ValidationError) as exc_info:
        Recommendation(
            subject="bogus claim",
            expected_value=0.5,
            ci_low=0.4,
            ci_high=0.6,
            citation="see notes from chat",  # no allowed marker
            language="en",
        )
    assert "Rule #3" in str(exc_info.value)


def test_recommendation_missing_citation_field_fails():
    with pytest.raises(ValidationError):
        Recommendation(
            subject="bogus claim",
            expected_value=0.5,
            ci_low=0.4,
            ci_high=0.6,
            language="en",
        )  # type: ignore[call-arg]


def test_recommendation_extra_field_forbidden():
    with pytest.raises(ValidationError):
        Recommendation(
            subject="ok",
            expected_value=0.5,
            ci_low=0.4,
            ci_high=0.6,
            citation="PMID:19489084 valid",
            language="en",
            backdoor_field="x",  # extra='forbid' should reject
        )  # type: ignore[call-arg]


def test_recommendation_ci_inversion_fails():
    with pytest.raises(ValidationError) as exc_info:
        Recommendation(
            subject="reversed CI",
            expected_value=0.5,
            ci_low=0.9,
            ci_high=0.1,
            citation="PMID:7686614 reversed CI test",
            language="en",
        )
    assert "Rule #4" in str(exc_info.value)


# ---------------------------------------------------------------------------
# BilingualRecommendation (Rule #5)
# ---------------------------------------------------------------------------
def _en_rec() -> Recommendation:
    return Recommendation(
        subject="vigabatrin",
        expected_value=0.7,
        ci_low=0.55,
        ci_high=0.82,
        citation="PMID:7686614 vigabatrin GABA-T inhibition",
        language="en",
    )


def _ka_rec() -> Recommendation:
    return Recommendation(
        subject="ვიგაბატრინი",
        expected_value=0.7,
        ci_low=0.55,
        ci_high=0.82,
        citation="PMID:7686614 ვიგაბატრინი",
        language="ka",
    )


def test_bilingual_with_both_languages_passes():
    rec = BilingualRecommendation(en=_en_rec(), ka=_ka_rec())
    assert rec.en.language == "en"
    assert rec.ka.language == "ka"


def test_bilingual_missing_ka_fails():
    with pytest.raises(ValidationError):
        BilingualRecommendation(en=_en_rec())  # type: ignore[call-arg]


def test_bilingual_swapped_languages_fails():
    bad_en = _en_rec().model_copy(update={"language": "ka"})
    with pytest.raises(ValidationError) as exc_info:
        BilingualRecommendation(en=bad_en, ka=_ka_rec())
    assert "Rule #5" in str(exc_info.value)


def test_allowed_markers_constant_nonempty():
    assert isinstance(ALLOWED_CITATION_MARKERS, tuple)
    assert len(ALLOWED_CITATION_MARKERS) >= 4
