"""
email_draft.py — Phase 5 Day 6 "write to X about Y" orchestrator.

Operator intent
---------------
"write to Sydney about Duke timing"
  -> parse  ->  recipient_hint="Sydney", topic="Duke timing"
  -> fuzzy match against contacts.full_name (>= 0.6)
  -> delegate to scripts.communicator.outreach_drafter.draft_outreach
     which renders the body, redacts, creates the Gmail draft (compose
     scope only — NEVER auto-sent), and inserts an outreach_log row.

Trust posture
-------------
- Gmail scope is compose-only (Phase 3 invariant). The drafter creates
  a Drafts entry; Shako manually clicks Send in Gmail UI.
- Daily cap of 5 drafts is inherited from MAX_DAILY_DRAFTS.
- PHI redactor runs inside draft_outreach as the last gate before the
  body becomes a Drafts entry.
- Banned-phrase detector inside the redactor blocks 'you should',
  'we recommend' etc.

Public surface
--------------
    parse_intent(text) -> EmailIntent | None
    draft_from_intent(text, *, dry_run=False) -> EmailDraftResult
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg2

from scripts.communicator.outreach_drafter import (
    MAX_DAILY_DRAFTS,
    OutreachDraft,
    count_drafts_today,
    draft_outreach,
)
from scripts.ledger import load_env
from scripts.manager.routing._shared import fuzzy_best_match


# Match "write/draft/email to <NAME> about <TOPIC>" — case-insensitive.
# NAME accepts letters + space + hyphen + apostrophe + period (for "Dr.").
_INTENT_PATTERNS = [
    re.compile(
        r"\b(?:write|draft|email|message)\s+(?:an?\s+email\s+)?to\s+"
        r"(?P<who>[A-Z][A-Za-z\-'.\s]{1,40}?)\s+about\s+(?:the\s+)?(?P<topic>.+)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:to|@)\s+(?P<who>[A-Z][A-Za-z\-'.\s]{1,40}?)\s*[:\-]\s*(?P<topic>.+)$",
        re.IGNORECASE,
    ),
]


@dataclass
class EmailIntent:
    recipient_hint: str
    topic: str


@dataclass
class EmailDraftResult:
    matched: bool
    intent: EmailIntent | None
    contact_id: str | None
    contact_name: str | None
    fuzzy_score: float | None
    draft: OutreachDraft | None
    blocked: bool
    block_reason: str | None
    dry_run: bool
    created_at: str


def parse_intent(text: str) -> EmailIntent | None:
    """Extract recipient + topic from operator-typed intent. None if no match."""
    s = text.strip().rstrip(".")
    for pat in _INTENT_PATTERNS:
        m = pat.search(s)
        if m:
            who = m.group("who").strip(" -,:")
            topic = m.group("topic").strip(" -,:.")
            if who and topic:
                return EmailIntent(recipient_hint=who, topic=topic)
    return None


def _open():
    load_env()
    return psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")


def _candidate_contacts(
    cur: psycopg2.extensions.cursor,
) -> list[tuple[str, str, list[str]]]:
    """Pull every contact's id + full_name + (short_name, email) as aliases."""
    cur.execute(
        "SELECT id, COALESCE(full_name,''), "
        "COALESCE(short_name,''), COALESCE(email,'') FROM contacts"
    )
    out: list[tuple[str, str, list[str]]] = []
    for cid, full, short, email in cur.fetchall():
        aliases = [a for a in (short, email) if a]
        out.append((str(cid), full, aliases))
    return out


def draft_from_intent(text: str, *, dry_run: bool = False) -> EmailDraftResult:
    """Top-to-bottom: parse intent, resolve contact, delegate to drafter."""
    intent = parse_intent(text)
    now_iso = datetime.now(timezone.utc).isoformat()
    if intent is None:
        return EmailDraftResult(
            matched=False,
            intent=None,
            contact_id=None,
            contact_name=None,
            fuzzy_score=None,
            draft=None,
            blocked=True,
            block_reason="intent_not_recognized",
            dry_run=dry_run,
            created_at=now_iso,
        )

    # Daily cap check up-front so the operator gets a clear failure
    # instead of a flaky drafter-blocked return.
    if not dry_run and count_drafts_today() >= MAX_DAILY_DRAFTS:
        return EmailDraftResult(
            matched=True,
            intent=intent,
            contact_id=None,
            contact_name=None,
            fuzzy_score=None,
            draft=None,
            blocked=True,
            block_reason=f"daily_cap_reached({MAX_DAILY_DRAFTS}/{MAX_DAILY_DRAFTS})",
            dry_run=dry_run,
            created_at=now_iso,
        )

    conn = _open()
    try:
        with conn.cursor() as cur:
            candidates = _candidate_contacts(cur)
    finally:
        conn.close()

    hit = fuzzy_best_match(intent.recipient_hint, candidates, threshold=0.6)
    if hit is None:
        return EmailDraftResult(
            matched=True,
            intent=intent,
            contact_id=None,
            contact_name=None,
            fuzzy_score=None,
            draft=None,
            blocked=True,
            block_reason=f"no_contact_match_for_{intent.recipient_hint!r}",
            dry_run=dry_run,
            created_at=now_iso,
        )
    contact_id, score = hit
    contact_name = next(
        (full for cid, full, _ in candidates if cid == contact_id), None
    )

    draft = draft_outreach(
        contact_id=contact_id,
        query=intent.topic,
        purpose="question",
        language="en",
        dry_run=dry_run,
    )
    return EmailDraftResult(
        matched=True,
        intent=intent,
        contact_id=contact_id,
        contact_name=contact_name,
        fuzzy_score=score,
        draft=draft,
        blocked=bool(draft.blocked),
        block_reason=draft.block_reason,
        dry_run=dry_run,
        created_at=now_iso,
    )


__all__ = ["parse_intent", "draft_from_intent", "EmailIntent", "EmailDraftResult"]
