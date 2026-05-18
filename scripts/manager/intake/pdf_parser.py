"""
pdf_parser.py — Phase 5 Day 2 PDF intake parser.

Two-stage extraction:

  1. pdfplumber pulls plain text + table rows out of the PDF. For
     born-digital documents (most BMC discharge summaries, all
     researcher-forwarded papers) this is enough.

  2. If the text yield is below ``VISION_FALLBACK_THRESHOLD_CHARS``,
     the PDF is suspected to be scanned. The parser renders each page
     as an image and asks Claude Sonnet 4.5 to OCR the visible text.

Both stages funnel into ``redact_or_block`` BEFORE the result is
returned — PHI never leaves this module unredacted, and a referenced
.nii/.dcm filename hard-blocks persistence.

Public surface
--------------
    extract_text(pdf_bytes: bytes) -> PdfExtraction
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass, field
from typing import Any

from scripts.manager.intake._shared import redact_or_block

# pdfplumber is optional at import time — tests can run without it if they
# only exercise the dataclass + dispatch logic.
try:
    import pdfplumber  # type: ignore
except ImportError:  # pragma: no cover - exercised in CI without pdfplumber
    pdfplumber = None  # type: ignore[assignment]

# pillow is optional too — only the vision fallback needs it.
try:
    from PIL import Image  # type: ignore  # noqa: F401
except ImportError:  # pragma: no cover
    Image = None  # type: ignore[assignment]


VISION_FALLBACK_THRESHOLD_CHARS = 100


@dataclass
class PdfExtraction:
    text: str
    page_count: int
    used_vision: bool
    redactions_count: int
    tables: list[list[list[str | None]]] = field(default_factory=list)


def _pdfplumber_pass(pdf_bytes: bytes) -> tuple[str, int, list[list[list[str | None]]]]:
    """Return (concatenated_text, page_count, tables)."""
    if pdfplumber is None:
        raise RuntimeError(
            "pdfplumber not installed. uv pip install 'pdfplumber>=0.11' "
            "or only call extract_text on born-digital PDFs after install."
        )
    chunks: list[str] = []
    tables: list[list[list[str | None]]] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            chunks.append(page_text)
            for table in page.extract_tables() or []:
                tables.append(table)
        page_count = len(pdf.pages)
    return ("\n\n".join(chunks).strip(), page_count, tables)


def _vision_fallback(pdf_bytes: bytes, *, agent_id: str) -> str:
    """Render each page to PNG and ask Claude Sonnet 4.5 to OCR it.

    Lazy-imports anthropic + pillow + pdfplumber so this function is only
    paid for when truly needed.
    """
    if pdfplumber is None:
        raise RuntimeError("pdfplumber required for vision fallback page rendering")
    if Image is None:
        raise RuntimeError("Pillow required for vision fallback. uv pip install pillow")

    import anthropic

    from scripts.cognition.budget import check_daily_budget
    from scripts.ledger import load_env
    import os

    # Budget gate before any Claude call.
    check_daily_budget(raise_on_over=True)
    load_env()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY missing")

    # Render pages → PNG bytes.
    images_b64: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            pil_image = page.to_image(resolution=150).original  # type: ignore[union-attr]
            buf = io.BytesIO()
            pil_image.save(buf, format="PNG")
            images_b64.append(base64.b64encode(buf.getvalue()).decode("ascii"))

    if not images_b64:
        return ""

    client = anthropic.Anthropic(api_key=api_key)
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                "Transcribe the visible text from each page in reading order. "
                "Return ONLY the transcript — no commentary, no Markdown. "
                "Preserve paragraph breaks with blank lines."
            ),
        }
    ]
    for b64 in images_b64:
        content.append(
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": b64},
            }
        )
    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        temperature=0.0,
        messages=[{"role": "user", "content": content}],
    )

    # Mirror llm._record_call so the spend is tracked.
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
    pdf_bytes: bytes, *, agent_id: str = "manager.pdf_parser"
) -> PdfExtraction:
    """Run the pdfplumber → vision-fallback pipeline.

    Always redacts the final text via ``redact_or_block`` before returning.
    """
    text, page_count, tables = _pdfplumber_pass(pdf_bytes)
    used_vision = False
    if len(text) < VISION_FALLBACK_THRESHOLD_CHARS:
        # likely scanned — promote to vision
        vision_text = _vision_fallback(pdf_bytes, agent_id=agent_id)
        if vision_text:
            text = vision_text
            used_vision = True

    redacted = redact_or_block(text)
    return PdfExtraction(
        text=redacted.text,
        page_count=page_count,
        used_vision=used_vision,
        redactions_count=redacted.redactions_count,
        tables=tables,
    )


__all__ = ["extract_text", "PdfExtraction", "VISION_FALLBACK_THRESHOLD_CHARS"]
