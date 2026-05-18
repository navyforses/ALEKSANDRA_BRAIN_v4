"""
scripts.manager.intake — Phase 5 Day 2 + Day 3 multi-modal parsers.

Submodules (filled in on Day 2 / Day 3):

  _shared          — common entity dataclasses + PHI redactor adapter
  pdf_parser       — pdfplumber → text/tables; Claude vision fallback
  image_ocr        — Pillow + Tesseract; Claude vision fallback
  voice_transcribe — OpenAI Whisper API client (Day 3)
  email_parser     — stdlib email.policy.default
  text_extractor   — Claude Sonnet 4.5 structured output

Every parser writes its output to ``intake_drops`` only after the
project-wide PHI redactor (``scripts.communicator.phi_redactor.redact``)
has confirmed the input is PHI-clean. The CHECK constraint
``intake_drops_must_redact`` enforces this at the database boundary.
"""

from __future__ import annotations

__all__: list[str] = []
