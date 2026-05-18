"""
image_ocr.py — Phase 5 Day 2 photo intake (medication labels, BMC paperwork).

Two-stage extraction:

  1. pytesseract OCR — fast, free, works for clear medication-bottle
     labels. Requires the Tesseract binary installed on the host (see
     docs/DAY2_OCR_RUNBOOK.md).

  2. Claude Sonnet 4.5 vision fallback — fires when:
       - pytesseract is not installed
       - the system Tesseract binary is missing
       - the OCR result is too short (likely poor lighting or non-Latin
         script). Threshold: ``VISION_FALLBACK_THRESHOLD_CHARS``.

Both paths run the result through ``redact_or_block`` so PHI never
leaves this module unredacted.

Public surface
--------------
    extract_text(image_bytes: bytes, *, agent_id='manager.image_ocr')
        -> ImageExtraction
"""

from __future__ import annotations

import base64
import io
import os
from dataclasses import dataclass

from scripts.manager.intake._shared import redact_or_block

try:
    from PIL import Image  # type: ignore
except ImportError:  # pragma: no cover
    Image = None  # type: ignore[assignment]

try:
    import pytesseract  # type: ignore
except ImportError:  # pragma: no cover
    pytesseract = None  # type: ignore[assignment]


VISION_FALLBACK_THRESHOLD_CHARS = 20


@dataclass
class ImageExtraction:
    text: str
    used_vision: bool
    redactions_count: int


def _configure_tesseract() -> None:
    """Honor TESSERACT_PATH env var (Windows installer default path).

    On Linux/macOS Tesseract is typically on PATH; on Windows it isn't,
    so the operator runbook says to set TESSERACT_PATH to e.g.
    C:\\Program Files\\Tesseract-OCR\\tesseract.exe.
    """
    if pytesseract is None:
        return
    candidate = os.environ.get("TESSERACT_PATH", "").strip()
    if candidate and os.path.exists(candidate):
        pytesseract.pytesseract.tesseract_cmd = candidate


def _tesseract_pass(image_bytes: bytes) -> str:
    """Return the OCR transcript, or empty string on failure."""
    if pytesseract is None or Image is None:
        return ""
    _configure_tesseract()
    try:
        img = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(img).strip()
    except Exception:
        return ""


def _vision_fallback(image_bytes: bytes, *, agent_id: str) -> str:
    """Ask Claude Sonnet 4.5 to OCR the image. Records spend in runs."""
    import anthropic

    from scripts.cognition.budget import check_daily_budget
    from scripts.ledger import load_env

    check_daily_budget(raise_on_over=True)
    load_env()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY missing")

    client = anthropic.Anthropic(api_key=api_key)
    b64 = base64.b64encode(image_bytes).decode("ascii")
    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        temperature=0.0,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Transcribe the visible text on this image. "
                            "Return ONLY the transcript with line breaks "
                            "preserved. If the image has no readable text, "
                            "return an empty string."
                        ),
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": b64,
                        },
                    },
                ],
            }
        ],
    )

    from datetime import datetime, timezone
    from scripts.cognition.llm import _record_call

    usage = getattr(resp, "usage", None)
    in_t = int(getattr(usage, "input_tokens", 0) or 0)
    out_t = int(getattr(usage, "output_tokens", 0) or 0)
    now = datetime.now(timezone.utc)
    _record_call(
        agent_id=agent_id,
        model="claude-sonnet-4-5",
        start=now,
        end=now,
        input_tokens=in_t,
        output_tokens=out_t,
        exit_status="completed",
    )
    return "".join(
        b.text for b in resp.content if getattr(b, "type", "") == "text"
    ).strip()


def extract_text(
    image_bytes: bytes, *, agent_id: str = "manager.image_ocr"
) -> ImageExtraction:
    """Run the pytesseract → vision-fallback pipeline.

    Returns redacted text + the path taken (used_vision=True iff Claude
    vision answered).
    """
    text = _tesseract_pass(image_bytes)
    used_vision = False
    if len(text) < VISION_FALLBACK_THRESHOLD_CHARS:
        vision_text = _vision_fallback(image_bytes, agent_id=agent_id)
        if vision_text:
            text = vision_text
            used_vision = True

    redacted = redact_or_block(text)
    return ImageExtraction(
        text=redacted.text,
        used_vision=used_vision,
        redactions_count=redacted.redactions_count,
    )


__all__ = ["extract_text", "ImageExtraction", "VISION_FALLBACK_THRESHOLD_CHARS"]
