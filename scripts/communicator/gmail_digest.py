"""
gmail_digest.py — Phase 4 ACD-03 weekly Gmail digest renderer.

Produces a plain-text Gmail body that mirrors the Sunday Weekly Brief PDF
in a text-only form Shako (or anyone else cc'd) can read in their inbox
without opening the attached PDF. The Gmail draft is the redundancy
channel — Telegram remains primary.

Recipient:
  - `FAMILY_GMAIL_ADDRESS` env var (the family's own Gmail), or falls back
    to whatever account is authenticated for `gmail.compose` (self-send
    via the OAuth-authorised account).

Cadence:
  - Sunday 09:00 ET (13:00 UTC). Same cron that fires the Weekly Brief
    PDF; the digest step runs after the PDF + R2 upload.

Send mode:
  - Months 1–6: staged as Gmail draft (compose scope). Shako reviews and
    sends. Per the 2026-05-16 owner-locked decision, family-internal
    Gmail digest may auto-send from day 1, but we keep the manual gate in
    until month 7 for conservatism. Toggle via `gmail_digest_auto_send`
    flag in `data/patient_context.yaml` once Shako wants it.

Idempotency:
  - One outreach_log row per (week_start, trigger_kind='weekly_digest').
    Re-running on the same week returns the existing draft id.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import psycopg2

from scripts.communicator._bilingual_read import display_field_py
from scripts.communicator.outreach_drafter import (
    GMAIL_SCOPES,
    MAX_DAILY_DRAFTS,
    _gmail_create_draft,
    _gmail_create_draft_with_attachment,
    count_drafts_today,
)
from scripts.communicator.phi_redactor import ConsentFlags, redact
from scripts.communicator.weekly_brief import BriefSections, collect_sections
from scripts.ledger import load_env


# Phase 6 Plan 06-12 / D-02 — Gmail audience is operational/clinician-facing,
# English-only. Every read of a migration-012-converted JSONB column (or
# briefs.sections nested bilingual field) must be resolved through
# display_field_py(field, 'en').
GMAIL_LOCALE = "en"


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------
@dataclass
class WeeklyDigestResult:
    week_start: date
    subject: str
    body: str
    recipient: str
    gmail_draft_id: str | None = None
    outreach_log_id: str | None = None
    blocked: bool = False
    block_reason: str | None = None
    dry_run: bool = False
    rendered_at: str = ""


# ---------------------------------------------------------------------------
# Recipient resolution
# ---------------------------------------------------------------------------
def _family_recipient() -> str:
    """Resolve the family Gmail address to send the digest to."""
    explicit = os.environ.get("FAMILY_GMAIL_ADDRESS", "").strip()
    if explicit:
        return explicit
    # Fallback — the OAuth-authorised account is the operator's own Gmail.
    # We avoid hard-coding an address here; the operator can set
    # FAMILY_GMAIL_ADDRESS explicitly when ready.
    return ""


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def render_subject(week_start: date) -> str:
    return f"ALEKSANDRA_BRAIN Weekly Brief — week of {week_start.isoformat()}"


def render_body(
    sections: BriefSections,
    *,
    pdf_r2_path: str | None = None,
    notion_database_id: str | None = None,
) -> str:
    """Plain-text body that mirrors the brief's headline sections.

    Telegram is the primary push; this email is the redundancy channel.
    Layout intentionally short so it reads in an inbox preview:

      1. Header (week range)
      2. This week, in short — auto-counted summary
      3. Headline finding per section (≤3 items)
      4. Citation appendix
      5. Footer disclaimer
    """
    lines: list[str] = []
    lines.append("ALEKSANDRA_BRAIN — Weekly Brief")
    lines.append(
        f"Week of {sections.week_start.isoformat()} – {sections.week_end.isoformat()}"
    )
    lines.append(f"Generated {sections.generated_at.isoformat(timespec='seconds')}")
    lines.append("")

    lines.append("This week, in short:")
    if sections.summary_lines:
        for line in sections.summary_lines[:6]:
            # Phase 6 I18N-07: post-06-09, BriefSections.summary_lines is
            # list[dict[str, str]] ({en, ka}). Gmail audience reads .en.
            # display_field_py also tolerates legacy str rows (pre-migration
            # forward-compat) and None.
            lines.append(f"  • {display_field_py(line, GMAIL_LOCALE)}")
    else:
        lines.append("  • No new items this week.")
    lines.append("")

    def _section(title: str, items: list, render_item) -> None:
        lines.append(f"{title}:")
        if not items:
            lines.append("  • No new items this week.")
        else:
            for item in items[:3]:
                lines.append(f"  • {render_item(item)}")
        lines.append("")

    # Phase 6 I18N-07: BriefSections row fields (p.title, h.title, t.name,
    # o.subject, q.question) may be `str` (legacy) OR `{en, ka}` (post-06-09
    # _bilingual_mirror / post-migration-012). Gmail audience routes every read
    # through display_field_py(field, GMAIL_LOCALE) so the English half is
    # what the inbox sees.
    _section(
        "New evidence",
        sections.papers,
        lambda p: (
            f"{display_field_py(p.title, GMAIL_LOCALE)} [{p.citation_id}, "
            f"relevance={p.relevance_score if p.relevance_score is not None else 'n/a'}]"
        ),
    )
    _section(
        "Hypothesis updates",
        sections.hypotheses,
        lambda h: (
            f"{display_field_py(h.title, GMAIL_LOCALE)} — "
            f"status={h.status}, confidence={h.confidence or 'n/a'}"
        ),
    )
    _section(
        "Repurposing watch",
        sections.therapies,
        lambda t: (
            f"{display_field_py(t.name, GMAIL_LOCALE)} — "
            f"{t.aleksandra_status or 'n/a'} / HIE evidence {t.evidence_in_hie or 'n/a'}"
        ),
    )
    _section(
        "Outreach queue",
        sections.outreach,
        lambda o: (
            f"[{o.contact_label}] {display_field_py(o.subject, GMAIL_LOCALE)} "
            f"({'sent' if o.sent_at else 'pending review'})"
        ),
    )
    _section(
        "Open family questions",
        sections.questions,
        lambda q: display_field_py(q.question, GMAIL_LOCALE),
    )

    if pdf_r2_path:
        lines.append(f"Full PDF: {pdf_r2_path}")
    if notion_database_id:
        lines.append(f"Notion archive: notion.so/{notion_database_id.replace('-', '')}")
    lines.append("")

    if sections.citations:
        lines.append("Citation appendix:")
        for cid in sections.citations[:20]:
            lines.append(f"  • {cid}")
        if len(sections.citations) > 20:
            lines.append(f"  • … and {len(sections.citations) - 20} more")
        lines.append("")

    lines.append(
        "ALEKSANDRA_BRAIN is a research-discovery system, not a clinician. "
        "Every claim above carries a source for verification. "
        "Clinical decisions remain with Aleksandra's doctors."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def _find_existing_weekly_digest(week_start: date) -> str | None:
    """Return outreach_log.id for an existing digest for `week_start`, or None.

    Idempotency: weekly digest is keyed by (trigger_kind='weekly_digest',
    drafted_at::date matches week_start). Re-running on the same week
    returns the existing draft id.
    """
    load_env()
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM outreach_log
                WHERE trigger_kind = 'weekly_digest'
                  AND drafted_at::date = %s
                ORDER BY drafted_at DESC
                LIMIT 1
                """,
                (week_start,),
            )
            row = cur.fetchone()
            return str(row[0]) if row else None
    finally:
        conn.close()


