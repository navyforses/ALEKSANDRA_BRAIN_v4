"""
outreach_drafter.py — Phase 3 CGM-04 + CGM-09 outreach draft pipeline.

Drafts emails to researchers / clinicians via the Gmail API. The OAuth
scope is locked to `gmail.compose` only — this module CANNOT send mail.
Send action stays manual via the Gmail UI for months 1–6 (per the
2026-05-16 owner-locked decision).

Hard caps:
  - Maximum 5 approved outbound drafts per UTC day (CGM-09)
  - Every persisted row requires phi_redacted=true (CHECK constraint
    in migration 008)
  - Every draft body must pass banned_phrases.check() and the redactor

Lifecycle for a single outreach:

    1. Caller passes (contact_id, query, purpose, language).
    2. We pull consent flags from contacts.
    3. summarize() produces a source-grounded SummaryDraft.
    4. The SummaryDraft must be persistable() — else we return blocked.
    5. We render subject + body in the recipient's language.
    6. Daily cap check (queries outreach_log unless `today_draft_count`
       passed by tests) — returns blocked when count >= MAX_DAILY_DRAFTS.
    7. Gmail API creates a draft (compose-only scope).
    8. We insert outreach_log row with phi_redacted=true, gmail_draft_id
       set, sent_at NULL.

`dry_run=True` runs every step except the live Gmail call and the DB
insert — used by the verifier and by Manager-side sanity checks.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import psycopg2

from scripts.communicator.phi_redactor import (
    ConsentFlags,
    RedactionResult,
    load_consent_flags,
    redact,
)
from scripts.communicator.summarize import SummaryDraft, generate_summary
from scripts.ledger import load_env


# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------
MAX_DAILY_DRAFTS = 5

# Gmail OAuth scope is intentionally narrow. The MUST-NOT list:
#   - gmail.send         (would let us send)
#   - gmail.modify       (would let us mark/delete)
#   - gmail.readonly     (overbroad inbox read)
GMAIL_SCOPES = ("https://www.googleapis.com/auth/gmail.compose",)

# Gmail OAuth artifact paths — referenced by docs/RUNBOOK-gmail-api.md
GMAIL_CREDENTIALS_PATH = os.environ.get(
    "GMAIL_OAUTH_CREDENTIALS_PATH", ".secrets/gmail_oauth_credentials.json"
)
GMAIL_TOKEN_PATH = os.environ.get(
    "GMAIL_OAUTH_TOKEN_PATH", ".secrets/gmail_oauth_token.json"
)


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------
@dataclass
class OutreachDraft:
    contact_id: str
    purpose: str
    language: str
    subject: str
    body: str
    summary: SummaryDraft | None = None
    redaction: RedactionResult | None = None
    evidence_refs: list[str] = field(default_factory=list)
    confidence: float = 0.0
    blocked: bool = False
    block_reason: str | None = None
    gmail_draft_id: str | None = None  # set after Gmail API success
    outreach_log_id: str | None = None  # set after DB insert
    originating_run_id: str | None = None  # OBS-02: runs.id that produced this draft
    dry_run: bool = False
    drafted_at: str = ""


# ---------------------------------------------------------------------------
# Daily cap query
# ---------------------------------------------------------------------------
def count_drafts_today(now: datetime | None = None) -> int:
    """Return today's UTC-day outreach_log row count. Fail closed on DB error."""
    if now is None:
        now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    try:
        load_env()
        conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM outreach_log WHERE drafted_at >= %s",
                    (today_start,),
                )
                row = cur.fetchone()
                return int(row[0]) if row else 0
        finally:
            conn.close()
    except Exception:
        return MAX_DAILY_DRAFTS


# ---------------------------------------------------------------------------
# Subject + body rendering
# ---------------------------------------------------------------------------
_SUBJECT_TEMPLATES = {
    "question": "Question about HIE research context",
    "follow_up": "Following up on our prior conversation",
    "update": "Brief update on our family's research path",
    "intro": "Introduction — family research project",
    "thanks": "Thank you",
}


def _render_subject(purpose: str, language: str) -> str:
    base = _SUBJECT_TEMPLATES.get(purpose, _SUBJECT_TEMPLATES["question"])
    return base


