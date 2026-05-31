"""MRI report -> BeliefEvidence adapter (Phase 7.0 Days 16-17).

Reads MRI report rows (caller-fetched) and emits BeliefEvidence for:

  - cyst_volume_pct        (Beta)        -> {"n": 100, "k": pct}
  - brainstem_function     (Categorical) -> {"observations": [class_index]}
  - csf_biomarkers         (Vector)      -> {"observations": [[nse, s100b, gfap, tau]]}

Parsing pipeline (CHEAP-first; no LLM):

  1. Deterministic regex against report text
  2. Keyword pattern match for staging-type fields (brainstem)
  3. Confidence reflects extraction method (see module docstring)
  4. Failed extraction -> return None + logger.warning(dim + status); never
     raise. The pipeline philosophy is partial success: a report that yields
     only cyst_volume_pct still moves the belief state.

Schema note (Phase 7.0 Day 16-17 discovery): there is no `mri_reports`
table in Phase 0-6 — the closest analogue is `aleksandra_timeline` rows
where `event_type='mri_scan'` (with the narrative in `description`).
Callers map timeline rows -> MriReportRow before invoking the adapter.
A dedicated `mri_reports` table can land in a future Phase 1 enhancement
without changing this adapter — only the caller's fetch query changes.

Hard rules from `.claude/agents/v7-bayes.md`:
  - NO PHI in logs (only field names + extraction status)
  - Idempotency via BeliefEvidence.evidence_hash
  - source = "mri_report" (matches persistence.ALLOWED_EVIDENCE_SOURCES)
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Callable, Optional

from pydantic import BaseModel, ConfigDict, Field

from brain.belief.persistence import (
    BeliefEvidence,
    compute_evidence_hash,
    get_dimension_by_name,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Row shape callers must hand in
# ---------------------------------------------------------------------------
class MriReportRow(BaseModel):
    """Caller-supplied MRI-report shape. Mirrors the columns an adapter
    needs from either a future `mri_reports` table or an
    `aleksandra_timeline` row with `event_type='mri_scan'`.

    Fields:
      id          : stable identifier (UUID string or numeric id).
                    Used as `source_ref` for evidence_hash idempotency.
      mri_date    : datetime — drives `BeliefEvidence.observed_at`.
      report_text : free-text narrative (radiology read / radiologist
                    impression). Regex + keyword extraction happens here.
      structured_findings : optional pre-parsed fields. Not consumed in
                    the MVP adapter (regex-only), but reserved for v7.1
                    when a Phase 1 enhancement pre-populates structured
                    numeric fields from RAGFlow.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    mri_date: datetime
    report_text: str
    structured_findings: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Cyst-volume regex
# ---------------------------------------------------------------------------
# Matches phrases like:
#   "cystic encephalomalacia involving 12% of cerebrum"
#   "cystic change in approximately 8 percent of brain"
#   "cystic lesion, 15%"
# Capture group 1 is the integer percentage.
_CYST_PCT_REGEX = re.compile(
    r"(?:cyst(?:ic)?\s+(?:encephalomalacia|change|lesion|area)|"
    r"cystic\s+(?:area|lesion|encephalomalacia))"
    r"[^.0-9]*?(\d{1,3})\s*(?:%|percent|of\s+(?:cerebrum|brain))",
    re.IGNORECASE,
)


def extract_cyst_volume(report: MriReportRow, dim_id: int) -> Optional[BeliefEvidence]:
    """Parse a cyst percentage from `report.report_text`.

    Returns None if the regex finds no match or the captured value is
    outside [0, 100].

    Output value shape: `{"n": 100, "k": int(pct)}` — Beta likelihood
    interprets this as a Binomial observation (k successes out of 100
    cyst-tissue trials), which matches `LIKELIHOOD_VALUE_SCHEMA["beta"]`.
    """
    match = _CYST_PCT_REGEX.search(report.report_text)
    if not match:
        logger.warning(
            "cyst_volume_pct extraction: no pattern match (mri_report id=%s)",
            report.id,
        )
        return None
    pct = int(match.group(1))
    if not (0 <= pct <= 100):
        logger.warning(
            "cyst_volume_pct extraction: out-of-range pct=%d (mri_report id=%s)",
            pct,
            report.id,
        )
        return None
    value: dict[str, Any] = {"n": 100, "k": pct}
    evidence_hash = compute_evidence_hash(
        dimension_id=dim_id,
        source="mri_report",
        source_ref=str(report.id),
        value=value,
    )
    return BeliefEvidence(
        dimension_id=dim_id,
        source="mri_report",
        source_ref=str(report.id),
        value=value,
        evidence_hash=evidence_hash,
        confidence=0.90,  # explicit numeric in text
        observed_at=report.mri_date,
    )


# ---------------------------------------------------------------------------
# Brainstem-function keyword classifier (3 states)
# ---------------------------------------------------------------------------
# State indices match dimensions.toml: 0=impaired, 1=partial, 2=intact.
# Keywords are checked in priority order (severe before partial before
# preserved) — first match wins.
_BRAINSTEM_KEYWORDS: dict[int, list[str]] = {
    0: [
        "severe brainstem injury",
        "diffuse brainstem damage",
        "complete brainstem involvement",
        "extensive brainstem injury",
        "brainstem necrosis",
    ],
    1: [
        "partial brainstem involvement",
        "mild brainstem injury",
        "some brainstem changes",
        "focal brainstem signal abnormality",
        "minimal brainstem involvement",
    ],
    2: [
        "preserved brainstem",
        "brainstem intact",
        "brainstem appears normal",
        "intact brainstem",
        "brainstem unremarkable",
    ],
}


