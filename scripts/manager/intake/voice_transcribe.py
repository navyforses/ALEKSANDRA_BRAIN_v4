"""
voice_transcribe.py — Phase 5 Day 3 voice intake via OpenAI Whisper.

Trust boundary
--------------
Audio bytes NEVER persist. The flow is:

    raw audio bytes
       └─> OpenAI Whisper API  (whisper-1)
              └─> raw transcript
                     └─> PHI redactor  (redact_or_block)
                            └─> redacted text + redactions_count

The audio blob is held only in the request lifetime of the caller —
typically a Next.js route handler or an n8n webhook payload — and is
GC'd as soon as ``transcribe(...)`` returns. There is no R2 upload,
no temp file, no cache.

Spend tracking
--------------
Whisper API is $0.006 per minute (verified 2026-05). We append a
``runs`` row with ``kind='whisper_call'`` and ``token_cost`` set to
``duration_minutes * 0.006`` so the existing daily-budget cron and
verify_phase4 OBS-03 surface count Whisper into the same daily cap.

Public surface
--------------
    transcribe(audio_bytes, *, mime='audio/webm', filename='clip.webm',
               agent_id='manager.voice_transcribe') -> VoiceTranscript
"""

from __future__ import annotations

import io
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from scripts.cognition.budget import check_daily_budget
from scripts.communicator.language import detect as detect_language
from scripts.ledger import _supabase_creds, _supabase_headers, load_env
from scripts.manager.intake._shared import redact_or_block


WHISPER_MODEL = "whisper-1"
WHISPER_PRICING_USD_PER_MINUTE = 0.006

SUPPORTED_MIME = {
    "audio/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/ogg",
    "audio/flac",
}


@dataclass
class VoiceTranscript:
    """Output of ``transcribe(...)``."""

    text: str
    duration_sec: float
    language: str
    redactions_count: int


# ---------------------------------------------------------------------------
# Spend writer — analogous to scripts.cognition.llm._record_call but for
# the Whisper line item.
# ---------------------------------------------------------------------------
def _record_whisper_call(
    *,
    agent_id: str,
    duration_sec: float,
    start: datetime,
    end: datetime,
    exit_status: str,
    exit_reason: str | None = None,
) -> None:
    try:
        url, key = _supabase_creds()
    except RuntimeError as e:
        print(f"[runs.write] supabase creds missing: {e}", file=sys.stderr)
        return

    cost = max(0.0, duration_sec / 60.0) * WHISPER_PRICING_USD_PER_MINUTE
    payload: dict[str, Any] = {
        "kind": "whisper_call",
        "agent_id": agent_id,
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "token_cost": round(cost, 6),
        "tokens_input": 0,
        "tokens_output": 0,
        "exit_status": exit_status,
    }
    if exit_reason:
        payload["exit_reason"] = exit_reason[:1000]

    try:
        httpx.post(
            f"{url}/rest/v1/runs",
            json=payload,
            headers={**_supabase_headers(key), "Prefer": "return=minimal"},
            timeout=10,
        )
    except Exception as e:
        print(
            f"[runs.write] failed to record whisper_call: {type(e).__name__}: {e}",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def transcribe(
    audio_bytes: bytes,
    *,
    mime: str = "audio/webm",
    filename: str = "clip.webm",
    agent_id: str = "manager.voice_transcribe",
) -> VoiceTranscript:
    """Send audio to OpenAI Whisper, redact the transcript, return text + meta.

    Args:
        audio_bytes: Raw audio. Held only in this function's local scope.
        mime: MIME type ('audio/webm' for browser MediaRecorder default).
        filename: Filename passed to the multipart upload — Whisper uses
                  the extension for codec hinting.
        agent_id: Spend bookkeeping ('manager.voice_transcribe' default).

    Returns:
        VoiceTranscript(text, duration_sec, language, redactions_count).

    Raises:
        RuntimeError: OPENAI_API_KEY missing.
        ValueError: unsupported MIME.
        BlockedByRedactor (from _shared): if the redactor's hard-block
          pattern fires on the transcript (e.g., the user dictated a
          NIfTI filename). The audio is already gone at that point.
    """
    if mime not in SUPPORTED_MIME:
        raise ValueError(f"unsupported audio MIME {mime!r}")

    load_env()
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY missing — voice transcription requires an OpenAI key. "
            "See docs/DAY3_VOICE_RUNBOOK.md for setup."
        )

    # Defense-in-depth budget gate. Whisper is bookkept against the same
    # daily cap as Anthropic calls. raise_on_over=True so the audio never
    # crosses the network when over budget.
    check_daily_budget(raise_on_over=True)

    # Lazy import — keeps voice_transcribe.py cheap when other parsers
    # import _shared transitively.
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    start = datetime.now(timezone.utc)
    duration_sec = 0.0
    try:
        # The SDK accepts a file-like object (or tuple (name, file)) for
        # the `file` arg. We wrap bytes in BytesIO so nothing hits disk.
        buf = io.BytesIO(audio_bytes)
        buf.name = filename  # Whisper SDK uses .name for the upload filename
        result = client.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=buf,
            response_format="verbose_json",
        )
        # verbose_json gives duration + language + text
        raw_text = getattr(result, "text", "") or ""
        duration_sec = float(getattr(result, "duration", 0.0) or 0.0)
        api_language = (getattr(result, "language", "") or "").lower()
    except Exception as e:
        end = datetime.now(timezone.utc)
        _record_whisper_call(
            agent_id=agent_id,
            duration_sec=duration_sec,
            start=start,
            end=end,
            exit_status="failed",
            exit_reason=f"{type(e).__name__}: {str(e)[:600]}",
        )
        raise

    end = datetime.now(timezone.utc)
    _record_whisper_call(
        agent_id=agent_id,
        duration_sec=duration_sec,
        start=start,
        end=end,
        exit_status="completed",
    )

    # Confirm language via the deterministic detector — Whisper's `language`
    # field uses ISO 639-1; map to {en, fr, ka} since those are the three
    # outreach languages Phase 3 ships. If Whisper says something we don't
    # ship, fall back to the deterministic detector's verdict.
    if api_language in {"en", "fr", "ka"}:
        language = api_language
    else:
        decision = detect_language(raw_text)
        language = decision.label

    redacted = redact_or_block(raw_text)
    return VoiceTranscript(
        text=redacted.text,
        duration_sec=duration_sec,
        language=language,
        redactions_count=redacted.redactions_count,
    )


__all__ = ["transcribe", "VoiceTranscript", "WHISPER_MODEL", "SUPPORTED_MIME"]
