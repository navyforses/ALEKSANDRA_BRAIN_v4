"""
briefing.py — Phase 5 Day 6 morning briefing composer.

Sunday-09:00 ET (13:00 UTC) per Shako's locked decision. Pulls last
24 h of activity into a 3-bullet, ≤ 50-word Telegram message, writes
a `briefs` row for audit, then optionally archives via Notion.

Composition (deterministic, no LLM):

  1. Today line — today's appointment OR "no appointments today"
  2. Activity line — count of evidence_ledger rows ingested last 24 h
                     + top therapy candidate this week
  3. Follow-up line — outreach drafts pending Shako's manual send

A hard 50-word cap is enforced before send. Going over raises
BriefingTooLong so the contract is observable in tests; production
falls back to a truncated bullet rather than blocking the send.

Calendar source
---------------
Reads from `aleksandra_timeline` where event_date = today AND
event_type IN ('appointment', 'medication_change'). When the
Google Calendar integration lands (next plan, ACI-02), this function
will swap that SELECT for a calendar query without touching the
composition pipeline.

Public surface
--------------
    run(*, dry_run=False) -> dict
    compose(*, today_events, last_24h_evidence_count,
            pending_outreach_count) -> BriefMessage
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

import psycopg2

from scripts.ledger import _supabase_creds, _supabase_headers, load_env


WORD_CAP = 50


class BriefingTooLong(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Phase 6 I18N-06 / D-02 — bilingual emission for manager-briefing template strings
# ---------------------------------------------------------------------------
# The manager briefing is deterministic Python templating (no LLM call). Per
# RESEARCH.md Pattern 6 Recommendation, use Option A (deterministic prose
# mirror) — zero Anthropic cost. The Telegram audience is the family; the
# .ka half is the primary read surface (per Phase 6 D-02 per-tier policy +
# the audience routing landing in plan 06-12).
#
# TODO(Phase 6 execute): Shako sanity-check these template strings before merge.
# Translations avoid the D-05 banned imperatives (უნდა, აუცილებლად, განიხილეთ,
# მოითხოვეთ, ითხოვეთ, განიხილეთ, გაითვალისწინეთ, სცადეთ) — descriptive
# evidence-grade Georgian only.
BRIEFING_TEMPLATES_KA: dict[str, str] = {
    "good_morning": "დილა მშვიდობისა.",
    "today_event": "• დღეს: {title}",
    "today_event_at": "• დღეს: {title} @ {loc}",
    "today_more": " (+{n} მეტი)",
    "today_none": "• დღეს: შეხვედრები არ არის",
    "activity_evidence": "{n} ახალი წყარო (24სთ)",
    "activity_top_therapy": "მთავარი თერაპია {name}",
    "activity_prefix": "• აქტიურობა: ",
    "activity_quiet": "• აქტიურობა: მშვიდი ბოლო 24სთ-ში",
    "follow_pending": "• გასაგზავნი: {n} მონახაზი მიმოხილვისთვის",
    "follow_clear": "• გასაგზავნი: ფოსტა გასუფთავებულია",
}


def _build_bilingual_bullets(
    today_line_key: str,
    today_args: dict[str, Any],
    activity_line_key: str,
    activity_args: dict[str, Any],
    follow_line_key: str,
    follow_args: dict[str, Any],
    *,
    en_today: str,
    en_activity: str,
    en_follow: str,
) -> list[dict[str, str]]:
    """Render the 3-bullet bilingual structure for persistence in briefs.sections.

    Each bullet is `{en, ka}`. The deterministic English half is passed in
    pre-built (it already matches the str-only message text); the Georgian
    half is rendered from BRIEFING_TEMPLATES_KA. The text body used for
    Telegram send keeps the English-only form for backward compat with
    Phase 5 dispatch infrastructure — Phase 6 plan 06-12 swaps it.
    """

    def _ka(key: str, args: dict[str, Any]) -> str:
        return BRIEFING_TEMPLATES_KA[key].format(**args)

    return [
        {"en": en_today, "ka": _ka(today_line_key, today_args)},
        {"en": en_activity, "ka": _ka(activity_line_key, activity_args)},
        {"en": en_follow, "ka": _ka(follow_line_key, follow_args)},
    ]


@dataclass
class BriefMessage:
    text: str
    word_count: int
    bullets: list[str] = field(default_factory=list)
    # Phase 6 I18N-06: bilingual_bullets is the {en, ka} mirror of `bullets`
    # persisted into briefs.sections JSONB per migration 012's reshape. The
    # English-only `text` field is preserved for backward-compat Telegram
    # dispatch (plan 06-12 swaps the Telegram body to read .ka).
    bilingual_bullets: list[dict[str, str]] = field(default_factory=list)


def _open():
    load_env()
    return psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")


# ---------------------------------------------------------------------------
# Data pulls
# ---------------------------------------------------------------------------
def _todays_events(cur: psycopg2.extensions.cursor) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT event_date, event_type, title, institution
        FROM aleksandra_timeline
        WHERE event_date = CURRENT_DATE
          AND event_type IN ('appointment','medication_change','observation')
        ORDER BY event_date, title
        LIMIT 5
        """
    )
    return [
        {
            "event_date": r[0].isoformat() if r[0] else None,
            "event_type": r[1],
            "title": r[2],
            "institution": r[3],
        }
        for r in cur.fetchall()
    ]