def extract_brainstem_function(
    report: MriReportRow, dim_id: int
) -> Optional[BeliefEvidence]:
    """Classify brainstem state from staging keywords -> {0,1,2}.

    Returns None if no keyword matches. Confidence=0.75 (keyword-based).
    """
    text = report.report_text.lower()
    matched_state: Optional[int] = None
    # Priority order: impaired (0) -> partial (1) -> intact (2)
    for state in (0, 1, 2):
        for kw in _BRAINSTEM_KEYWORDS[state]:
            if kw in text:
                matched_state = state
                break
        if matched_state is not None:
            break
    if matched_state is None:
        logger.warning(
            "brainstem_function extraction: no keyword match (mri_report id=%s)",
            report.id,
        )
        return None
    value: dict[str, Any] = {"observations": [matched_state]}
    evidence_hash = compute_evidence_hash(
        dimension_id=dim_id,
        source="mri_report",
        source_ref=str(report.id),
        value=value,
    )
    return BeliefEvidence(
        dimension_id=dim_id,
        source="mri_report",
        source_ref=str(report.id),
        value=value,
        evidence_hash=evidence_hash,
        confidence=0.75,
        observed_at=report.mri_date,
    )


# ---------------------------------------------------------------------------
# CSF biomarker panel (vector likelihood)
# ---------------------------------------------------------------------------
# Matches "NSE: 4.2", "S100B = 3.0", "GFAP 2.5", "Tau: 1.8" etc.
_CSF_MARKER_REGEX = re.compile(
    r"\b(NSE|S100B|GFAP|Tau)\b\s*[:=]?\s*(-?\d+\.?\d*)",
    re.IGNORECASE,
)

_CSF_ORDER = ("NSE", "S100B", "GFAP", "Tau")  # mirrors dimensions.toml mu_vec order


def extract_csf_biomarkers(
    report: MriReportRow, dim_id: int
) -> Optional[BeliefEvidence]:
    """Extract a 4-dim CSF biomarker vector (NSE, S100B, GFAP, Tau).

    Returns None if NO marker is mentioned. If a partial panel is found,
    missing markers default to 0.0 (z-score = control mean) and confidence
    drops to 0.55 (raw-value-without-z-conversion penalty).

    Output value shape: `{"observations": [[nse, s100b, gfap, tau]]}` —
    matches `LIKELIHOOD_VALUE_SCHEMA["vector"]` (2D: N=1 sample x D=4 dims).
    """
    matches = _CSF_MARKER_REGEX.findall(report.report_text)
    if not matches:
        return None  # CSF panel absent — silent (most reports won't have it)
    # Case-insensitive marker lookup: normalize captured marker to canonical
    # casing in `_CSF_ORDER` ("NSE", "S100B", "GFAP", "Tau").
    canonical_by_lower = {k.lower(): k for k in _CSF_ORDER}
    marker_map: dict[str, float] = {k: 0.0 for k in _CSF_ORDER}
    for marker, raw_val in matches:
        canonical = canonical_by_lower.get(marker.lower())
        if canonical is None:
            continue
        try:
            marker_map[canonical] = float(raw_val)
        except ValueError:
            continue
    value: dict[str, Any] = {"observations": [[marker_map[k] for k in _CSF_ORDER]]}
    evidence_hash = compute_evidence_hash(
        dimension_id=dim_id,
        source="mri_report",
        source_ref=str(report.id),
        value=value,
    )
    return BeliefEvidence(
        dimension_id=dim_id,
        source="mri_report",
        source_ref=str(report.id),
        value=value,
        evidence_hash=evidence_hash,
        confidence=0.55,  # raw-value, age-matched normative ranges not applied
        observed_at=report.mri_date,
    )


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------
def adapt_mri_report(
    report: MriReportRow,
    *,
    dimension_loader: Optional[Callable[[str], Any]] = None,
) -> list[BeliefEvidence]:
    """Run all 3 MRI extractors over `report` and return successful evidence.

    Parameters
    ----------
    report : MriReportRow
        Caller-supplied report shape.
    dimension_loader : optional callable name -> BeliefDimension|None
        Injectable for tests so they don't hit the live DB. Defaults to
        `persistence.get_dimension_by_name` (which DOES hit the DB).

    Returns
    -------
    list[BeliefEvidence]
        Zero, one, two, or three evidence rows depending on which
        extractors succeeded. Order: cyst, brainstem, CSF.
    """
    loader = dimension_loader or get_dimension_by_name
    evidences: list[BeliefEvidence] = []

    extractors: list[
        tuple[str, Callable[[MriReportRow, int], Optional[BeliefEvidence]]]
    ] = [
        ("cyst_volume_pct", extract_cyst_volume),
        ("brainstem_function", extract_brainstem_function),
        ("csf_biomarkers", extract_csf_biomarkers),
    ]

    for dim_name, extractor in extractors:
        dim = loader(dim_name)
        if dim is None or getattr(dim, "id", None) is None:
            logger.warning(
                "dimension %s not in catalog; skipping (mri_report id=%s)",
                dim_name,
                report.id,
            )
            continue
        ev = extractor(report, dim.id)
        if ev is not None:
            evidences.append(ev)

    return evidences


__all__ = [
    "MriReportRow",
    "extract_cyst_volume",
    "extract_brainstem_function",
    "extract_csf_biomarkers",
    "adapt_mri_report",
]