def _insert_weekly_digest_row(
    *,
    subject: str,
    body: str,
    citations: list[str],
    gmail_draft_id: str | None,
    redactions_count: int,
    originating_run_id: str | None = None,
) -> str:
    """Persist outreach_log row for the weekly digest.

    Uses contact_id = NULL semantics by inserting against a system
    "family-self" contact.

    Migration 010 / OBS-02: `originating_run_id` links back to the
    runs row that produced the weekly_brief render. Callers pass
    `weekly_brief_run_id` when known; None on legacy / fixture paths.
    """
    load_env()
    family_contact_id = os.environ.get("FAMILY_CONTACT_ID", "").strip()
    if not family_contact_id:
        raise RuntimeError(
            "FAMILY_CONTACT_ID env var missing — set it to the contacts.id row "
            "that represents the family's own Gmail recipient. The contacts row "
            "should have consent_full_name=TRUE so the digest is delivered "
            "without identity redaction (it's going to Shako himself)."
        )
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO outreach_log (
                  contact_id, subject, body, language,
                  trigger_kind, evidence_refs, confidence,
                  phi_redacted, phi_redactions_count, gmail_draft_id,
                  drafted_at, originating_run_id
                ) VALUES (
                  %s, %s, %s, 'en',
                  'weekly_digest', %s, NULL,
                  TRUE, %s, %s,
                  NOW(), %s
                )
                RETURNING id
                """,
                (
                    family_contact_id,
                    subject,
                    body,
                    citations,
                    redactions_count,
                    gmail_draft_id,
                    originating_run_id,
                ),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return str(new_id)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def stage_weekly_digest(
    *,
    week_start: date | None = None,
    pdf_r2_path: str | None = None,
    notion_database_id: str | None = None,
    pdf_attachment_path: Path | None = None,
    dry_run: bool = False,
    fixture: bool = False,
) -> WeeklyDigestResult:
    """Render the weekly Gmail digest body and stage a Gmail draft.

    Pipeline:
      1. Idempotency check — return existing draft if this week was already staged
      2. Daily cap check (uses outreach_log row count; fails closed)
      3. Resolve recipient (FAMILY_GMAIL_ADDRESS or OAuth-authed self)
      4. Collect BriefSections via weekly_brief.collect_sections()
      5. Render subject + body
      6. Final phi_redactor pass over the joined body (safety net)
      7. Gmail draft (compose scope) — with PDF attachment if path supplied
      8. outreach_log row insert with trigger_kind='weekly_digest'

    dry_run=True does everything except the Gmail API and DB insert.
    fixture=True uses BriefSections fixture data (FFV-03 verifier path).
    """
    if week_start is None:
        today = date.today()
        days_since_sunday = (today.weekday() + 1) % 7
        week_start = today - timedelta(days=days_since_sunday)

    rendered_at = datetime.now(timezone.utc).isoformat()

    # 1. Idempotency check — skip in dry_run
    if not dry_run:
        existing = _find_existing_weekly_digest(week_start)
        if existing:
            return WeeklyDigestResult(
                week_start=week_start,
                subject=render_subject(week_start),
                body="",
                recipient=_family_recipient(),
                outreach_log_id=existing,
                rendered_at=rendered_at,
                blocked=True,
                block_reason="already_staged_for_this_week",
            )

    # 2. Daily cap check
    if not dry_run:
        count = count_drafts_today()
        if count >= MAX_DAILY_DRAFTS:
            return WeeklyDigestResult(
                week_start=week_start,
                subject=render_subject(week_start),
                body="",
                recipient=_family_recipient(),
                blocked=True,
                block_reason=f"daily_cap_reached({count}/{MAX_DAILY_DRAFTS})",
                rendered_at=rendered_at,
            )

    # 3. Recipient
    recipient = _family_recipient()

    # 4. Sections
    sections = collect_sections(week_start, fixture=fixture)

    # 5. Subject + body
    subject = render_subject(week_start)
    body = render_body(
        sections,
        pdf_r2_path=pdf_r2_path,
        notion_database_id=notion_database_id,
    )

    # 6. PHI safety-net pass
    safety = redact(body, consent=ConsentFlags())
    if safety.blocked:
        return WeeklyDigestResult(
            week_start=week_start,
            subject=subject,
            body=body,
            recipient=recipient,
            blocked=True,
            block_reason=f"phi_safety_blocked: {safety.block_reason}",
            dry_run=dry_run,
            rendered_at=rendered_at,
        )
    redacted_body = safety.text
    redactions_count = len(safety.redactions)

    if dry_run:
        return WeeklyDigestResult(
            week_start=week_start,
            subject=subject,
            body=redacted_body,
            recipient=recipient,
            dry_run=True,
            rendered_at=rendered_at,
        )

    if not recipient:
        return WeeklyDigestResult(
            week_start=week_start,
            subject=subject,
            body=redacted_body,
            recipient="",
            blocked=True,
            block_reason="recipient_unresolved: set FAMILY_GMAIL_ADDRESS in .env",
            rendered_at=rendered_at,
        )

    # 7. Gmail draft
    if pdf_attachment_path is not None and pdf_attachment_path.exists():
        draft_id = _gmail_create_draft_with_attachment(
            recipient,
            subject,
            redacted_body,
            pdf_attachment_path,
        )
    else:
        draft_id = _gmail_create_draft(recipient, subject, redacted_body)

    # 8. outreach_log row
    citations = list(sections.citations)[:20]
    log_id = _insert_weekly_digest_row(
        subject=subject,
        body=redacted_body,
        citations=citations,
        gmail_draft_id=draft_id,
        redactions_count=redactions_count,
    )

    return WeeklyDigestResult(
        week_start=week_start,
        subject=subject,
        body=redacted_body,
        recipient=recipient,
        gmail_draft_id=draft_id,
        outreach_log_id=log_id,
        rendered_at=rendered_at,
    )


def _bilingual_dryrun_sections() -> BriefSections:
    """Fixture BriefSections with bilingual JSONB-shaped fields.

    Used by --bilingual-dryrun (which check_i18n_07 reads to assert ZERO
    Mkhedruli codepoints appear in the Gmail-side output — Gmail audience
    is English-only per CONTEXT.md D-02).
    """
    from scripts.communicator.weekly_brief import (  # noqa: PLC0415
        HypothesisRow,
        OutreachRow,
        PaperRow,
        QuestionRow,
        TherapyRow,
    )

    today = date.today()
    return BriefSections(
        week_start=today,
        week_end=today + timedelta(days=6),
        generated_at=datetime.now(timezone.utc),
        summary_lines=[
            {
                "en": "3 new relevant papers this week.",
                "ka": "ამ კვირას 3 ახალი სტატია.",
            },
            {"en": "2 hypothesis updates.", "ka": "2 ჰიპოთეზის განახლება."},
        ],
        papers=[
            PaperRow(
                title={  # type: ignore[arg-type]
                    "en": "Vigabatrin washout in infant HIE",
                    "ka": "ვიგაბატრინის გამორეცხვა ჩვილებში HIE-ით",
                },
                citation_id="PMID:00000000",
                ingested_at=today.isoformat(),
                relevance_score=0.91,
            ),
        ],
        hypotheses=[
            HypothesisRow(
                title={  # type: ignore[arg-type]
                    "en": "Cord blood window aligns with Duke EAP",
                    "ka": "სანაყოფე სისხლის ფანჯარა ემთხვევა Duke EAP-ს",
                },
                status="evaluating",
                confidence="medium",
                reviewed_at=today.isoformat(),
                supporting=[],
            ),
        ],
        therapies=[
            TherapyRow(
                name={  # type: ignore[arg-type]
                    "en": "Vigabatrin",
                    "ka": "ვიგაბატრინი",
                },
                therapy_type="anticonvulsant",
                aleksandra_status="evaluating",
                evidence_in_hie="moderate",
            ),
        ],
        outreach=[
            OutreachRow(
                subject={  # type: ignore[arg-type]
                    "en": "Cord blood EAP follow-up",
                    "ka": "სანაყოფე სისხლის EAP-ის შემდგომი ნაბიჯი",
                },
                language="en",
                drafted_at=today.isoformat(),
                sent_at=None,
                contact_label="Duke DTRI",
                confidence=0.8,
            ),
        ],
        questions=[
            QuestionRow(
                id="q-001",
                question={  # type: ignore[arg-type]
                    "en": "When does vigabatrin washout complete?",
                    "ka": "როდის სრულდება ვიგაბატრინის გამორეცხვა?",
                },
                context="treatment-timeline",
                asked_at=today.isoformat(),
                status="open",
            ),
        ],
        citations=["PMID:00000000"],
    )


def _bilingual_dryrun() -> int:
    """Print a Gmail body composed via display_field_py(..., 'en'). Exit 0.

    Verifier check_i18n_07 reads stdout and asserts ZERO Mkhedruli codepoints
    (U+10A0..U+10FF) — Gmail audience is English-only per CONTEXT.md D-02.
    """
    sections = _bilingual_dryrun_sections()
    body = render_body(sections)
    print(body)
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse  # noqa: PLC0415

    parser = argparse.ArgumentParser(
        prog="scripts.communicator.gmail_digest",
        description="Phase 4 weekly Gmail digest + Phase 6 bilingual dry-run.",
    )
    parser.add_argument(
        "--bilingual-dryrun",
        action="store_true",
        help=(
            "Phase 6 I18N-07: render a Gmail body from JSONB-shaped fixture "
            "sections via display_field_py(..., 'en'). Prints body to stdout, "
            "exit 0, no Gmail API call, no DB write. Verifier check_i18n_07 "
            "asserts ZERO Mkhedruli codepoints appear (audience is English-only)."
        ),
    )
    args = parser.parse_args(argv)
    if args.bilingual_dryrun:
        return _bilingual_dryrun()
    parser.print_help()
    return 0


__all__ = [
    "WeeklyDigestResult",
    "render_subject",
    "render_body",
    "stage_weekly_digest",
    "GMAIL_SCOPES",
    "GMAIL_LOCALE",
]


if __name__ == "__main__":
    raise SystemExit(main())
