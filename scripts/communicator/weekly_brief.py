"""
weekly_brief.py — Phase 3 CGM-05 weekly brief PDF renderer.

Renders a one-page (or short multi-page) PDF summary of what changed in
the project over the last 7 days, with a citation appendix that lists
every PMID/DOI/NCT/URL referenced in the body.

Sections (per Phase 3 plan — empty sections render "No new items this
week" rather than disappear, per CGM-05):

  1. Cover           — week range, generated timestamp, redaction mode
  2. Summary         — short prose; this week's headline + open decisions
  3. New evidence    — top papers / trials / preprints from last 7 days
  4. Hypotheses      — confirmed / changed this week
  5. Repurposing     — therapy candidates worth monitoring
  6. Outreach queue  — drafts pending Shako review, drafts sent this week
  7. Family questions — items from scripts/communicator/questions_queue.yaml
  8. Citations       — appendix listing every source referenced above

Renderer: ReportLab Platypus (Frame + Paragraph + Table + Spacer).
Chosen over weasyprint because the Windows family workstation lacks the
GTK runtime weasyprint depends on. Trade-off documented in
TRIAGE_PLAN_PHASE_3.md risk register.

PDF output path: `briefs/<week_start_iso>.pdf` under the configured
output directory (defaults to ./briefs/ on disk; R2 upload is the
weekly_brief.json workflow's job).

The renderer never inserts a row into the `briefs` table. The caller
(workflow or manual script) decides whether to persist; persistence
requires `phi_redacted=true` via the migration-008 CHECK constraint.

Usage:
    .venv/Scripts/python.exe -X utf8 -m scripts.communicator.weekly_brief \\
        --week-start 2026-05-18 --output briefs/2026-05-18.pdf

    .venv/Scripts/python.exe -X utf8 -m scripts.communicator.weekly_brief \\
        --dry-run --output briefs/dry_run.pdf
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import psycopg2
import yaml
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

from scripts.communicator.phi_redactor import ConsentFlags, redact
from scripts.ledger import load_env


ROOT = Path(__file__).resolve().parent.parent.parent
QUESTIONS_QUEUE_PATH = ROOT / "scripts" / "communicator" / "questions_queue.yaml"


# ---------------------------------------------------------------------------
# Phase 6 I18N-06 / D-02 — bilingual emission for briefs.sections
# ---------------------------------------------------------------------------
# Option A (deterministic-mirror, zero Anthropic cost) per RESEARCH.md Pattern 6:
# the 5 fixed summary-line templates produced by collect_sections() are mirrored
# into {en, ka} via the lookup table below. The Communicator agent's per-row
# inserts (hypotheses/therapies/aleksandra_timeline) use Option B (compose_bilingual)
# — see agents/communicator.py.
#
# TODO(Phase 6 execute): Shako sanity-check the Georgian phrasing of these 5
# template strings before this plan's commit is merged. The translations follow
# evidence-grade descriptive Georgian (not imperatives) so they cannot trigger
# the D-05 imperative-verb lint extended by plan 06-11. Polite-plural avoided
# where bare descriptive forms read naturally to a family audience.
#
# Templates map 1:1 to the f-strings in collect_sections() lines ~359-365.
# Counts substituted via str.format(n=...) before {en, ka} emission.
SUMMARY_TEMPLATES_KA: dict[str, str] = {
    "papers": "ამ კვირას {n} ახალი რელევანტური სტატია.",
    "hypotheses": "{n} ჰიპოთეზის განახლება.",
    "therapies": "{n} თერაპიის კანდიდატი აქტიური მონიტორინგის ქვეშ.",
    "outreach_pending": "{n} გასაგზავნი მონახაზი მიმოხილვისთვის.",
    "open_questions": "{n} ღია ოჯახური კითხვა.",
}

SUMMARY_TEMPLATES_EN: dict[str, str] = {
    "papers": "{n} new relevant papers this week.",
    "hypotheses": "{n} hypothesis updates.",
    "therapies": "{n} therapy candidates under active monitoring.",
    "outreach_pending": "{n} outreach drafts pending review.",
    "open_questions": "{n} open family questions.",
}


def _bilingual_line(key: str, *, n: int) -> dict[str, str]:
    """Render a {en, ka} pair for a summary-line template key.

    Option A — deterministic prose mirror; no Anthropic call.
    """
    return {
        "en": SUMMARY_TEMPLATES_EN[key].format(n=n),
        "ka": SUMMARY_TEMPLATES_KA[key].format(n=n),
    }


def _bilingual_mirror(value: str | None) -> dict[str, str]:
    """Mirror a single English string into {en, ka} with both halves identical.

    Used for per-row title/name fields inside briefs.sections that originate
    from already-stored DB rows. Once those source tables go through migration
    012 + the Communicator's compose_bilingual write path, this mirror becomes
    a safety net (returns whatever upstream already bilingualized).
    """
    s = value or ""
    return {"en": s, "ka": s}


# ---------------------------------------------------------------------------
# Brief data shape
# ---------------------------------------------------------------------------
@dataclass
class PaperRow:
    title: str
    citation_id: str  # PMID:..., DOI:..., NCT:..., URL or ledger:...
    ingested_at: str
    relevance_score: float | None


@dataclass
class HypothesisRow:
    title: str
    status: str
    confidence: str | None
    reviewed_at: str | None
    supporting: list[str]


@dataclass
class TherapyRow:
    name: str
    therapy_type: str | None
    aleksandra_status: str | None
    evidence_in_hie: str | None


@dataclass
class OutreachRow:
    subject: str
    language: str
    drafted_at: str
    sent_at: str | None
    contact_label: str
    confidence: float | None


@dataclass
class QuestionRow:
    id: str
    question: str
    context: str
    asked_at: str
    status: str


@dataclass
class BriefSections:
    week_start: date
    week_end: date
    generated_at: datetime
    # Phase 6 I18N-06: summary_lines is a list of {en, ka} dicts now (was list[str]
    # pre-06-09). The PDF renderer reads .en for display; .ka is persisted into
    # briefs.sections JSONB for the Telegram audience.
    summary_lines: list[dict[str, str]] = field(default_factory=list)
    papers: list[PaperRow] = field(default_factory=list)
    hypotheses: list[HypothesisRow] = field(default_factory=list)
    therapies: list[TherapyRow] = field(default_factory=list)
    outreach: list[OutreachRow] = field(default_factory=list)
    questions: list[QuestionRow] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)  # appendix rows

    def to_dict(self) -> dict:
        """Serialisable form for the `briefs.sections` JSONB column.

        Phase 6 I18N-06: family-visible body fields are emitted as `{en, ka}`
        per migration 012's reshape. Summary lines come pre-bilingualized from
        collect_sections() via _bilingual_line(); per-row title/name fields are
        mirrored via _bilingual_mirror() (Option A — zero Anthropic cost).

        Internal-only metadata (citation_id, ingested_at, dates, scores,
        statuses, languages) STAYS as scalar strings — not family-visible prose.
        """
        return {
            "week_start": self.week_start.isoformat(),
            "week_end": self.week_end.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            # summary_lines: already a list of {en, ka} pairs from collect_sections()
            "summary_lines": self.summary_lines,
            "papers": [
                {
                    "title": _bilingual_mirror(p.title),
                    "citation_id": p.citation_id,
                    "ingested_at": p.ingested_at,
                    "relevance_score": p.relevance_score,
                }
                for p in self.papers
            ],
            "hypotheses": [
                {
                    "title": _bilingual_mirror(h.title),
                    "status": h.status,
                    "confidence": h.confidence,
                    "reviewed_at": h.reviewed_at,
                    "supporting": h.supporting,
                }
                for h in self.hypotheses
            ],
            "therapies": [
                {
                    "name": _bilingual_mirror(t.name),
                    "therapy_type": t.therapy_type,
                    "aleksandra_status": t.aleksandra_status,
                    "evidence_in_hie": t.evidence_in_hie,
                }
                for t in self.therapies
            ],
            "outreach": [
                {
                    "subject": _bilingual_mirror(o.subject),
                    "language": o.language,
                    "drafted_at": o.drafted_at,
                    "sent_at": o.sent_at,
                    "contact_label": o.contact_label,
                    "confidence": o.confidence,
                }
                for o in self.outreach
            ],
            "questions": [
                {
                    "id": q.id,
                    "question": _bilingual_mirror(q.question),
                    "context": _bilingual_mirror(q.context),
                    "asked_at": q.asked_at,
                    "status": q.status,
                }
                for q in self.questions
            ],
            "citations": self.citations,
        }


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------
def _connect():
    load_env()
    return psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")


def _build_citation_id(source_type: str | None, source_id: str | None) -> str:
    if not source_type or not source_id:
        return "URL:n/a"
    if source_type == "pubmed":
        return f"PMID:{source_id}"
    if source_type == "ctgov":
        return f"NCT:{source_id}"
    if source_type in {"biorxiv", "medrxiv", "doi"}:
        return f"DOI:{source_id}"
    if source_type == "url":
        return f"URL:{source_id}"
    return f"{source_type}:{source_id}"


def collect_sections(
    week_start: date,
    *,
    fixture: bool = False,
) -> BriefSections:
    """Pull last-week data from Supabase, or build a fixture-only brief.

    Fixture mode is used by the verifier to keep CGM-05 deterministic and
    independent of whether the project has fresh data this week.
    """
    week_end = week_start + timedelta(days=6)
    generated_at = datetime.now(timezone.utc)

    sections = BriefSections(
        week_start=week_start,
        week_end=week_end,
        generated_at=generated_at,
    )
    sections.questions = _load_questions()

    if fixture:
        # Phase 6 I18N-06: fixture summary lines emitted as {en, ka} dicts.
        # The Georgian halves use the same descriptive (non-imperative) register
        # required by the D-05 banned-imperative lint extended in plan 06-11.
        sections.summary_lines = [
            {
                "en": (
                    "This is a fixture render used by CGM-05 — not a real "
                    "weekly brief."
                ),
                "ka": (
                    "ეს არის CGM-05-ის ფიქსტურა — არ წარმოადგენს რეალურ "
                    "კვირეულ მონახაზს."
                ),
            },
            {
                "en": (
                    "Every section below carries a placeholder row so the "
                    "renderer is exercised end-to-end."
                ),
                "ka": (
                    "ქვემოთ ყველა სექციას აქვს ჩანაცვლების ჩანაწერი, რათა "
                    "რენდერერი სრულად შემოწმდეს."
                ),
            },
        ]
        sections.papers = [
            PaperRow(
                title="Fixture paper — cord blood for severe HIE (placeholder)",
                citation_id="PMID:0000001",
                ingested_at=generated_at.isoformat(),
                relevance_score=0.91,
            )
        ]
        sections.hypotheses = [
            HypothesisRow(
                title="Fixture hypothesis — vigabatrin washout interaction",
                status="confirmed",
                confidence="medium",
                reviewed_at=generated_at.isoformat(),
                supporting=["PMID:0000001"],
            )
        ]
        sections.therapies = [
            TherapyRow(
                name="Fixture therapy — cord blood (placeholder)",
                therapy_type="cell",
                aleksandra_status="evaluating",
                evidence_in_hie="promising",
            )
        ]
        sections.outreach = [
            OutreachRow(
                subject="Fixture outreach subject",
                language="en",
                drafted_at=generated_at.isoformat(),
                sent_at=None,
                contact_label="researcher (placeholder)",
                confidence=0.62,
            )
        ]
        sections.citations = ["PMID:0000001"]
        sections.summary_lines.append(
            {
                "en": "Citation appendix exercised with 1 entry (PMID:0000001).",
                "ka": "ციტირების დანართი შესრულდა 1 ჩანაწერით (PMID:0000001).",
            }
        )
        return sections

    # Live pulls — last 7 days
    conn = _connect()
    try:
        with conn.cursor() as cur:
            # Top 3 papers by relevance from last 7 days
            cur.execute(
                """
                SELECT
                  p.title,
                  CASE
                    WHEN p.pmid IS NOT NULL THEN 'pubmed'
                    WHEN p.ct_id IS NOT NULL THEN 'ctgov'
                    WHEN p.doi IS NOT NULL THEN COALESCE(l.source_type, 'doi')
                    ELSE 'url'
                  END AS source_type,
                  COALESCE(p.pmid, p.ct_id, p.doi, p.source_url) AS source_id,
                  COALESCE(l.retrieval_timestamp, p.ingested_at) AS retrieved_at,
                  p.relevance_score
                FROM papers p
                LEFT JOIN evidence_ledger l
                  ON l.mode = 'positive'
                 AND (
                   (l.source_type = 'pubmed' AND l.source_id = p.pmid)
                   OR (l.source_type = 'ctgov' AND l.source_id = p.ct_id)
                   OR (l.source_type IN ('biorxiv', 'medrxiv') AND l.source_id = p.doi)
                 )
                WHERE COALESCE(l.retrieval_timestamp, p.ingested_at) >= %s
                ORDER BY p.relevance_score DESC NULLS LAST
                LIMIT 3
                """,
                (datetime.combine(week_start, datetime.min.time(), timezone.utc),),
            )
            for title, source_type, source_id, ts, score in cur.fetchall():
                cid = _build_citation_id(source_type, source_id)
                sections.papers.append(
                    PaperRow(
                        title=title or "(untitled)",
                        citation_id=cid,
                        ingested_at=ts.isoformat() if ts else "",
                        relevance_score=float(score) if score is not None else None,
                    )
                )
                if cid not in sections.citations:
                    sections.citations.append(cid)

            # Hypotheses confirmed or status-changed this week
            cur.execute(
                """
                SELECT title, status, confidence_level, reviewed_at, supporting_papers
                FROM hypotheses
                WHERE COALESCE(reviewed_at, created_at) >= %s
                ORDER BY COALESCE(reviewed_at, created_at) DESC
                LIMIT 10
                """,
                (datetime.combine(week_start, datetime.min.time(), timezone.utc),),
            )
            for title, status, conf, ts, supporting in cur.fetchall():
                supp = supporting or []
                sections.hypotheses.append(
                    HypothesisRow(
                        title=title or "(untitled)",
                        status=status or "unknown",
                        confidence=conf,
                        reviewed_at=ts.isoformat() if ts else None,
                        supporting=list(supp)[:5],
                    )
                )

            # Repurposing watch — active therapy candidates
            cur.execute(
                """
                SELECT name, therapy_type, aleksandra_status, evidence_in_hie
                FROM therapies
                WHERE aleksandra_status IN ('evaluating', 'applied', 'planned')
                ORDER BY name ASC
                LIMIT 10
                """
            )
            for name, ttype, astatus, evidence in cur.fetchall():
                sections.therapies.append(
                    TherapyRow(
                        name=name or "(unnamed)",
                        therapy_type=ttype,
                        aleksandra_status=astatus,
                        evidence_in_hie=evidence,
                    )
                )

            # Outreach drafts in the window
            cur.execute(
                """
                SELECT subject, language, drafted_at, sent_at, contact_id, confidence
                FROM outreach_log
                WHERE drafted_at >= %s
                ORDER BY drafted_at DESC
                LIMIT 10
                """,
                (datetime.combine(week_start, datetime.min.time(), timezone.utc),),
            )
            outreach_rows = cur.fetchall()
            for subject, lang, drafted, sent, contact_id, conf in outreach_rows:
                # Resolve contact role for display label (no PHI)
                cur.execute(
                    "SELECT contact_type FROM contacts WHERE id = %s",
                    (contact_id,),
                )
                role_row = cur.fetchone()
                role = role_row[0] if role_row else "contact"
                sections.outreach.append(
                    OutreachRow(
                        subject=subject or "(no subject)",
                        language=lang or "en",
                        drafted_at=drafted.isoformat() if drafted else "",
                        sent_at=sent.isoformat() if sent else None,
                        contact_label=role,
                        confidence=float(conf) if conf is not None else None,
                    )
                )
    finally:
        conn.close()

    # Summary lines — built from the section counts.
    # Phase 6 I18N-06 / D-02: each line is a {en, ka} pair, rendered via the
    # SUMMARY_TEMPLATES_KA + SUMMARY_TEMPLATES_EN lookup tables (Option A —
    # deterministic prose mirror, zero Anthropic cost).
    pending_outreach = len([o for o in sections.outreach if not o.sent_at])
    sections.summary_lines = [
        _bilingual_line("papers", n=len(sections.papers)),
        _bilingual_line("hypotheses", n=len(sections.hypotheses)),
        _bilingual_line("therapies", n=len(sections.therapies)),
        _bilingual_line("outreach_pending", n=pending_outreach),
        _bilingual_line("open_questions", n=len(sections.questions)),
    ]
    return sections


def _load_questions() -> list[QuestionRow]:
    if not QUESTIONS_QUEUE_PATH.exists():
        return []
    with QUESTIONS_QUEUE_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    items = data.get("questions", []) or []
    rows: list[QuestionRow] = []
    for q in items:
        if (q.get("status") or "open").lower() != "open":
            continue
        rows.append(
            QuestionRow(
                id=q.get("id", ""),
                question=q.get("question", "")[:300],
                context=q.get("context", "")[:300],
                asked_at=q.get("asked_at", ""),
                status=q.get("status", "open"),
            )
        )
    return rows


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _styles():
    base = getSampleStyleSheet()
    base.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=base["Heading2"],
            spaceBefore=12,
            spaceAfter=6,
            fontSize=13,
        )
    )
    base.add(
        ParagraphStyle(
            name="Mono",
            parent=base["BodyText"],
            fontName="Courier",
            fontSize=8,
            leading=10,
        )
    )
    return base


_EMPTY = "No new items this week."


def _section(flowables: list, styles, title: str, items: list, render_item):
    flowables.append(Paragraph(title, styles["SectionHeading"]))
    if not items:
        flowables.append(Paragraph(_EMPTY, styles["BodyText"]))
        return
    for item in items:
        flowables.append(render_item(item, styles))
    flowables.append(Spacer(1, 6))


def render_pdf(sections: BriefSections, output_path: Path) -> Path:
    """Write the brief to a PDF. Output_path's parent is created if needed."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=f"ALEKSANDRA_BRAIN Weekly Brief {sections.week_start.isoformat()}",
        author="ALEKSANDRA_BRAIN Communicator",
    )
    styles = _styles()
    body: list = []

    # --- Cover ---------------------------------------------------------------
    body.append(Paragraph("ALEKSANDRA_BRAIN — Weekly Brief", styles["Title"]))
    body.append(
        Paragraph(
            f"Week of {sections.week_start.isoformat()} – {sections.week_end.isoformat()}",
            styles["BodyText"],
        )
    )
    body.append(
        Paragraph(
            f"Generated {sections.generated_at.isoformat(timespec='seconds')}",
            styles["BodyText"],
        )
    )
    body.append(
        Paragraph(
            "Redaction mode: maximally protective (default identity "
            '"A.J., 8-month-old infant with severe HIE"). '
            "Approval: this PDF is a draft — Shako reviews before any send.",
            styles["BodyText"],
        )
    )

    # --- Summary -------------------------------------------------------------
    body.append(Paragraph("This week, in short", styles["SectionHeading"]))
    if sections.summary_lines:
        for line in sections.summary_lines:
            # Phase 6 I18N-06: lines are {en, ka} dicts; PDF renders the
            # English half (ReportLab's default fonts don't render Mkhedruli
            # reliably; the .ka half is preserved in briefs.sections JSONB
            # for the Telegram audience routing landed in plan 06-12).
            en_text = line["en"] if isinstance(line, dict) else str(line)
            body.append(Paragraph("• " + en_text, styles["BodyText"]))
    else:
        body.append(Paragraph(_EMPTY, styles["BodyText"]))

    # --- Sections ------------------------------------------------------------
    _section(
        body,
        styles,
        "New evidence",
        sections.papers,
        lambda p, s: Paragraph(
            f"• <b>{p.title}</b> "
            f"[{p.citation_id}, relevance={p.relevance_score if p.relevance_score is not None else 'n/a'}]",
            s["BodyText"],
        ),
    )
    _section(
        body,
        styles,
        "Hypothesis updates",
        sections.hypotheses,
        lambda h, s: Paragraph(
            f"• <b>{h.title}</b> — status={h.status}, "
            f"confidence={h.confidence or 'n/a'}, "
            f"supporting={len(h.supporting)} citation(s)",
            s["BodyText"],
        ),
    )
    _section(
        body,
        styles,
        "Repurposing watch",
        sections.therapies,
        lambda t, s: Paragraph(
            f"• <b>{t.name}</b> — type={t.therapy_type or 'n/a'}, "
            f"status={t.aleksandra_status or 'n/a'}, "
            f"HIE evidence={t.evidence_in_hie or 'n/a'}",
            s["BodyText"],
        ),
    )
    _section(
        body,
        styles,
        "Outreach queue",
        sections.outreach,
        lambda o, s: Paragraph(
            f"• [{o.contact_label}] {o.subject} "
            f"({o.language}, conf={o.confidence if o.confidence is not None else 'n/a'}) — "
            f"{'sent' if o.sent_at else 'pending review'}",
            s["BodyText"],
        ),
    )
    _section(
        body,
        styles,
        "Open family questions",
        sections.questions,
        lambda q, s: Paragraph(
            f"• <b>{q.question}</b><br/>"
            f"<font size=8 color='#555'>{q.context}</font>",
            s["BodyText"],
        ),
    )

    # --- Appendix: citations -------------------------------------------------
    body.append(PageBreak())
    body.append(Paragraph("Citation appendix", styles["SectionHeading"]))
    if not sections.citations:
        body.append(Paragraph(_EMPTY, styles["BodyText"]))
    else:
        rows = [["#", "Source ID"]]
        for i, cid in enumerate(sections.citations, start=1):
            rows.append([str(i), cid])
        tbl = Table(rows, colWidths=[0.5 * inch, 6.0 * inch])
        tbl.setStyle(
            TableStyle(
                [
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                ]
            )
        )
        body.append(tbl)

    body.append(Spacer(1, 12))
    body.append(
        Paragraph(
            "<i>ALEKSANDRA_BRAIN is a research-discovery system, not a clinician. "
            "Every claim above carries a source. Clinical decisions remain with Aleksandra's doctors.</i>",
            styles["BodyText"],
        )
    )

    doc.build(body)

    # Run the final body text through phi_redactor as a safety net — the
    # rendered PDF is opaque to the redactor, but the in-memory section text
    # is available. We re-check the joined text for PHI patterns that might
    # have slipped past the upstream pipeline.
    # Phase 6 I18N-06: summary_lines is list[dict[str, str]] now; flatten BOTH
    # halves so the redactor sweeps Georgian PHI patterns too (plan 06-10 made
    # the redactor bilingual-aware).
    summary_strings: list[str] = []
    for line in sections.summary_lines:
        if isinstance(line, dict):
            summary_strings.append(line.get("en", ""))
            summary_strings.append(line.get("ka", ""))
        else:
            summary_strings.append(str(line))
    flat = "\n".join([*summary_strings, *(p.title for p in sections.papers)])
    safety = redact(flat, consent=ConsentFlags())
    if safety.blocked:
        # If the safety net trips, remove the PDF and refuse — caller must
        # rewrite the upstream evidence before re-rendering.
        try:
            output_path.unlink()
        except OSError:
            pass
        raise RuntimeError(
            f"weekly_brief safety-net redactor blocked: {safety.block_reason}"
        )
    return output_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--week-start",
        type=date.fromisoformat,
        default=None,
        help="ISO date YYYY-MM-DD; default = the most recent past Sunday.",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="PDF output path. Default: briefs/<week-start>.pdf",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Render from fixture data — no DB pulls.",
    )
    ap.add_argument(
        "--bilingual-test",
        action="store_true",
        help=(
            "Phase 6 I18N-06 verifier hook: emit the bilingual sections dict as "
            "JSON to stdout (no PDF). Intended to be combined with --dry-run so "
            "the verifier can assert summary_lines[0].en and .ka are non-empty."
        ),
    )
    args = ap.parse_args(argv)

    if args.week_start is None:
        today = date.today()
        # Most recent Sunday on or before today (date.weekday: Mon=0..Sun=6)
        days_since_sunday = (today.weekday() + 1) % 7
        args.week_start = today - timedelta(days=days_since_sunday)

    if args.output is None:
        args.output = ROOT / "briefs" / f"{args.week_start.isoformat()}.pdf"

    sections = collect_sections(args.week_start, fixture=args.dry_run)

    # Phase 6 I18N-06 verifier hook: emit the bilingual sections dict to stdout
    # as JSON. NO PDF is rendered (skips ReportLab + the safety-net redactor).
    # The verifier asserts summary_lines[0].en and .ka are non-empty strings.
    if args.bilingual_test:
        import json as _json  # noqa: PLC0415

        sd = sections.to_dict()
        print(_json.dumps(sd, ensure_ascii=False, default=str, indent=2))
        return 0

    path = render_pdf(sections, args.output)
    print(f"weekly brief rendered: {path} ({path.stat().st_size} bytes)")
    print(f"citations: {len(sections.citations)}")
    return 0


__all__ = [
    "BriefSections",
    "PaperRow",
    "HypothesisRow",
    "TherapyRow",
    "OutreachRow",
    "QuestionRow",
    "collect_sections",
    "render_pdf",
]


if __name__ == "__main__":
    sys.exit(main())
