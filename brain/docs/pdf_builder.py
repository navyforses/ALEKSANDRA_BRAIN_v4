# -*- coding: utf-8 -*-
"""Phase 7.7 PDF builder.

ReportLab-backed PDF assembler for two surfaces:

  * `build_doctor_handout` - EN clinical handout listing dimension
    summaries + scenario tables with citations.
  * `build_family_handover_pdf` - KA wife-facing handover summarizing
    what the system does + how to use it.

Both wrappers funnel into `build_pdf`, which calls the Phase 7.5
Rule #12 guard (`assert_min_primary_sources`) BEFORE any file is
written. A PDF lacking >= 5 primary sources never reaches disk.

Hard rules respected:
  * sync only (no asyncio)
  * no LLM calls
  * no PHI - synthetic inputs only in tests
  * no network I/O
  * reportlab is an OPTIONAL dependency; absence raises
    `PDFBuilderUnavailableError` (ImportError subclass) so callers
    can decide between skip / install / dry-run

Reference:
    v7_architecture/70_PHASES/77_PHASE_7_7_ACCEPTANCE_WINDOW_2W.md §2.1
    brain/common/pdf_guard.py
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from brain.common.pdf_guard import (
    PRIMARY_SOURCE_PATTERNS,
    assert_min_primary_sources,
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class PDFBuilderUnavailableError(ImportError):
    """Raised when reportlab is not installed.

    Tests can skip / xfail on this; callers can fall back to a
    Markdown-only path.
    """


class PDFCitationError(ValueError):
    """Raised when a citation does not match a primary-source pattern.

    Stronger than `InsufficientSourcesError` (which counts primaries):
    this rejects ANY citation string that is not itself a primary
    source. Used by `PdfDocument` field validation.
    """


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class PdfSection(BaseModel):
    """One section of a PDF document.

    `body` is markdown-lite: paragraphs separated by `\\n\\n`. No HTML
    is allowed (ReportLab `Paragraph` accepts a very small markup
    subset; we keep prose plain for safety + bilingual rendering).
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    heading: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    level: int = Field(default=1, ge=1, le=3)


