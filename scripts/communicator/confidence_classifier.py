"""
confidence_classifier.py — Phase 3 CGM-06 confidence scoring.

Pure function. No LLM call. Returns a float in [0.0, 1.0] for every input.

The score answers: "How much should the family trust this claim to be
reliable enough to act as a discussion point with a clinician?" It does NOT
answer "is this medically correct" — that judgement stays with the clinician.

Inputs
------
- evidence_grade: integer 1..6 from the project's six-tier evidence ranking.
  1 = systematic review/meta-analysis, 2 = RCT, 3 = cohort/case-control,
  4 = case series/uncontrolled, 5 = expert opinion/mechanism, 6 = unverified.
- source_count: how many independent sources cite the claim.
- source_recency_years: age of the newest source in years (e.g. 0.5 = 6 months).
  Negative or NaN treated as 0.
- direct_relevance: True if the source studies HIE / cystic encephalomalacia
  / neonatal hypoxia directly; False if it's cross-disease analogy.
- citation_round_trip_passed: True if PMID/DOI/NCT/URL resolves end-to-end.

Output
------
score ∈ [0.0, 1.0] rounded to 4 decimal places.

Threshold guide (consumed by tier_router on Day 4):
    score >= 0.85 → may route to T1 (urgent)
    score >= 0.70 → may route to T2 (action needed)
    score >= 0.50 → may route to T3 (important)
    score <  0.50 → T4 (weekly appendix only)

Formula
-------
    grade_weight    = (7 - clamp(grade, 1, 6)) / 6.0      # ∈ [1/6, 1.0]
    source_weight   = min(source_count / 3.0, 1.0)         # cap at 3 sources
    recency_weight  = clamp(1.0 - recency_years / 5.0, 0.2, 1.0)
    relevance_bonus = 1.0 if direct else 0.7
    roundtrip_gate  = 1.0 if citation_round_trip_passed else 0.5

    raw = grade_weight * source_weight * recency_weight * relevance_bonus
    score = round(raw * roundtrip_gate, 4)

The roundtrip_gate halves the score when the citation does not round-trip,
guaranteeing that an unverifiable claim cannot cross the T1 threshold even
if every other signal is perfect.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfidenceInput:
    evidence_grade: int
    source_count: int
    source_recency_years: float
    direct_relevance: bool
    citation_round_trip_passed: bool


def _clamp(v: float, lo: float, hi: float) -> float:
    if math.isnan(v):
        v = lo
    return max(lo, min(hi, v))


def score(inp: ConfidenceInput) -> float:
    """Deterministic confidence score for a single claim."""
    grade = _clamp(float(inp.evidence_grade), 1.0, 6.0)
    grade_weight = (7.0 - grade) / 6.0  # grade 1 → 1.0, grade 6 → 1/6

    source_count = max(0, int(inp.source_count))
    source_weight = min(source_count / 3.0, 1.0)

    recency = float(inp.source_recency_years)
    if math.isnan(recency) or recency < 0:
        recency = 0.0
    recency_weight = _clamp(1.0 - recency / 5.0, 0.2, 1.0)

    relevance_bonus = 1.0 if inp.direct_relevance else 0.7
    roundtrip_gate = 1.0 if inp.citation_round_trip_passed else 0.5

    raw = grade_weight * source_weight * recency_weight * relevance_bonus
    return round(raw * roundtrip_gate, 4)


__all__ = ["ConfidenceInput", "score"]