def _render_body(summary: SummaryDraft, purpose: str, language: str) -> str:
    """Compose a plain-text email body from the SummaryDraft.

    We never embed PHI directly. The body is built from summary.redacted_text
    (which has run through phi_redactor) plus a citation appendix at the end.
    """
    intro = {
        "question": "I am reaching out about a research question related to severe neonatal HIE.",
        "follow_up": "Following up on the conversation referenced below.",
        "update": "A short update from the family's research workflow.",
        "intro": "Brief introduction — I run a research-discovery workflow for an infant with severe HIE.",
        "thanks": "A short note of thanks.",
    }.get(purpose, "Brief research note.")

    body_lines: list[str] = [intro, ""]
    for c in summary.claims:
        body_lines.append(f"- {c.sentence}")
    body_lines.append("")
    body_lines.append("Sources referenced:")
    for cid in summary.citations:
        body_lines.append(f"  • {cid}")
    body_lines.append("")
    body_lines.append(
        "This message is research context, not a clinical request. "
        "Every claim above carries a source for verification."
    )
    return "\n".join(body_lines)


# ---------------------------------------------------------------------------
# Gmail draft I/O — only loaded when really sending to Gmail
# ---------------------------------------------------------------------------
def _gmail_service() -> Any:
    """Construct an authorised Gmail service.

    Raises FileNotFoundError if the OAuth artifacts haven't been provisioned
    yet — see docs/RUNBOOK-gmail-api.md for the one-time setup.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds: Credentials | None = None
    if os.path.exists(GMAIL_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH, GMAIL_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(GMAIL_CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"Gmail OAuth credentials missing at {GMAIL_CREDENTIALS_PATH}. "
                    "Run the OAuth bootstrap per docs/RUNBOOK-gmail-api.md."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                GMAIL_CREDENTIALS_PATH, list(GMAIL_SCOPES)
            )
            creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(GMAIL_TOKEN_PATH) or ".", exist_ok=True)
        with open(GMAIL_TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _gmail_create_draft(to_email: str, subject: str, body: str) -> str:
    """Create a Gmail draft for the authenticated user. Returns the draft ID."""
    service = _gmail_service()
    msg = EmailMessage()
    msg.set_content(body)
    msg["To"] = to_email
    msg["Subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    draft = (
        service.users()
        .drafts()
        .create(userId="me", body={"message": {"raw": raw}})
        .execute()
    )
    return draft["id"]


def _gmail_create_draft_with_attachment(
    to_email: str,
    subject: str,
    body: str,
    attachment_path: Path,
    attachment_filename: str | None = None,
) -> str:
    """Create a Gmail draft with one PDF attached. Returns the draft ID.

    Uses the same gmail.compose scope as the plain-text draft path — adding
    an attachment does not require gmail.send or any broader capability.
    """
    service = _gmail_service()
    msg = EmailMessage()
    msg.set_content(body)
    msg["To"] = to_email
    msg["Subject"] = subject

    pdf_bytes = attachment_path.read_bytes()
    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=attachment_filename or attachment_path.name,
    )

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    draft = (
        service.users()
        .drafts()
        .create(userId="me", body={"message": {"raw": raw}})
        .execute()
    )
    return draft["id"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def draft_outreach(
    contact_id: str,
    query: str,
    *,
    purpose: str = "question",
    language: str = "en",
    consent: ConsentFlags | None = None,
    today_draft_count: int | None = None,
    dry_run: bool = False,
) -> OutreachDraft:
    """Build a Phase 3 outreach draft, optionally stage it in Gmail.

    Caller responsibilities:
      - contact_id must exist in contacts (FK enforces).
      - Manager must manually click Send in Gmail UI (months 1–6 policy).

    `today_draft_count` lets tests pass in a known count to avoid hitting
    outreach_log; production callers leave it None.
    """
    # 1. Daily cap check — earliest gate (cheap)
    count = today_draft_count if today_draft_count is not None else count_drafts_today()
    if count >= MAX_DAILY_DRAFTS:
        return OutreachDraft(
            contact_id=contact_id,
            purpose=purpose,
            language=language,
            subject="",
            body="",
            blocked=True,
            block_reason=f"daily_cap_reached({count}/{MAX_DAILY_DRAFTS})",
            dry_run=dry_run,
            drafted_at=datetime.now(timezone.utc).isoformat(),
        )

    # 2. Consent flags
    if consent is None:
        consent = load_consent_flags(contact_id)

    # 3. Summarize evidence
    summary = generate_summary(
        query, audience="researcher", language=language, consent=consent
    )

    if not summary.persistable():
        return OutreachDraft(
            contact_id=contact_id,
            purpose=purpose,
            language=language,
            subject="",
            body="",
            summary=summary,
            blocked=True,
            block_reason="summary_not_persistable",
            dry_run=dry_run,
            drafted_at=datetime.now(timezone.utc).isoformat(),
        )

    # 4. Render
    subject = _render_subject(purpose, language)
    body = _render_body(summary, purpose, language)

    # 5. Final redaction safety net — the body should already be clean, but
    # re-running with the recipient's consent guarantees nothing slipped in.
    final_redaction = redact(body, consent=consent)
    if final_redaction.blocked:
        return OutreachDraft(
            contact_id=contact_id,
            purpose=purpose,
            language=language,
            subject=subject,
            body=body,
            summary=summary,
            redaction=final_redaction,
            blocked=True,
            block_reason=f"final_redaction_blocked: {final_redaction.block_reason}",
            dry_run=dry_run,
            drafted_at=datetime.now(timezone.utc).isoformat(),
        )
    body = final_redaction.text

    draft = OutreachDraft(
        contact_id=contact_id,
        purpose=purpose,
        language=language,
        subject=subject,
        body=body,
        summary=summary,
        redaction=final_redaction,
        evidence_refs=summary.citations,
        confidence=summary.confidence,
        dry_run=dry_run,
        drafted_at=datetime.now(timezone.utc).isoformat(),
    )

    if dry_run:
        return draft

    # 6. Live path: create Gmail draft + insert outreach_log row
    to_email = _lookup_contact_email(contact_id)
    if not to_email:
        draft.blocked = True
        draft.block_reason = "contact_missing_email"
        return draft

    draft.gmail_draft_id = _gmail_create_draft(to_email, subject, body)
    draft.outreach_log_id = _insert_outreach_log(draft)
    return draft


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def _lookup_contact_email(contact_id: str) -> str | None:
    load_env()
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT email FROM contacts WHERE id = %s", (contact_id,))
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


def _insert_outreach_log(draft: OutreachDraft) -> str:
    """Persist an outreach_log row. Returns the new id (UUID string).

    Migration 010 / OBS-02: writes `originating_run_id` from
    `draft.originating_run_id`. Callers that produced the draft from
    an agent run set this; legacy / fixture paths leave it None and
    the column stays NULL (column is nullable, so this is safe).
    """
    load_env()
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
                  %s, %s, %s, %s,
                  %s, %s, %s,
                  TRUE, %s, %s,
                  NOW(), %s
                )
                RETURNING id
                """,
                (
                    draft.contact_id,
                    draft.subject,
                    draft.body,
                    draft.language,
                    draft.purpose,
                    draft.evidence_refs,
                    draft.confidence,
                    len(draft.redaction.redactions) if draft.redaction else 0,
                    draft.gmail_draft_id,
                    draft.originating_run_id,
                ),
            )
            new_id = cur.fetchone()[0]
            cur.execute(
                """
                UPDATE contacts
                SET last_contacted_at = NOW(),
                    outreach_count = COALESCE(outreach_count, 0) + 1,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (draft.contact_id,),
            )
        conn.commit()
        return str(new_id)
    finally:
        conn.close()


def draft_clinician_outreach(
    contact_id: str,
    topic: str,
    *,
    audience_label: str,
    claims: list,
    citation_metadata: dict[str, dict] | None = None,
    agent_run_ids: list[str] | None = None,
    consent: ConsentFlags | None = None,
    today_draft_count: int | None = None,
    dry_run: bool = False,
    output_dir: Path | None = None,
) -> OutreachDraft:
    """Phase 4 ACD-05 — render clinician PDF and stage Gmail draft with attachment.

    Pipeline:
      1. Daily cap check (uses outreach_log row count; fails closed on DB error).
      2. Consent lookup for the recipient contact.
      3. Patient context snapshot (versioned).
      4. PDF render via clinician_pdf.render_clinician_pdf().
      5. Optional R2 upload (only when caller passes the artifact path through;
         the upload itself is a Manager-side action so we keep it out of this
         function to avoid blocking the smoke test on R2 connectivity).
      6. Gmail draft with PDF attachment via the gmail.compose scope.
      7. outreach_log row insert with trigger_kind='clinician_pdf' and
         phi_redacted=TRUE.

    Manual-send-only: the draft is staged in Gmail Drafts. Shako reviews
    and clicks Send. The PDF lives on disk (or R2 if Manager uploads).
    """
    from scripts.communicator.clinician_pdf import (
        ClinicianClaim,
        ClinicianPDFInput,
        render_clinician_pdf,
    )
    from scripts.communicator.patient_context import current_context

    count = today_draft_count if today_draft_count is not None else count_drafts_today()
    if count >= MAX_DAILY_DRAFTS:
        return OutreachDraft(
            contact_id=contact_id,
            purpose="clinician_pdf",
            language="en",
            subject="",
            body="",
            blocked=True,
            block_reason=f"daily_cap_reached({count}/{MAX_DAILY_DRAFTS})",
            dry_run=dry_run,
            drafted_at=datetime.now(timezone.utc).isoformat(),
        )

    if consent is None:
        consent = load_consent_flags(contact_id) if not dry_run else ConsentFlags()

    ctx = current_context()

    # Coerce caller's claim list into ClinicianClaim records
    coerced_claims: list[ClinicianClaim] = []
    for raw in claims or []:
        if isinstance(raw, ClinicianClaim):
            coerced_claims.append(raw)
            continue
        coerced_claims.append(
            ClinicianClaim(
                sentence=str(raw.get("sentence", "")).strip(),
                citation_ids=list(raw.get("citation_ids") or []),
                evidence_grade=int(raw.get("evidence_grade", 5)),
                confidence=float(raw.get("confidence", 0.0)),
            )
        )

    out_dir = output_dir or (Path("briefs") / "clinician")
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / (
        f"clinician_{ctx.version_hash}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.pdf"
    )

    pdf_inp = ClinicianPDFInput(
        topic=topic,
        audience_label=audience_label,
        claims=coerced_claims,
        citation_metadata=citation_metadata or {},
        agent_run_ids=agent_run_ids or [],
    )
    pdf_out = render_clinician_pdf(
        pdf_inp,
        pdf_path,
        consent=consent,
        context=ctx,
    )
    if pdf_out.blocked:
        return OutreachDraft(
            contact_id=contact_id,
            purpose="clinician_pdf",
            language="en",
            subject=f"Clinician brief — {topic[:60]}",
            body="",
            blocked=True,
            block_reason=f"pdf_blocked: {pdf_out.block_reason}",
            dry_run=dry_run,
            drafted_at=datetime.now(timezone.utc).isoformat(),
        )

    body = (
        f"Hello,\n\n"
        f"Attached is a clinician-shareable brief on {topic}. The brief is "
        f"research-discovery material for your review, not a clinical "
        f"recommendation. Every claim cites a source the recipient can "
        f"verify independently. Patient context version: {pdf_out.patient_context_version}.\n\n"
        f"Best,\nShako (sent on behalf of A.J.'s family)"
    )
    subject = f"Clinician brief — {topic[:60]}"

    citations: list[str] = sorted(
        {cid for claim in coerced_claims for cid in claim.citation_ids}
    )
    confidence = (
        round(
            sum(c.confidence for c in coerced_claims) / len(coerced_claims),
            4,
        )
        if coerced_claims
        else 0.0
    )

    draft = OutreachDraft(
        contact_id=contact_id,
        purpose="clinician_pdf",
        language="en",
        subject=subject,
        body=body,
        evidence_refs=citations,
        confidence=confidence,
        dry_run=dry_run,
        drafted_at=datetime.now(timezone.utc).isoformat(),
    )

    if dry_run:
        return draft

    to_email = _lookup_contact_email(contact_id)
    if not to_email:
        draft.blocked = True
        draft.block_reason = "contact_missing_email"
        return draft

    draft.gmail_draft_id = _gmail_create_draft_with_attachment(
        to_email, subject, body, pdf_path
    )
    draft.outreach_log_id = _insert_outreach_log(draft)
    return draft


__all__ = [
    "OutreachDraft",
    "draft_outreach",
    "draft_clinician_outreach",
    "count_drafts_today",
    "MAX_DAILY_DRAFTS",
    "GMAIL_SCOPES",
]
