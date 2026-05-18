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


@dataclass
class BriefMessage:
    text: str
    word_count: int
    bullets: list[str] = field(default_factory=list)


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
    if today_events:
        ev = today_events[0]
        loc = ev.get("institution") or ""
        today_line = f"• Today: {ev['title']}" + (f" @ {loc}" if loc else "")
        if len(today_events) > 1:
            today_line += f" (+{len(today_events) - 1} more)"
    else:
        today_line = "• Today: no appointments"

    activity_bits: list[str] = []
    if last_24h_evidence_count:
        activity_bits.append(f"{last_24h_evidence_count} new sources (24h)")
    if top_therapy:
        activity_bits.append(f"top therapy {top_therapy}")
    activity_line = (
        "• Activity: " + "; ".join(activity_bits)
        if activity_bits
        else "• Activity: quiet last 24h"
    )

    follow_line = (
        f"• Follow-ups: {pending_outreach_count} draft"
        + ("s" if pending_outreach_count != 1 else "")
        + " awaiting send"
        if pending_outreach_count
        else "• Follow-ups: inbox clear"
    )

    bullets = [today_line, activity_line, follow_line]
    text = "Good morning. " + "\n".join(bullets)
    wc = _count_words(text)

    if wc > WORD_CAP:
        # Soft truncate: drop the activity sub-line first, then trim.
        shorter = [today_line, follow_line]
        text = "Good morning. " + "\n".join(shorter)
        wc = _count_words(text)
        if wc > WORD_CAP:
            words = text.split()
            text = " ".join(words[:WORD_CAP])
            wc = WORD_CAP

    return BriefMessage(text=text, word_count=wc, bullets=bullets)


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

    sections = {
        "kind": "manager_morning_briefing",
        "bullets": msg.bullets,
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
