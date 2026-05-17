"""
telegram_sender.py — Phase 4 ACD-01 + ACD-02 Telegram dispatcher.

Routes a (TierDecision, SummaryDraft, run_id) tuple into the family
Telegram channel according to tier:

  T0  blocked — NOT sent. We still write the alerts_log row so the audit
                trail captures every classifier output, including blocks.
  T1  urgent — sent immediately to Telegram. delivered_at = now().
  T2  action_needed — enqueued for the daily 09:00 ET batch
                       (workflows/telegram_daily_digest.json picks it up).
                       Quiet-hours: if tier_router stamped a
                       deferred_until, it's stored in payload so the
                       workflow can respect it.
  T3  important — same enqueue path as T2.
  T4  weekly — skipped here. The Sunday weekly brief is the surface for
               T4; we don't double-send.

Hard contracts:
  - Every alerts_log insert sets phi_redacted = TRUE (migration-008 CHECK
    constraint refuses the row otherwise).
  - The T1 daily cap (T1_DAILY_CAP = 1 in tier_router) is the tier_router's
    responsibility, not this sender's. By the time we see a T1 decision,
    the cap is already accounted for.
  - The sender is AUTO from day 1 for family-internal Telegram (Shako/Natia
    only). External outreach drafts remain manual via Gmail compose.

Family-internal-only: TELEGRAM_CHAT_ID is the family group chat. There is
no per-recipient routing in this sender — every dispatched message goes
to the same chat. Clinician communication goes through the Gmail draft
flow in scripts/communicator/outreach_drafter.py, not this dispatcher.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
import psycopg2

from scripts.communicator.summarize import SummaryDraft
from scripts.communicator.tier_router import TierDecision
from scripts.ledger import load_env


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------
@dataclass
class DispatchResult:
    tier: str
    alerts_log_id: str | None = None
    telegram_message_id: int | None = None
    delivered: bool = False
    deferred: bool = False
    deferred_until: datetime | None = None
    skipped: bool = False
    skipped_reason: str | None = None
    blocked: bool = False
    blocked_reason: str | None = None


# ---------------------------------------------------------------------------
# Telegram primitive
# ---------------------------------------------------------------------------
def _send_telegram(text: str) -> int:
    """Send `text` to TELEGRAM_CHAT_ID. Returns the Telegram message_id."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing from env")
    r = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    r.raise_for_status()
    body = r.json() or {}
    return int(body.get("result", {}).get("message_id") or 0)


# ---------------------------------------------------------------------------
# Message composition
# ---------------------------------------------------------------------------
_TIER_PREFIX = {
    "T1": "🔴 URGENT",
    "T2": "🟡 Action needed",
    "T3": "🟢 Important",
}


def _compose_text(decision: TierDecision, draft: SummaryDraft) -> str:
    """Build a short plain-text Telegram message for a Communicator draft."""
    prefix = _TIER_PREFIX.get(decision.tier, decision.tier)
    title_line = f"{prefix} (conf {decision.confidence:.2f})"

    # We render the first 2-3 claims max; full content lives in Notion +
    # outreach_log. Telegram's job is the notification, not the archive.
    claim_lines: list[str] = []
    for claim in draft.claims[:3]:
        snippet = claim.sentence.strip()
        if len(snippet) > 220:
            snippet = snippet[:217] + "..."
        cites = ", ".join(claim.citation_ids[:3])
        claim_lines.append(f"• {snippet}\n  [{cites}]")

    if not claim_lines:
        claim_lines.append("(no source-grounded claims in this draft)")

    tail = "Review in dashboard. Clinical decisions stay with Aleksandra's doctors."
    return "\n\n".join([title_line, "\n".join(claim_lines), tail])