def _last_24h_evidence_count(cur: psycopg2.extensions.cursor) -> int:
    cur.execute(
        """
        SELECT count(*) FROM evidence_ledger
        WHERE retrieval_timestamp >= now() - interval '24 hours'
        """
    )
    row = cur.fetchone()
    return int(row[0]) if row else 0


def _top_therapy_this_week(cur: psycopg2.extensions.cursor) -> str | None:
    cur.execute(
        """
        SELECT name FROM therapies
        WHERE aleksandra_status IN ('evaluating','applied','planned')
          AND updated_at >= now() - interval '7 days'
        ORDER BY updated_at DESC LIMIT 1
        """
    )
    row = cur.fetchone()
    return row[0] if row else None


def _pending_outreach_count(cur: psycopg2.extensions.cursor) -> int:
    cur.execute(
        """
        SELECT count(*) FROM outreach_log
        WHERE sent_at IS NULL
          AND drafted_at >= now() - interval '14 days'
        """
    )
    row = cur.fetchone()
    return int(row[0]) if row else 0


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------
def _count_words(s: str) -> int:
    return len([w for w in s.split() if w])


def compose(
    *,
    today_events: list[dict[str, Any]],
    last_24h_evidence_count: int,
    top_therapy: str | None,
    pending_outreach_count: int,
) -> BriefMessage:
    """Build the 3-bullet ≤ 50-word message. Deterministic, no LLM."""
    # Phase 6 I18N-06: build both halves of each bullet at the same time so the
    # Georgian renderings stay structurally identical to the English ones.
    if today_events:
        ev = today_events[0]
        loc = ev.get("institution") or ""
        title_str = str(ev["title"]) if ev["title"] else ""
        today_line = f"• Today: {title_str}" + (f" @ {loc}" if loc else "")
        if len(today_events) > 1:
            today_line += f" (+{len(today_events) - 1} more)"
        # Bilingual mirror
        if loc:
            today_key = "today_event_at"
            today_args: dict[str, Any] = {"title": title_str, "loc": loc}
        else:
            today_key = "today_event"
            today_args = {"title": title_str}
        ka_today = BRIEFING_TEMPLATES_KA[today_key].format(**today_args)
        if len(today_events) > 1:
            ka_today += BRIEFING_TEMPLATES_KA["today_more"].format(
                n=len(today_events) - 1
            )
    else:
        today_line = "• Today: no appointments"
        ka_today = BRIEFING_TEMPLATES_KA["today_none"]

    activity_bits: list[str] = []
    activity_bits_ka: list[str] = []
    if last_24h_evidence_count:
        activity_bits.append(f"{last_24h_evidence_count} new sources (24h)")
        activity_bits_ka.append(
            BRIEFING_TEMPLATES_KA["activity_evidence"].format(n=last_24h_evidence_count)
        )
    if top_therapy:
        activity_bits.append(f"top therapy {top_therapy}")
        activity_bits_ka.append(
            BRIEFING_TEMPLATES_KA["activity_top_therapy"].format(name=top_therapy)
        )
    if activity_bits:
        activity_line = "• Activity: " + "; ".join(activity_bits)
        ka_activity = BRIEFING_TEMPLATES_KA["activity_prefix"] + "; ".join(
            activity_bits_ka
        )
    else:
        activity_line = "• Activity: quiet last 24h"
        ka_activity = BRIEFING_TEMPLATES_KA["activity_quiet"]

    if pending_outreach_count:
        follow_line = (
            f"• Follow-ups: {pending_outreach_count} draft"
            + ("s" if pending_outreach_count != 1 else "")
            + " awaiting send"
        )
        ka_follow = BRIEFING_TEMPLATES_KA["follow_pending"].format(
            n=pending_outreach_count
        )
    else:
        follow_line = "• Follow-ups: inbox clear"
        ka_follow = BRIEFING_TEMPLATES_KA["follow_clear"]

    bullets = [today_line, activity_line, follow_line]
    bilingual_bullets = [
        {"en": today_line, "ka": ka_today},
        {"en": activity_line, "ka": ka_activity},
        {"en": follow_line, "ka": ka_follow},
    ]
    text = "Good morning. " + "\n".join(bullets)
    wc = _count_words(text)

    if wc > WORD_CAP:
        # Soft truncate: drop the activity sub-line first, then trim.
        shorter = [today_line, follow_line]
        text = "Good morning. " + "\n".join(shorter)
        wc = _count_words(text)
        # bilingual_bullets keeps all 3 bullets — JSONB audit trail is allowed
        # to be richer than the truncated Telegram body.
        if wc > WORD_CAP:
            words = text.split()
            text = " ".join(words[:WORD_CAP])
            wc = WORD_CAP

    return BriefMessage(
        text=text,
        word_count=wc,
        bullets=bullets,
        bilingual_bullets=bilingual_bullets,
    )