class PdfDocument(BaseModel):
    """A complete PDF specification ready for `build_pdf`.

    `citations` MUST contain >= 5 entries that each match a
    `PRIMARY_SOURCE_PATTERNS` substring. Both the count rule (Rule
    #12) and the per-citation pattern rule are enforced.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    title: str = Field(..., min_length=1)
    subtitle: Optional[str] = None
    language: Literal["en", "ka"]
    sections: list[PdfSection] = Field(..., min_length=1)
    citations: list[str] = Field(..., min_length=1)
    author: str = "ALEKSANDRA_BRAIN v7"
    generated_at: Optional[datetime] = None

    @field_validator("citations")
    @classmethod
    def _validate_citation_patterns(cls, value: list[str]) -> list[str]:
        for i, citation in enumerate(value):
            if not isinstance(citation, str) or not citation.strip():
                raise PDFCitationError(f"citation[{i}] empty or non-string")
            lowered = citation.lower()
            if not any(p in lowered for p in PRIMARY_SOURCE_PATTERNS):
                raise PDFCitationError(
                    f"citation[{i}] does not match any primary-source "
                    f"pattern {PRIMARY_SOURCE_PATTERNS}: {citation!r}"
                )
        return value


# ---------------------------------------------------------------------------
# ReportLab import gate
# ---------------------------------------------------------------------------
def _require_reportlab() -> tuple[Any, ...]:
    """Import reportlab on demand; raise PDFBuilderUnavailableError if missing.

    Returns the small tuple of names build_pdf needs so call sites
    do not import reportlab at module top-level (keeps imports cheap
    when only models are needed).
    """
    try:
        from reportlab.lib.pagesizes import A4  # type: ignore
        from reportlab.lib.styles import getSampleStyleSheet  # type: ignore
        from reportlab.lib.units import cm  # type: ignore
        from reportlab.platypus import (  # type: ignore
            Paragraph,
            SimpleDocTemplate,
            Spacer,
        )
    except ImportError as exc:
        raise PDFBuilderUnavailableError(
            "reportlab not installed; install in .venv-v7 via "
            "'uv pip install reportlab'"
        ) from exc
    return A4, getSampleStyleSheet, cm, Paragraph, SimpleDocTemplate, Spacer


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------
def build_pdf(
    doc: PdfDocument,
    *,
    out_path: Path,
    dry_run: bool = False,
) -> Path:
    """Assemble `doc` into a PDF at `out_path`.

    Phase 7.5 Rule #12 enforcement (>= 5 primary citations) runs
    BEFORE any file I/O. If the rule fails, `InsufficientSourcesError`
    propagates and no file is written.

    Args:
        doc: validated PdfDocument.
        out_path: destination path (will be overwritten).
        dry_run: if True, perform validation only and return the path
            without writing the file. Useful in tests where reportlab
            is not installed.

    Returns:
        The path the PDF was (or would be) written to.

    Raises:
        InsufficientSourcesError: doc.citations has < 5 primary sources.
        PDFBuilderUnavailableError: reportlab missing and dry_run=False.
        PDFCitationError: caught at PdfDocument construction.
    """
    # Rule #12 - PHYSICAL pre-flush gate.
    assert_min_primary_sources(doc.citations, doc_id=doc.title)

    if dry_run:
        return out_path

    (
        A4,
        getSampleStyleSheet,
        cm,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    ) = _require_reportlab()

    out_path.parent.mkdir(parents=True, exist_ok=True)

    template = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        title=doc.title,
        author=doc.author,
    )
    styles = getSampleStyleSheet()

    # W2: KA docs need a Georgian-glyph font or every Mkhedruli character
    # renders as a tofu box. Provision strictly on ka (fail loudly rather than
    # silently ship boxes); EN docs never touch this path.
    if (doc.language or "").lower() == "ka":
        from brain.common.ka_font import ensure_ka_font

        ka_family = ensure_ka_font(strict=True)
        if ka_family:
            for _name in (
                "Title",
                "Heading1",
                "Heading2",
                "Heading3",
                "Italic",
                "BodyText",
            ):
                if _name in styles.byName:
                    styles[_name].fontName = ka_family

    flow: list[Any] = []

    # Header.
    flow.append(Paragraph(_escape(doc.title), styles["Title"]))
    if doc.subtitle:
        flow.append(Paragraph(_escape(doc.subtitle), styles["Heading2"]))
    generated = doc.generated_at or datetime.now(timezone.utc)
    flow.append(
        Paragraph(
            f"Generated {generated.isoformat(timespec='seconds')} "
            f"by {_escape(doc.author)} (lang={doc.language})",
            styles["Italic"],
        )
    )
    flow.append(Spacer(1, 0.5 * cm))

    # Sections.
    for section in doc.sections:
        heading_style = styles[f"Heading{section.level}"]
        flow.append(Paragraph(_escape(section.heading), heading_style))
        for paragraph in section.body.split("\n\n"):
            text = paragraph.strip()
            if text:
                flow.append(Paragraph(_escape(text), styles["BodyText"]))
                flow.append(Spacer(1, 0.2 * cm))
        flow.append(Spacer(1, 0.3 * cm))

    # References - mandatory section.
    flow.append(Paragraph("References", styles["Heading1"]))
    for i, citation in enumerate(doc.citations, start=1):
        flow.append(Paragraph(f"[{i}] {_escape(citation)}", styles["BodyText"]))

    template.build(flow)
    return out_path


# ---------------------------------------------------------------------------
# Convenience: doctor handout (EN)
# ---------------------------------------------------------------------------
def build_doctor_handout(
    *,
    dim_summaries: list[dict],
    scenarios: list[dict],
    citations: list[str],
    lang: Literal["en", "ka"] = "en",
    out_path: Path,
    dry_run: bool = False,
) -> Path:
    """Assemble a doctor handout PDF.

    Args:
        dim_summaries: list of dicts with keys `name`, `summary`,
            optional `posterior_summary` - one section per dimension.
        scenarios: list of dicts with keys `label`, `description`,
            optional `outcome_summary` - one section per scenario.
        citations: >= 5 primary-source strings.
        lang: en (default) for clinician audience; ka allowed.
        out_path: destination.
        dry_run: pass-through to build_pdf.

    Returns:
        Path the PDF was (or would be) written to.
    """
    sections: list[PdfSection] = []

    sections.append(
        PdfSection(
            heading="Patient context",
            body=(
                "Synthetic-input handout assembled by ALEKSANDRA_BRAIN v7. "
                "Use as decision-support context only; clinical decisions "
                "remain with the responsible clinician."
            ),
            level=1,
        )
    )

    if dim_summaries:
        sections.append(
            PdfSection(
                heading="Dimension summaries",
                body="Posterior summaries for each tracked dimension.",
                level=1,
            )
        )
        for dim in dim_summaries:
            name = str(dim.get("name", "unnamed dimension"))
            body_parts = [str(dim.get("summary", "")).strip()]
            posterior = dim.get("posterior_summary")
            if posterior:
                body_parts.append(f"Posterior: {posterior}")
            sections.append(
                PdfSection(
                    heading=name,
                    body="\n\n".join(p for p in body_parts if p),
                    level=2,
                )
            )

    if scenarios:
        sections.append(
            PdfSection(
                heading="Simulation scenarios",
                body="Forward-simulated counterfactual scenarios.",
                level=1,
            )
        )
        for scenario in scenarios:
            label = str(scenario.get("label", "unnamed scenario"))
            body_parts = [str(scenario.get("description", "")).strip()]
            outcome = scenario.get("outcome_summary")
            if outcome:
                body_parts.append(f"Outcome: {outcome}")
            sections.append(
                PdfSection(
                    heading=label,
                    body="\n\n".join(p for p in body_parts if p),
                    level=2,
                )
            )

    document = PdfDocument(
        title="Aleksandra Digital Twin - Doctor Handout",
        subtitle="Phase 7.7 acceptance-window evidence package",
        language=lang,
        sections=sections,
        citations=citations,
    )
    return build_pdf(document, out_path=out_path, dry_run=dry_run)


# ---------------------------------------------------------------------------
# Convenience: KA family handover
# ---------------------------------------------------------------------------
def build_family_handover_pdf(
    *,
    summary_sections: list[dict],
    citations: list[str],
    out_path: Path,
    dry_run: bool = False,
) -> Path:
    """Assemble the KA wife-facing handover PDF.

    Args:
        summary_sections: list of dicts with keys `heading`, `body`,
            optional `level` (default 1).
        citations: >= 5 primary-source strings.
        out_path: destination.
        dry_run: pass-through to build_pdf.

    Returns:
        Path the PDF was (or would be) written to.
    """
    sections: list[PdfSection] = []
    for sec in summary_sections:
        sections.append(
            PdfSection(
                heading=str(sec.get("heading", "")),
                body=str(sec.get("body", "")),
                level=int(sec.get("level", 1)),
            )
        )
    if not sections:
        sections.append(
            PdfSection(
                heading="ციფრული ტყუპის გადაცემა",
                body=(
                    "ALEKSANDRA_BRAIN v7 ფამილი-handover. " "დეტალები web cockpit-ში."
                ),
                level=1,
            )
        )

    document = PdfDocument(
        title="ALEKSANDRA_BRAIN v7 - ოჯახური გადაცემა",
        subtitle="Phase 7.7 KA handover",
        language="ka",
        sections=sections,
        citations=citations,
    )
    return build_pdf(document, out_path=out_path, dry_run=dry_run)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _escape(text: str) -> str:
    """ReportLab `Paragraph` accepts a Markup-like syntax (`<`, `>`,
    `&` are special). Escape the three reserved characters so user
    text never breaks the renderer.
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


__all__ = [
    "PDFBuilderUnavailableError",
    "PDFCitationError",
    "PdfDocument",
    "PdfSection",
    "build_doctor_handout",
    "build_family_handover_pdf",
    "build_pdf",
]
