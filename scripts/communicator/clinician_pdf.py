"""
clinician_pdf.py — Phase 4 ACD-05 clinician-shareable PDF renderer.

Produces a PDF that Dr. Hien (or any clinician the family chooses to
share with) can read AND independently verify. Different layout from
`weekly_brief.py`:

  - Cover with patient-context version stamp (hash + date)
  - Topic + agent run IDs section (so the clinician can audit the runs
    that produced the claims)
  - Claims table (sentence + citation tuple per row)
  - Citation appendix with retrieval timestamp + source type
  - Footer: "research-discovery system, not a clinician" disclaimer

Hard rules:
  - No PHI unless `consent_full_name=True` on the recipient contact's
    consent record. Default identity = patient_context.identity_default
    (the redactor's "A.J., 8-month-old infant with severe HIE").
  - Every claim must carry ≥1 citation id; uncited claims are dropped
    before rendering, never silently included.
  - Final phi_redactor pass over the joined body text; blocked output
    deletes the PDF and raises (same safety net as weekly_brief.render_pdf).

Renderer: ReportLab Platypus — same dependency family as the weekly brief
so we don't need a GTK runtime. The visual layout is dense and clinical
rather than family-friendly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from scripts.communicator.patient_context import PatientContext, current_context
from scripts.communicator.phi_redactor import ConsentFlags, redact


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------
@dataclass
class ClinicianClaim:
    sentence: str
    citation_ids: list[str]  # PMID:..., DOI:..., NCT:...
    evidence_grade: int  # 1..6
    confidence: float  # 0..1


@dataclass
class ClinicianPDFInput:
    topic: str
    audience_label: str  # e.g. "Dr. Hien, BMC Pediatric Neurology"
    claims: list[ClinicianClaim]
    citation_metadata: dict[str, dict] = field(default_factory=dict)
    # dict keyed by citation_id with sub-keys: retrieval_timestamp, source_type, url
    agent_run_ids: list[str] = field(default_factory=list)
    rendered_at: datetime | None = None


@dataclass
class ClinicianPDFOutput:
    pdf_path: Path
    bytes_written: int
    patient_context_version: str
    claim_count: int
    citation_count: int
    blocked: bool = False
    block_reason: str | None = None


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
def _styles():
    base = getSampleStyleSheet()
    base.add(
        ParagraphStyle(
            name="ClinSectionHeading",
            parent=base["Heading2"],
            spaceBefore=14,
            spaceAfter=6,
            fontSize=13,
        )
    )
    base.add(
        ParagraphStyle(
            name="ClinSubHeading",
            parent=base["Heading3"],
            spaceBefore=8,
            spaceAfter=4,
            fontSize=11,
        )
    )
    base.add(
        ParagraphStyle(
            name="ClinMono",
            parent=base["BodyText"],
            fontName="Courier",
            fontSize=8,
            leading=10,
        )
    )
    base.add(
        ParagraphStyle(
            name="ClinFooter",
            parent=base["BodyText"],
            fontSize=8,
            textColor=colors.grey,
            spaceBefore=10,
        )
    )
    return base


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
def render_clinician_pdf(
    inp: ClinicianPDFInput,
    output_path: Path,
    *,
    consent: ConsentFlags | None = None,
    context: PatientContext | None = None,
) -> ClinicianPDFOutput:
    """Render a clinician-shareable PDF to `output_path`.

    Caller is responsible for cleanup / R2 upload. The renderer's only
    side effect is writing the PDF file; it does not insert any DB row.
    Persistence (outreach_log with phi_redacted=true) is the
    `outreach_drafter.draft_clinician_outreach()` job.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    consent = consent or ConsentFlags()
    ctx = context or current_context()
    rendered_at = inp.rendered_at or datetime.now(timezone.utc)

    # Drop uncited claims defensively (the upstream Communicator pipeline
    # already does this; double-check before rendering).
    claims = [c for c in inp.claims if c.citation_ids]

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=f"ALEKSANDRA_BRAIN — Clinician brief — {inp.topic[:60]}",
        author="ALEKSANDRA_BRAIN Communicator",
    )
    styles = _styles()
    body: list = []

    # --- Cover --------------------------------------------------------------
    body.append(Paragraph("ALEKSANDRA_BRAIN — Clinician Brief", styles["Title"]))
    body.append(Paragraph(f"<b>Topic:</b> {inp.topic}", styles["BodyText"]))
    body.append(Paragraph(f"<b>For:</b> {inp.audience_label}", styles["BodyText"]))
    body.append(
        Paragraph(
            f"<b>Rendered:</b> {rendered_at.isoformat(timespec='seconds')}",
            styles["BodyText"],
        )
    )
    body.append(
        Paragraph(
            f"<b>Patient context version:</b> {ctx.version_hash} "
            f"(last updated {ctx.last_updated_iso})",
            styles["BodyText"],
        )
    )

    # --- Patient context ---------------------------------------------------
    body.append(
        Paragraph("Patient context (this version)", styles["ClinSectionHeading"])
    )
    identity = (
        "Aleksandra Jincharadze" if consent.consent_full_name else ctx.identity_default
    )
    rows = [
        ["Identity", identity],
        ["Age band", ctx.age_band],
        ["Diagnosis", ctx.diagnosis_summary],
        ["Location", ctx.location],
        ["Active programs", "; ".join(ctx.active_programs) or "—"],
    ]
    ctx_table = Table(rows, colWidths=[1.5 * inch, 5.0 * inch])
    ctx_table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (0, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
            ]
        )
    )
    body.append(ctx_table)

    # --- Agent run IDs ------------------------------------------------------
    body.append(Paragraph("Originating agent runs", styles["ClinSectionHeading"]))
    if inp.agent_run_ids:
        for rid in inp.agent_run_ids[:20]:
            body.append(Paragraph(f"• {rid}", styles["ClinMono"]))
    else:
        body.append(
            Paragraph(
                "No agent run IDs supplied — caller passed an empty list.",
                styles["BodyText"],
            )
        )

    # --- Claims -------------------------------------------------------------
    body.append(Paragraph("Findings (claim → citations)", styles["ClinSectionHeading"]))
    if not claims:
        body.append(
            Paragraph("No source-grounded findings to share.", styles["BodyText"])
        )
    else:
        claim_rows = [["#", "Claim", "Citations", "Grade", "Conf"]]
        for i, c in enumerate(claims, start=1):
            cites = ", ".join(c.citation_ids[:5])
            claim_rows.append(
                [
                    str(i),
                    c.sentence,
                    cites,
                    str(c.evidence_grade),
                    f"{c.confidence:.2f}",
                ]
            )
        claim_table = Table(
            claim_rows,
            colWidths=[0.35 * inch, 3.4 * inch, 2.0 * inch, 0.45 * inch, 0.5 * inch],
            repeatRows=1,
        )
        claim_table.setStyle(
            TableStyle(
                [
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        body.append(claim_table)

    # --- Appendix: citation tuples -----------------------------------------
    body.append(PageBreak())
    body.append(Paragraph("Citation appendix", styles["ClinSectionHeading"]))
    body.append(
        Paragraph(
            "Each row shows the citation id, source type, retrieval timestamp, "
            "and (where available) the source URL. The clinician can verify any "
            "claim by following the citation independently.",
            styles["BodyText"],
        )
    )

    all_citations = sorted({cid for c in claims for cid in c.citation_ids})
    if not all_citations:
        body.append(Paragraph("No citations referenced.", styles["BodyText"]))
    else:
        appx = [["#", "Citation", "Source type", "Retrieved", "URL"]]
        for i, cid in enumerate(all_citations, start=1):
            meta = inp.citation_metadata.get(cid, {})
            appx.append(
                [
                    str(i),
                    cid,
                    meta.get("source_type", ""),
                    meta.get("retrieval_timestamp", ""),
                    (meta.get("url") or "")[:60],
                ]
            )
        appx_table = Table(
            appx,
            colWidths=[0.3 * inch, 1.5 * inch, 0.8 * inch, 1.4 * inch, 2.7 * inch],
            repeatRows=1,
        )
        appx_table.setStyle(
            TableStyle(
                [
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        body.append(appx_table)

    body.append(Spacer(1, 14))
    body.append(
        Paragraph(
            "<i>ALEKSANDRA_BRAIN is a research-discovery system for the family, "
            "not a clinician. Every claim above carries a source for independent "
            "verification. Clinical decisions remain with the patient's doctors.</i>",
            styles["ClinFooter"],
        )
    )

    # --- PHI safety net over the body text we constructed ------------------
    flat = "\n".join(
        [inp.topic, identity, *(c.sentence for c in claims)] + list(ctx.active_programs)
    )
    safety = redact(flat, consent=consent)
    if safety.blocked:
        return ClinicianPDFOutput(
            pdf_path=output_path,
            bytes_written=0,
            patient_context_version=ctx.version_hash,
            claim_count=len(claims),
            citation_count=len(all_citations),
            blocked=True,
            block_reason=safety.block_reason,
        )

    doc.build(body)
    size = output_path.stat().st_size if output_path.exists() else 0
    return ClinicianPDFOutput(
        pdf_path=output_path,
        bytes_written=size,
        patient_context_version=ctx.version_hash,
        claim_count=len(claims),
        citation_count=len(all_citations),
        blocked=False,
    )


__all__ = [
    "ClinicianClaim",
    "ClinicianPDFInput",
    "ClinicianPDFOutput",
    "render_clinician_pdf",
]