# ---------------------------------------------------------------------------
# alerts_log writer
# ---------------------------------------------------------------------------
def _insert_alerts_log(
    *,
    tier: str,
    event_kind: str,
    confidence: float | None,
    payload: dict[str, Any],
    delivered_at: datetime | None,
    blocked_reason: str | None,
    originating_run_id: str | None = None,
) -> str:
    """Insert one alerts_log row. Returns new id (UUID string).

    Every insert is required to be phi_redacted=TRUE by the migration-008
    CHECK constraint. The caller is responsible for ensuring the underlying
    draft passed phi_redactor before reaching this writer.

    `originating_run_id` (migration 010 / OBS-02): the runs.id of the
    agent execution that produced this dispatch. Stored as an explicit
    column so verify_phase4 OBS-02 can confirm linkage with a single
    SQL query. Nullable for legacy/test paths.
    """
    load_env()
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO alerts_log (
                  tier, event_kind, confidence, payload,
                  delivered_at, blocked_reason,
                  phi_redacted, originating_run_id
                ) VALUES (
                  %s, %s, %s, %s::jsonb,
                  %s, %s,
                  TRUE, %s
                )
                RETURNING id
                """,
                (
                    tier,
                    event_kind,
                    confidence,
                    json.dumps(payload, default=str),
                    delivered_at,
                    blocked_reason,
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
def dispatch(
    decision: TierDecision,
    draft: SummaryDraft,
    *,
    run_id: str,
    event_kind: str,
    dry_run: bool = False,
) -> DispatchResult:
    """Route one Communicator draft through the tier-based Telegram dispatcher.

    Caller responsibilities:
      - `draft.persistable()` must be True (banned passed, redaction not
        blocked, claims cited). If False, we still record T0/blocked but
        won't send to Telegram.
      - `run_id` is the originating `runs.id` so OBS-02 (Day 6) can link
        delivered messages back to their agent run via payload.run_id.
      - `event_kind` is the upstream event taxonomy (paper_match,
        researcher_reply, trial_deadline_24h, etc.). Stored on alerts_log.

    dry_run=True does everything except the Telegram POST and the DB insert
    — used by the verifier and Manager-side sanity checks.
    """
    payload: dict[str, Any] = {
        "run_id": run_id,
        "draft_summary": draft.raw_text[:500] if draft.raw_text else "",
        "citations": list(draft.citations)[:20],
        "reason": decision.reason,
    }
    if decision.deferred_until is not None:
        payload["deferred_until"] = decision.deferred_until.isoformat()

    # --- T0: block --------------------------------------------------------
    if decision.tier == "T0":
        if dry_run:
            return DispatchResult(
                tier="T0",
                blocked=True,
                blocked_reason=decision.blocked_reason or decision.reason,
            )
        row_id = _insert_alerts_log(
            tier="T0",
            event_kind=event_kind,
            confidence=decision.confidence,
            payload=payload,
            delivered_at=None,
            blocked_reason=decision.blocked_reason or decision.reason,
            originating_run_id=run_id,
        )
        return DispatchResult(
            tier="T0",
            alerts_log_id=row_id,
            blocked=True,
            blocked_reason=decision.blocked_reason or decision.reason,
        )

    # --- T4: skip ---------------------------------------------------------
    if decision.tier == "T4":
        return DispatchResult(
            tier="T4",
            skipped=True,
            skipped_reason="T4 handled by weekly_brief — telegram_sender does not dispatch",
        )

    # --- T1: immediate Telegram ------------------------------------------
    if decision.tier == "T1":
        if not draft.persistable():
            # Defensive: T1 with a non-persistable draft is treated as T0
            return dispatch(
                TierDecision(
                    tier="T0",
                    confidence=decision.confidence,
                    reason="t1_with_non_persistable_draft",
                    blocked_reason="Underlying draft is not persistable",
                ),
                draft,
                run_id=run_id,
                event_kind=event_kind,
                dry_run=dry_run,
            )
        text = _compose_text(decision, draft)
        if dry_run:
            return DispatchResult(
                tier="T1",
                delivered=False,
                deferred=False,
                deferred_until=None,
            )
        msg_id = _send_telegram(text)
        row_id = _insert_alerts_log(
            tier="T1",
            event_kind=event_kind,
            confidence=decision.confidence,
            payload={**payload, "telegram_message_id": msg_id, "text_len": len(text)},
            delivered_at=datetime.now(timezone.utc),
            blocked_reason=None,
            originating_run_id=run_id,
        )
        return DispatchResult(
            tier="T1",
            alerts_log_id=row_id,
            telegram_message_id=msg_id,
            delivered=True,
        )

    # --- T2 / T3: enqueue for daily digest batch -------------------------
    if decision.tier in {"T2", "T3"}:
        if not draft.persistable():
            return DispatchResult(
                tier=decision.tier,
                skipped=True,
                skipped_reason="non_persistable_draft",
            )
        if dry_run:
            return DispatchResult(
                tier=decision.tier,
                deferred=decision.deferred_until is not None,
                deferred_until=decision.deferred_until,
            )
        row_id = _insert_alerts_log(
            tier=decision.tier,
            event_kind=event_kind,
            confidence=decision.confidence,
            payload=payload,
            delivered_at=None,
            blocked_reason=None,
            originating_run_id=run_id,
        )
        return DispatchResult(
            tier=decision.tier,
            alerts_log_id=row_id,
            delivered=False,
            deferred=decision.deferred_until is not None,
            deferred_until=decision.deferred_until,
        )

    # Unknown tier — defensive skip
    return DispatchResult(
        tier=decision.tier,
        skipped=True,
        skipped_reason=f"unknown_tier:{decision.tier}",
    )


def fire_daily_batch(*, dry_run: bool = False) -> dict[str, Any]:
    """Batch-deliver T2/T3 rows whose deferred_until has passed.

    Called by `workflows/telegram_daily_digest.json` at 09:00 ET. Reads
    alerts_log for pending T2/T3 rows, composes one summary Telegram
    message, marks them delivered.
    """
    load_env()
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, tier, event_kind, confidence, payload, created_at
                FROM alerts_log
                WHERE tier IN ('T2', 'T3')
                  AND delivered_at IS NULL
                  AND (
                    (payload->>'deferred_until') IS NULL
                    OR (payload->>'deferred_until')::timestamptz <= now()
                  )
                ORDER BY confidence DESC NULLS LAST, created_at ASC
                LIMIT 10
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return {"delivered": 0, "skipped": "no_pending_rows"}

    lines: list[str] = []
    ids_to_mark: list[str] = []
    for row in rows:
        row_id, tier, event_kind, confidence, payload, _ = row
        conf_str = f"{float(confidence):.2f}" if confidence is not None else "n/a"
        summary = (payload or {}).get("draft_summary") or "(no summary)"
        lines.append(f"[{tier} conf={conf_str}] {summary[:200]}")
        ids_to_mark.append(str(row_id))

    text = (
        "📨 Daily digest — pending action / important items\n\n"
        + "\n\n".join(f"{i+1}. {line}" for i, line in enumerate(lines))
        + "\n\nReview in dashboard. Clinical decisions stay with Aleksandra's doctors."
    )

    if dry_run:
        return {
            "delivered": 0,
            "dry_run": True,
            "row_count": len(rows),
            "text_len": len(text),
        }

    msg_id = _send_telegram(text)
    now = datetime.now(timezone.utc)
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE alerts_log
                SET delivered_at = %s,
                    payload = payload || jsonb_build_object('telegram_message_id', %s::bigint)
                WHERE id = ANY(%s::uuid[])
                """,
                (now, msg_id, ids_to_mark),
            )
        conn.commit()
    finally:
        conn.close()

    return {"delivered": len(rows), "telegram_message_id": msg_id}


__all__ = ["DispatchResult", "dispatch", "fire_daily_batch"]
