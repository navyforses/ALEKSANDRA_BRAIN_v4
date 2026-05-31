"""Phase 7.4 Day 7 — Telegram outbound dry-run flow.

Wraps the rate-limited send of an `OutboundQuestion` to the family Telegram
channel. In code-complete mode this is always a dry-run: we log the
rendered text and the rate-limit decision, never reach a live Telegram
bot.

Production wiring deferred (per dispatch contract): the live path imports
`scripts.communicator.telegram_sender` (or `scripts.manager.telegram_sender`)
lazily. ImportError -> status `missing_dependency`.

Emergency switch: `EMERGENCY_FREEZE = True` makes every send return early
without touching the rate limiter or the network. Spec §5.3.
"""

from __future__ import annotations

import sys
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from brain.active.rate_limiter import (
    WEEKLY_CAP,
    can_send_question,
    record_sent,
    weekly_sent_count,
)


# Emergency freeze switch (spec §5.3). Flip to True to halt every send.
EMERGENCY_FREEZE: bool = False


class OutboundQuestion(BaseModel):
    """One question scheduled for outbound delivery."""

    model_config = ConfigDict(extra="forbid")

    dim_name: str = Field(..., min_length=1)
    observation_type: str = Field(..., min_length=1)
    text_ka: str = Field(..., min_length=1)
    text_en: str = Field(..., min_length=1)
    eig_nats: float = Field(..., ge=0.0)
    wife_chat_id: str = Field(..., min_length=1)
    week_iso: str = Field(..., min_length=1)
    dry_run: bool = True
    expected_format: str = Field(..., min_length=1)


def _try_import_live_sender():
    """Lazy import of the production Telegram sender.

    Phase 4 ships `scripts.communicator.telegram_sender`. Phase 5
    introduced an alternate `scripts.manager.telegram_sender` reference.
    We try both before failing.
    """
    try:
        from scripts.communicator.telegram_sender import (  # type: ignore  # noqa: WPS433
            send_telegram_message,
        )
        return send_telegram_message
    except Exception:
        pass
    try:
        from scripts.manager.telegram_sender import (  # type: ignore  # noqa: WPS433
            send_telegram_message,
        )
        return send_telegram_message
    except Exception:
        return None


def _log(msg: str) -> None:
    print(f"[telegram_flow] {msg}", file=sys.stderr)


def send_question(
    q: OutboundQuestion,
    *,
    force_dry_run: bool = False,
) -> dict:
    """Send `q` according to rate limit + dry-run + emergency-freeze rules.

    Returns a result dict with at least the `status` key:
        - "frozen"             : EMERGENCY_FREEZE is True
        - "rate_limited"       : weekly cap reached for this ISO week
        - "dry_run"            : dry-run mode (counter still incremented)
        - "missing_dependency" : live mode requested but sender unimportable
        - "sent"               : live send succeeded (production only)
        - "error"              : exception during live send
    """
    if EMERGENCY_FREEZE:
        _log(f"frozen (EMERGENCY_FREEZE on): week={q.week_iso} dim={q.dim_name}")
        return {
            "status": "frozen",
            "dim_name": q.dim_name,
            "week_iso": q.week_iso,
        }

    if not can_send_question(q.week_iso):
        current = weekly_sent_count(q.week_iso)
        _log(
            f"rate_limited week={q.week_iso} count={current}/{WEEKLY_CAP} "
            f"dim={q.dim_name}"
        )
        return {
            "status": "rate_limited",
            "weekly_cap": WEEKLY_CAP,
            "current_count": current,
            "week_iso": q.week_iso,
            "dim_name": q.dim_name,
        }

    dry = q.dry_run or force_dry_run
    if dry:
        _log(
            f"dry_run week={q.week_iso} dim={q.dim_name} "
            f"chat={q.wife_chat_id} text_ka_len={len(q.text_ka)}"
        )
        # Counter increment so rate-limit testing exercises the full path.
        record_sent(q.week_iso)
        return {
            "status": "dry_run",
            "rendered_text": q.text_ka,
            "rendered_text_en": q.text_en,
            "dim_name": q.dim_name,
            "observation_type": q.observation_type,
            "week_iso": q.week_iso,
            "expected_format": q.expected_format,
        }

    # Live path
    sender = _try_import_live_sender()
    if sender is None:
        _log("live mode requested but telegram_sender module not importable")
        return {
            "status": "missing_dependency",
            "error": "telegram_sender module not found",
            "dim_name": q.dim_name,
        }
    try:
        result = sender(q.wife_chat_id, q.text_ka)
        record_sent(q.week_iso)
        return {
            "status": "sent",
            "dim_name": q.dim_name,
            "week_iso": q.week_iso,
            "raw": result if isinstance(result, dict) else {"return": str(result)},
        }
    except Exception as exc:  # noqa: BLE001
        _log(f"live send error: {type(exc).__name__}: {exc}")
        return {
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "dim_name": q.dim_name,
        }


__all__ = [
    "EMERGENCY_FREEZE",
    "OutboundQuestion",
    "send_question",
]