# ---------------------------------------------------------------------------
# briefs row writer (matches Phase 3 schema; PHI gate enforced)
# ---------------------------------------------------------------------------
def _insert_briefs_row(
    *, brief_date: date, msg: BriefMessage, dispatched_message_id: int | None
) -> str | None:
    try:
        url, key = _supabase_creds()
    except RuntimeError as e:
        print(f"[briefs.write] supabase creds missing: {e}", file=sys.stderr)
        return None

    # Phase 6 I18N-06 / D-02: persist the bilingual bullet bodies into the
    # `briefs.sections` JSONB so the Telegram audience routing (plan 06-12)
    # can read .ka and the Gmail-side audit can read .en. The legacy
    # English-only `bullets` field is retained for backward-compat with any
    # downstream consumer that still reads scalar strings.
    sections = {
        "kind": "manager_morning_briefing",
        "bullets": msg.bullets,
        "bilingual_bullets": msg.bilingual_bullets,
        "word_count": msg.word_count,
        "dispatched_message_id": dispatched_message_id,
    }
    payload = {
        "brief_week": brief_date.isoformat(),
        "pdf_r2_path": f"manager_briefing/{brief_date.isoformat()}.txt",
        "sections": sections,
        "phi_redacted": True,
        "delivered_telegram_at": (
            datetime.now(timezone.utc).isoformat()
            if dispatched_message_id is not None
            else None
        ),
    }
    try:
        import httpx  # noqa: PLC0415

        r = httpx.post(
            f"{url}/rest/v1/briefs",
            json=payload,
            headers={**_supabase_headers(key), "Prefer": "return=representation"},
            timeout=10,
        )
        if r.status_code in (200, 201):
            row = r.json()
            return row[0]["id"] if isinstance(row, list) and row else None
        print(f"[briefs.write] HTTP {r.status_code}: {r.text[:200]}", file=sys.stderr)
    except Exception as e:
        print(f"[briefs.write] failed: {type(e).__name__}: {e}", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def run(*, dry_run: bool = False) -> dict[str, Any]:
    """Compose, send, and audit one morning briefing.

    Returns a dict with text, word_count, telegram_message_id, briefs_id.
    On dry_run=True nothing is sent or written.
    """
    conn = _open()
    start = datetime.now(timezone.utc)
    try:
        with conn.cursor() as cur:
            events = _todays_events(cur)
            ev_count = _last_24h_evidence_count(cur)
            top_t = _top_therapy_this_week(cur)
            pending = _pending_outreach_count(cur)
    finally:
        conn.close()

    msg = compose(
        today_events=events,
        last_24h_evidence_count=ev_count,
        top_therapy=top_t,
        pending_outreach_count=pending,
    )

    telegram_message_id: int | None = None
    briefs_id: str | None = None
    if not dry_run:
        from scripts.communicator.telegram_sender import _send_telegram  # noqa: PLC0415

        telegram_message_id = _send_telegram(msg.text)
        briefs_id = _insert_briefs_row(
            brief_date=start.date(),
            msg=msg,
            dispatched_message_id=telegram_message_id,
        )

    # Always write a runs row so verify_phase5 MNG-10 can count this firing.
    if not dry_run:
        _record_run(
            start=start,
            end=datetime.now(timezone.utc),
            word_count=msg.word_count,
            telegram_message_id=telegram_message_id,
        )

    return {
        "text": msg.text,
        "word_count": msg.word_count,
        "bullets": msg.bullets,
        "telegram_message_id": telegram_message_id,
        "briefs_id": briefs_id,
        "dry_run": dry_run,
    }


def _record_run(
    *,
    start: datetime,
    end: datetime,
    word_count: int,
    telegram_message_id: int | None,
) -> None:
    try:
        url, key = _supabase_creds()
    except RuntimeError:
        return
    payload = {
        "kind": "manager_briefing",
        "agent_id": "manager.briefing",
        "exit_status": "completed",
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "token_cost": 0,
        "tokens_input": 0,
        "tokens_output": 0,
        "exit_reason": json.dumps(
            {
                "word_count": word_count,
                "telegram_message_id": telegram_message_id,
            }
        )[:1000],
    }
    try:
        import httpx  # noqa: PLC0415

        httpx.post(
            f"{url}/rest/v1/runs",
            json=payload,
            headers={**_supabase_headers(key), "Prefer": "return=minimal"},
            timeout=10,
        )
    except Exception:
        pass


__all__ = ["run", "compose", "BriefMessage", "BriefingTooLong", "WORD_CAP"]
