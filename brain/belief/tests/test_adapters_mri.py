"""Phase 7.0 Days 16-17 — MRI adapter unit tests.

All test fixtures are SYNTHETIC. No Aleksandra-specific clinical values
appear here (e.g., this suite uses cyst pcts of 15, 20, 8 — NOT her
actual value). The adapter must work on arbitrary input, not memorize
a single case.

Test coverage:
  1. Explicit cyst-pct extraction
  2. No-pattern -> None
  3. Out-of-range pct -> None
  4. Brainstem keyword classification (intact / partial / severe)
  5. Brainstem no-keyword -> None
  6. CSF panel (all 4 markers, partial panel, absent panel)
  7. Pipeline returns 3 evidences happy-path
  8. Pipeline returns subset when CSF absent
  9. evidence_hash determinism
  10. No PHI leaks in log output
  11. Dimension catalog missing -> skip + warning
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import pytest

from brain.belief.adapters.mri_report import (
    MriReportRow,
    adapt_mri_report,
    extract_brainstem_function,
    extract_csf_biomarkers,
    extract_cyst_volume,
)
from brain.belief.persistence import BeliefDimension


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
SYNTHETIC_DATE = datetime(2026, 5, 1, 9, 30, tzinfo=timezone.utc)


def _stub_dim(name: str, dim_id: int, distribution: str) -> BeliefDimension:
    """Build a BeliefDimension stand-in for adapter tests (no DB)."""
    return BeliefDimension(
        id=dim_id,
        name=name,
        distribution=distribution,
        prior_params={"alpha": 1.0, "beta": 1.0}
        if distribution == "beta"
        else {"x": 0.0},
        citation="https://pubmed.ncbi.nlm.nih.gov/0",
    )


_DIM_TABLE = {
    "cyst_volume_pct": _stub_dim("cyst_volume_pct", 1, "beta"),
    "brainstem_function": _stub_dim("brainstem_function", 2, "categorical"),
    "csf_biomarkers": _stub_dim("csf_biomarkers", 11, "vector"),
}


def _full_loader(name: str) -> Optional[BeliefDimension]:
    return _DIM_TABLE.get(name)


def _missing_loader(name: str) -> Optional[BeliefDimension]:
    return None  # simulate catalog gap


def _mri_row(text: str, ident: str = "mri-001") -> MriReportRow:
    return MriReportRow(
        id=ident,
        mri_date=SYNTHETIC_DATE,
        report_text=text,
    )


# ---------------------------------------------------------------------------
# 1. Cyst-volume extraction
# ---------------------------------------------------------------------------
def test_mri_adapter_extracts_explicit_cyst_pct() -> None:
    report = _mri_row(
        "Brain MRI shows cystic encephalomalacia involving 15% of cerebrum."
    )
    ev = extract_cyst_volume(report, dim_id=1)
    assert ev is not None
    assert ev.value == {"n": 100, "k": 15}
    assert ev.confidence == 0.90
    assert ev.source == "mri_report"
    assert ev.source_ref == "mri-001"
    assert ev.observed_at == SYNTHETIC_DATE


def test_mri_adapter_extracts_cyst_pct_with_word_percent() -> None:
    report = _mri_row("Cystic change in approximately 8 percent of brain.")
    ev = extract_cyst_volume(report, dim_id=1)
    assert ev is not None
    assert ev.value == {"n": 100, "k": 8}


def test_mri_adapter_skips_when_no_cyst_pct_pattern() -> None:
    report = _mri_row("No focal lesions identified. Brain parenchyma unremarkable.")
    ev = extract_cyst_volume(report, dim_id=1)
    assert ev is None


def test_mri_adapter_rejects_implausible_cyst_pct() -> None:
    report = _mri_row(
        "cystic lesion 150% of brain"
    )  # syntactically matches, semantically invalid
    ev = extract_cyst_volume(report, dim_id=1)
    assert ev is None  # out of [0, 100]


# ---------------------------------------------------------------------------
# 2. Brainstem-function extraction
# ---------------------------------------------------------------------------
def test_mri_adapter_extracts_preserved_brainstem() -> None:
    report = _mri_row("Preserved brainstem appearance throughout.")
    ev = extract_brainstem_function(report, dim_id=2)
    assert ev is not None
    assert ev.value == {"observations": [2]}  # intact
    assert ev.confidence == 0.75


def test_mri_adapter_extracts_severe_brainstem_injury() -> None:
    report = _mri_row("Severe brainstem injury with diffuse signal abnormality.")
    ev = extract_brainstem_function(report, dim_id=2)
    assert ev is not None
    assert ev.value == {"observations": [0]}  # impaired


def test_mri_adapter_extracts_partial_brainstem_involvement() -> None:
    report = _mri_row("Mild brainstem injury with focal signal abnormality.")
    ev = extract_brainstem_function(report, dim_id=2)
    assert ev is not None
    assert ev.value == {"observations": [1]}  # partial


def test_mri_adapter_no_brainstem_keyword_returns_none() -> None:
    report = _mri_row("Cerebral white matter changes. Cortical mantle thinning.")
    ev = extract_brainstem_function(report, dim_id=2)
    assert ev is None


def test_mri_adapter_brainstem_priority_severe_beats_intact() -> None:
    # If both severe and "preserved" appear, severe wins (clinical conservative).
    report = _mri_row(
        "Severe brainstem injury. Some previously preserved brainstem regions now affected."
    )
    ev = extract_brainstem_function(report, dim_id=2)
    assert ev is not None
    assert ev.value == {"observations": [0]}


# ---------------------------------------------------------------------------
# 3. CSF biomarker extraction
# ---------------------------------------------------------------------------
def test_mri_adapter_extracts_csf_biomarkers_when_all_four_present() -> None:
    report = _mri_row("CSF panel: NSE: 3.2, S100B = 2.8, GFAP 1.9, Tau: 2.1")
    ev = extract_csf_biomarkers(report, dim_id=11)
    assert ev is not None
    assert ev.value == {"observations": [[3.2, 2.8, 1.9, 2.1]]}
    assert ev.confidence == 0.55


def test_mri_adapter_partial_csf_panel_defaults_missing_to_zero() -> None:
    report = _mri_row("CSF NSE 4.5 elevated. Other markers not assessed.")
    ev = extract_csf_biomarkers(report, dim_id=11)
    assert ev is not None
    # Only NSE present; S100B/GFAP/Tau default to 0.0
    assert ev.value == {"observations": [[4.5, 0.0, 0.0, 0.0]]}


def test_mri_adapter_no_csf_panel_returns_none_for_csf() -> None:
    report = _mri_row("No CSF analysis performed. Imaging only.")
    ev = extract_csf_biomarkers(report, dim_id=11)
    assert ev is None


# ---------------------------------------------------------------------------
# 4. Pipeline integration
# ---------------------------------------------------------------------------
def test_mri_adapter_pipeline_returns_3_evidences_when_all_extract() -> None:
    report = _mri_row(
        "MRI: cystic encephalomalacia involving 20% of cerebrum. "
        "Preserved brainstem. "
        "CSF panel: NSE: 2.5, S100B = 3.0, GFAP 2.0, Tau: 1.8"
    )
    evidences = adapt_mri_report(report, dimension_loader=_full_loader)
    assert len(evidences) == 3
    # Check order: cyst, brainstem, CSF
    assert evidences[0].dimension_id == 1  # cyst
    assert evidences[1].dimension_id == 2  # brainstem
    assert evidences[2].dimension_id == 11  # csf


def test_mri_adapter_pipeline_returns_2_when_csf_absent() -> None:
    report = _mri_row(
        "MRI: cystic encephalomalacia involving 12% of cerebrum. " "Brainstem intact."
    )
    evidences = adapt_mri_report(report, dimension_loader=_full_loader)
    assert len(evidences) == 2
    dims = {ev.dimension_id for ev in evidences}
    assert dims == {1, 2}


def test_mri_adapter_pipeline_returns_empty_on_unparseable_report() -> None:
    report = _mri_row("Unremarkable brain MRI. Patient stable.")
    evidences = adapt_mri_report(report, dimension_loader=_full_loader)
    assert evidences == []


# ---------------------------------------------------------------------------
# 5. Idempotency: evidence_hash determinism
# ---------------------------------------------------------------------------
def test_mri_adapter_evidence_hash_deterministic() -> None:
    report = _mri_row("cystic encephalomalacia involving 18% of cerebrum")
    ev1 = extract_cyst_volume(report, dim_id=1)
    ev2 = extract_cyst_volume(report, dim_id=1)
    assert ev1 is not None and ev2 is not None
    assert ev1.evidence_hash == ev2.evidence_hash


def test_mri_adapter_evidence_hash_differs_by_report_id() -> None:
    report_a = _mri_row(
        "cystic encephalomalacia involving 10% of cerebrum", ident="mri-a"
    )
    report_b = _mri_row(
        "cystic encephalomalacia involving 10% of cerebrum", ident="mri-b"
    )
    ev_a = extract_cyst_volume(report_a, dim_id=1)
    ev_b = extract_cyst_volume(report_b, dim_id=1)
    assert ev_a is not None and ev_b is not None
    assert ev_a.evidence_hash != ev_b.evidence_hash


# ---------------------------------------------------------------------------
# 6. PHI safety
# ---------------------------------------------------------------------------
def test_mri_adapter_does_not_log_phi(caplog: pytest.LogCaptureFixture) -> None:
    """Logger must NEVER include the raw report_text body."""
    sensitive_text = "Patient unique-marker-XYZ-12345 with cystic encephalomalacia involving 22% of cerebrum"
    report = _mri_row(sensitive_text)
    with caplog.at_level(logging.WARNING, logger="brain.belief.adapters.mri_report"):
        # Even on happy path, run extractors that might warn (CSF will be silent here)
        extract_cyst_volume(report, dim_id=1)
        extract_brainstem_function(report, dim_id=2)  # will warn (no keyword)
    combined = "\n".join(rec.message for rec in caplog.records)
    assert "unique-marker-XYZ-12345" not in combined
    assert "cystic encephalomalacia" not in combined
    # Field name + ID are allowed (and are useful for debugging)
    assert "brainstem_function" in combined or "no keyword" in combined


def test_mri_adapter_log_warnings_only_carry_field_name_and_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    report = _mri_row("Plain text without any patterns.", ident="mri-test-99")
    with caplog.at_level(logging.WARNING, logger="brain.belief.adapters.mri_report"):
        adapt_mri_report(report, dimension_loader=_full_loader)
    for rec in caplog.records:
        # Allow the field name + id; forbid the report body fragments
        assert "Plain text" not in rec.message


# ---------------------------------------------------------------------------
# 7. Catalog-gap handling
# ---------------------------------------------------------------------------
def test_mri_adapter_skips_when_dimension_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    report = _mri_row(
        "cystic encephalomalacia involving 15% of cerebrum. Preserved brainstem."
    )
    with caplog.at_level(logging.WARNING, logger="brain.belief.adapters.mri_report"):
        evidences = adapt_mri_report(report, dimension_loader=_missing_loader)
    assert evidences == []
    # 3 dimensions × 1 warning each = 3 "not in catalog" warnings
    catalog_warnings = [r for r in caplog.records if "not in catalog" in r.message]
    assert len(catalog_warnings) == 3
