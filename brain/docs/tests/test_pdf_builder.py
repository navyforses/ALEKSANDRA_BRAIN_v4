# -*- coding: utf-8 -*-
"""Phase 7.7 PDF builder tests.

Coverage:
  1. PdfSection rejects level=4.
  2. PdfDocument with 4 citations raises InsufficientSourcesError
     (Phase 7.5 Rule #12) via build_pdf gate.
  3. PdfDocument with 5 PubMed citations passes validation.
  4. PdfDocument rejects citation strings that do NOT match a
     primary-source pattern (PDFCitationError).
  5. build_pdf dry_run=True returns path WITHOUT writing.
  6. When reportlab is missing, build_pdf with dry_run=False raises
     PDFBuilderUnavailableError. (xfail-skipped if reportlab is in
     the venv.)
  7. build_doctor_handout assembles correctly (dry_run).
  8. build_family_handover_pdf assembles correctly (dry_run).
  9. _escape collapses <, >, & safely.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from brain.common.pdf_guard import InsufficientSourcesError
from brain.docs.pdf_builder import (
    PDFBuilderUnavailableError,
    PDFCitationError,
    PdfDocument,
    PdfSection,
    _escape,
    build_doctor_handout,
    build_family_handover_pdf,
    build_pdf,
)

REPORTLAB_AVAILABLE = importlib.util.find_spec("reportlab") is not None

PUBMED_FIVE = [
    "https://pubmed.ncbi.nlm.nih.gov/7686614/",
    "https://pubmed.ncbi.nlm.nih.gov/32713850/",
    "https://pubmed.ncbi.nlm.nih.gov/19489084/",
    "https://doi.org/10.1001/jama.2020.0001",
    "https://clinicaltrials.gov/study/NCT00000000",
]


# ---------------------------------------------------------------------------
# 1. PdfSection level bounds
# ---------------------------------------------------------------------------
def test_pdf_section_level_4_rejected() -> None:
    with pytest.raises(Exception):
        PdfSection(heading="h", body="b", level=4)


def test_pdf_section_level_1_to_3_accepted() -> None:
    for level in (1, 2, 3):
        section = PdfSection(heading="h", body="b", level=level)
        assert section.level == level


# ---------------------------------------------------------------------------
# 2. Rule #12 - InsufficientSourcesError on < 5
# ---------------------------------------------------------------------------
def test_build_pdf_four_primary_sources_raises(tmp_path: Path) -> None:
    doc = PdfDocument(
        title="T",
        language="en",
        sections=[PdfSection(heading="h", body="b")],
        citations=PUBMED_FIVE[:4],
    )
    with pytest.raises(InsufficientSourcesError):
        build_pdf(doc, out_path=tmp_path / "x.pdf", dry_run=True)


# ---------------------------------------------------------------------------
# 3. PdfDocument with 5 PubMed citations passes
# ---------------------------------------------------------------------------
def test_build_pdf_five_pubmed_citations_passes_dry_run(
    tmp_path: Path,
) -> None:
    doc = PdfDocument(
        title="T",
        language="en",
        sections=[PdfSection(heading="h", body="b")],
        citations=PUBMED_FIVE,
    )
    result = build_pdf(doc, out_path=tmp_path / "x.pdf", dry_run=True)
    assert result == tmp_path / "x.pdf"
    assert not result.exists()  # dry_run does NOT write


# ---------------------------------------------------------------------------
# 4. Non-primary citation rejected at PdfDocument validation
# ---------------------------------------------------------------------------
def test_pdf_document_non_primary_citation_rejected() -> None:
    """Pydantic wraps the PDFCitationError raised in the validator
    into a ValidationError; assert the wrapped reason is propagated."""
    from pydantic import ValidationError

    bad = PUBMED_FIVE[:4] + ["personal note from Dr. Doe"]
    with pytest.raises(ValidationError) as excinfo:
        PdfDocument(
            title="T",
            language="en",
            sections=[PdfSection(heading="h", body="b")],
            citations=bad,
        )
    assert "primary-source pattern" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 5. dry_run returns path without writing (verified in test 3 too)
# ---------------------------------------------------------------------------
def test_dry_run_does_not_create_file(tmp_path: Path) -> None:
    out = tmp_path / "deep" / "tree" / "x.pdf"
    doc = PdfDocument(
        title="T",
        language="en",
        sections=[PdfSection(heading="h", body="b")],
        citations=PUBMED_FIVE,
    )
    result = build_pdf(doc, out_path=out, dry_run=True)
    assert result == out
    assert not out.exists()
    assert not out.parent.exists()  # mkdir is post-dry-run guard


# ---------------------------------------------------------------------------
# 6. reportlab-missing branch
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    REPORTLAB_AVAILABLE,
    reason="reportlab installed; ImportError branch unreachable",
)
def test_build_pdf_without_reportlab_raises(tmp_path: Path) -> None:
    doc = PdfDocument(
        title="T",
        language="en",
        sections=[PdfSection(heading="h", body="b")],
        citations=PUBMED_FIVE,
    )
    with pytest.raises(PDFBuilderUnavailableError):
        build_pdf(doc, out_path=tmp_path / "x.pdf", dry_run=False)


@pytest.mark.skipif(
    not REPORTLAB_AVAILABLE,
    reason="reportlab NOT installed; cannot test real write",
)
def test_build_pdf_with_reportlab_writes_file(tmp_path: Path) -> None:
    doc = PdfDocument(
        title="T",
        language="en",
        sections=[PdfSection(heading="h", body="b1\n\nb2")],
        citations=PUBMED_FIVE,
    )
    out = tmp_path / "real.pdf"
    result = build_pdf(doc, out_path=out, dry_run=False)
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 0
    head = out.read_bytes()[:4]
    assert head == b"%PDF"


# ---------------------------------------------------------------------------
# 7. build_doctor_handout convenience
# ---------------------------------------------------------------------------
def test_build_doctor_handout_dry_run(tmp_path: Path) -> None:
    out = tmp_path / "handout.pdf"
    result = build_doctor_handout(
        dim_summaries=[
            {"name": "cyst_volume_pct", "summary": "stable", "posterior_summary": "0.42 (HDI 0.21-0.61)"},
            {"name": "head_control_seconds", "summary": "improving"},
        ],
        scenarios=[
            {"label": "Vigabatrin trial", "description": "scenario A", "outcome_summary": "no change"},
        ],
        citations=PUBMED_FIVE,
        lang="en",
        out_path=out,
        dry_run=True,
    )
    assert result == out
    assert not out.exists()


def test_build_doctor_handout_insufficient_citations_raises(tmp_path: Path) -> None:
    with pytest.raises(InsufficientSourcesError):
        build_doctor_handout(
            dim_summaries=[{"name": "cyst", "summary": "s"}],
            scenarios=[{"label": "A", "description": "d"}],
            citations=PUBMED_FIVE[:3],
            out_path=tmp_path / "x.pdf",
            dry_run=True,
        )


# ---------------------------------------------------------------------------
# 8. build_family_handover_pdf convenience
# ---------------------------------------------------------------------------
def test_build_family_handover_pdf_dry_run(tmp_path: Path) -> None:
    out = tmp_path / "handover.pdf"
    result = build_family_handover_pdf(
        summary_sections=[
            {"heading": "ციფრული ტყუპის წვდომა", "body": "URL + login", "level": 1},
            {"heading": "კვირული შეკითხვა", "body": "Telegram flow", "level": 2},
        ],
        citations=PUBMED_FIVE,
        out_path=out,
        dry_run=True,
    )
    assert result == out
    assert not out.exists()


def test_build_family_handover_pdf_empty_sections_falls_back(
    tmp_path: Path,
) -> None:
    out = tmp_path / "handover.pdf"
    result = build_family_handover_pdf(
        summary_sections=[],
        citations=PUBMED_FIVE,
        out_path=out,
        dry_run=True,
    )
    assert result == out


# ---------------------------------------------------------------------------
# 9. _escape sanitizes
# ---------------------------------------------------------------------------
def test_escape_handles_specials() -> None:
    assert _escape("a & b") == "a &amp; b"
    assert _escape("<tag>") == "&lt;tag&gt;"
    assert _escape("plain") == "plain"
