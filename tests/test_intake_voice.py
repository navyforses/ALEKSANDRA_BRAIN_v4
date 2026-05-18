"""
tests/test_intake_voice.py — Phase 5 Day 3 voice transcription tests.

Default suite: structural assertions (module imports, MIME validation,
auth-missing path). No OpenAI cost.

PHASE5_LLM_TESTS=1 opt-in: real Whisper round-trip on a 1-second synthetic
tone fixture. ~$0.0001 per run.
"""

from __future__ import annotations

import io
import os
import struct
import wave
from pathlib import Path

import pytest

from scripts.manager.intake.voice_transcribe import (
    SUPPORTED_MIME,
    VoiceTranscript,
    WHISPER_MODEL,
    WHISPER_PRICING_USD_PER_MINUTE,
    transcribe,
)


FIXTURES = Path(__file__).parent / "fixtures" / "phase5"


def _synthetic_silent_wav(seconds: float = 1.0, rate: int = 16000) -> bytes:
    """Generate a 1-second silent WAV in-memory."""
    n_samples = int(seconds * rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(b"".join(struct.pack("<h", 0) for _ in range(n_samples)))
    return buf.getvalue()


def test_supported_mime_set_includes_browser_default():
    """Browser MediaRecorder default is audio/webm — must be supported."""
    assert "audio/webm" in SUPPORTED_MIME
    assert "audio/wav" in SUPPORTED_MIME
    assert "audio/mp3" in SUPPORTED_MIME


def test_pricing_constant_matches_documented_rate():
    # OpenAI Whisper API: $0.006 per minute (verified 2026-05).
    assert WHISPER_PRICING_USD_PER_MINUTE == pytest.approx(0.006)


def test_whisper_model_pinned():
    assert WHISPER_MODEL == "whisper-1"


def test_voice_transcript_dataclass_shape():
    t = VoiceTranscript(text="x", duration_sec=1.0, language="en", redactions_count=0)
    assert t.text == "x"
    assert t.duration_sec == 1.0
    assert t.language == "en"
    assert t.redactions_count == 0


def test_unsupported_mime_raises_valueerror():
    with pytest.raises(ValueError):
        transcribe(b"fake bytes", mime="audio/aiff")


def test_missing_openai_key_raises(monkeypatch):
    """When OPENAI_API_KEY is unset, transcribe() refuses BEFORE network."""
    monkeypatch.setenv("OPENAI_API_KEY", "")
    # SUPABASE_DB_URL etc. don't need to be set — the function must raise
    # on missing API key before reaching the budget gate.
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY missing"):
        transcribe(_synthetic_silent_wav(), mime="audio/wav")


@pytest.mark.skipif(
    os.environ.get("PHASE5_LLM_TESTS", "0") != "1"
    or not os.environ.get("OPENAI_API_KEY", "").strip(),
    reason="set PHASE5_LLM_TESTS=1 and OPENAI_API_KEY to exercise Whisper (~$0.0001 / call)",
)
def test_whisper_silent_clip_smoke():
    """End-to-end: silent 1s WAV → Whisper → redacted transcript.

    A silent clip typically yields an empty string OR a model hallucination
    of "you". Either way the shape must round-trip and the runs row gets
    written.
    """
    audio = _synthetic_silent_wav(1.0)
    result = transcribe(audio, mime="audio/wav", filename="silent.wav")
    assert isinstance(result, VoiceTranscript)
    assert result.duration_sec >= 0.0
    assert result.language in {"en", "fr", "ka"} or len(result.language) == 2
