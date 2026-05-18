"""
tests/test_intake_email.py — Phase 5 Day 2 forwarded-email parser tests.

Pure stdlib + PHI redactor; no LLM cost. Always safe to run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.manager.intake._shared import BlockedByRedactor
from scripts.manager.intake.email_parser import parse_eml_text


FIXTURES = Path(__file__).parent / "fixtures" / "phase5"


def test_parse_sydney_followup_eml():
    eml = (FIXTURES / "sydney_followup.eml").read_text(encoding="utf-8")
    parsed = parse_eml_text(eml)
    assert parsed.sender is not None and "Sydney" in parsed.sender
    assert parsed.subject == "RE: Duke EAP timing — windows for cord blood infusion"
    assert "jincharadzeshako@gmail.com" in " ".join(parsed.to)
    assert parsed.cc and "natia" in parsed.cc[0].lower()
    assert "Window A" in parsed.body_text
    # PHI redactor: Duke EAP is a hospital pattern -> redacted
    assert "Duke EAP" not in parsed.body_text
    assert parsed.redactions_count >= 1


def test_parse_minimal_inline_string():
    raw = (
        "From: Alice <alice@example.org>\r\n"
        "To: Bob <bob@example.org>\r\n"
        "Subject: Hello\r\n"
        "Date: Tue, 13 May 2026 09:00:00 +0000\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        "\r\n"
        "Just checking in.\r\n"
    )
    parsed = parse_eml_text(raw)
    assert parsed.sender == "Alice <alice@example.org>"
    assert parsed.subject == "Hello"
    assert parsed.body_text.strip() == "Just checking in."
    assert parsed.attachments == []


def test_block_on_mri_attachment_filename():
    # Forge a multipart .eml with a .nii.gz attachment — must hard-block.
    raw = (
        "From: bad@example.org\r\n"
        "To: ok@example.org\r\n"
        "Subject: scan\r\n"
        'Content-Type: multipart/mixed; boundary="b1"\r\n'
        "\r\n"
        "--b1\r\n"
        "Content-Type: text/plain\r\n"
        "\r\n"
        "Attached.\r\n"
        "--b1\r\n"
        "Content-Type: application/octet-stream\r\n"
        'Content-Disposition: attachment; filename="brain.nii.gz"\r\n'
        "\r\n"
        "JUNKBYTES\r\n"
        "--b1--\r\n"
    )
    with pytest.raises(BlockedByRedactor) as exc:
        parse_eml_text(raw)
    assert "nii.gz" in str(exc.value)
