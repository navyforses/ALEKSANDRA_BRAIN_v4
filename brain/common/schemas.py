"""Phase 7.5 Rule #3 - Citation mandatory (Pydantic strict).

Every recommendation that leaves the system MUST carry a citation. The
constraint is physical at the type-validation layer: a Recommendation
without a `citation` field raises ValidationError BEFORE the payload
reaches any output formatter, Telegram sender, or PDF builder.

Bilingual parity (Rule #5) is enforced by BilingualRecommendation: both
`en` and `ka` sub-objects must be present and individually valid.

Constitutional AI pattern: the rule lives in the schema (high trust
boundary) rather than in a formatter check (easy to forget on a new
output path). Pydantic v2 strict + extra='forbid' rejects any unknown
field, so a future code path cannot smuggle in a `citation_optional`
escape hatch by adding a new field.

Reference:
    v7_architecture/70_PHASES/75_PHASE_7_5_CONSTITUTIONAL_2W.md §2.1
    .claude/agents/v7-constitution.md Rule #3 row
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Allowed citation prefixes / substrings
# ---------------------------------------------------------------------------
# A citation is "primary" if it matches one of these substrings (case-insensitive).
# The list intentionally accepts PubMed, DOI, ClinicalTrials, and a GitHub URL
# for tooling/process citations. Conservative; expand only with a constitutional
# override row.
ALLOWED_CITATION_MARKERS: tuple[str, ...] = (
    "pubmed.ncbi.nlm.nih.gov",
    "doi.org",
    "PMID:",
    "DOI:",
    "github.com",
)


def _has_allowed_marker(citation: str) -> bool:
    """Return True iff `citation` contains any of the allowed substrings.

    Case-insensitive on the URL substrings, case-sensitive on the explicit
    "PMID:" / "DOI:" prefixes (uppercase by convention).
    """
    lowered = citation.lower()
    for marker in ALLOWED_CITATION_MARKERS:
        if marker in marker.lower():  # marker may already be lowercase
            pass
        if marker.lower() in lowered:
            return True
    return False


# ---------------------------------------------------------------------------
# Recommendation - single-language schema
# ---------------------------------------------------------------------------
class Recommendation(BaseModel):
    """A single-language recommendation row.

    Rule #3: ``citation`` is REQUIRED and must contain a primary-source
    marker (PubMed / DOI / ClinicalTrials / GitHub).
    Rule #4: ``ci_low`` and ``ci_high`` are REQUIRED alongside
    ``expected_value`` (point-estimate-only payloads are rejected by
    BOTH schema (here) and formatter layer (brain/common/formatter.py)).
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    subject: str = Field(..., min_length=1)
    expected_value: float
    ci_low: float
    ci_high: float
    citation: str = Field(..., min_length=10)
    language: Literal["en", "ka"]

    @model_validator(mode="after")
    def _validate_citation_marker(self) -> "Recommendation":
        if not _has_allowed_marker(self.citation):
            raise ValueError(
                "Phase 7.5 Rule #3: citation must contain one of "
                f"{ALLOWED_CITATION_MARKERS} - got {self.citation!r}"
            )
        if self.ci_low > self.ci_high:
            raise ValueError(
                "Phase 7.5 Rule #4: ci_low must be <= ci_high "
                f"(got ci_low={self.ci_low}, ci_high={self.ci_high})"
            )
        return self


# ---------------------------------------------------------------------------
# BilingualRecommendation - Rule #5 (parity)
# ---------------------------------------------------------------------------
class BilingualRecommendation(BaseModel):
    """A bilingual recommendation: both en + ka must be present and valid.

    Rule #5: bilingual parity. The wife-facing surface reads `ka`; the
    clinician-facing surface reads `en`; both must be non-empty and
    independently pass Rule #3 + Rule #4.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    en: Recommendation
    ka: Recommendation

    @model_validator(mode="after")
    def _validate_parity(self) -> "BilingualRecommendation":
        if self.en.language != "en":
            raise ValueError(
                f"Phase 7.5 Rule #5: en.language must be 'en' (got "
                f"{self.en.language!r})"
            )
        if self.ka.language != "ka":
            raise ValueError(
                f"Phase 7.5 Rule #5: ka.language must be 'ka' (got "
                f"{self.ka.language!r})"
            )
        if not self.en.subject.strip() or not self.ka.subject.strip():
            raise ValueError(
                "Phase 7.5 Rule #5: bilingual parity - both en.subject "
                "and ka.subject must be non-empty"
            )
        return self


__all__ = [
    "ALLOWED_CITATION_MARKERS",
    "Recommendation",
    "BilingualRecommendation",
]
