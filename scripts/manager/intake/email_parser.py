"""
email_parser.py — Phase 5 Day 2 forwarded-email parser.

Uses the stdlib ``email`` module with ``email.policy.default`` so unicode
bodies, attachments, and structured headers are all handled correctly.

Output shape
------------
``ParsedEmail`` carries the canonical fields (from / to / cc / subject /
date / body_text) plus a list of attachment summaries. The body text is
PHI-redacted before being returned, and any attachment whose filename is
``*.nii(.gz)`` or ``*.dcm`` triggers ``BlockedByRedactor`` so a forwarded
MRI never persists.

Public surface
--------------
    parse_eml(raw_bytes: bytes) -> ParsedEmail
    parse_eml_text(raw_str: str) -> ParsedEmail
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from email import message_from_bytes, message_from_string, policy
from email.message import Message

from scripts.manager.intake._shared import BlockedByRedactor, redact_or_block


_BLOCK_ATTACHMENT = re.compile(r".+\.(?:nii(?:\.gz)?|dcm)$", re.IGNORECASE)


@dataclass
class AttachmentSummary:
    filename: str
    content_type: str
    size_bytes: int


@dataclass
class ParsedEmail:
    sender: str | None
    to: list[str] = field(default_factory=list)
    cc: list[str] = field(default_factory=list)
    subject: str | None = None
    date: str | None = None
    body_text: str = ""
    attachments: list[AttachmentSummary] = field(default_factory=list)
    redactions_count: int = 0


def _split_addrs(value: str | None) -> list[str]:
    if not value:
        return []
    parts = [p.strip() for p in value.split(",")]
    return [p for p in parts if p]


def _extract_body_text(msg: Message) -> str:
    """Walk the MIME tree and return the first text/plain body found.

    Falls back to text/html stripped of tags if no text/plain part exists.
    """
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                continue
            ctype = part.get_content_type()
            if ctype == "text/plain":
                try:
                    return part.get_content()
                except (LookupError, UnicodeDecodeError, KeyError):
                    return part.get_payload(decode=True).decode(
                        "utf-8", errors="replace"
                    )
        # fallback to first text/html
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                continue
            if part.get_content_type() == "text/html":
                try:
                    html = part.get_content()
                except (LookupError, UnicodeDecodeError, KeyError):
                    html = part.get_payload(decode=True).decode(
                        "utf-8", errors="replace"
                    )
                return _strip_html(html)
        return ""

    # single-part
    ctype = msg.get_content_type()
    if ctype == "text/plain":
        try:
            return msg.get_content()
        except (LookupError, UnicodeDecodeError, KeyError):
            return msg.get_payload(decode=True).decode("utf-8", errors="replace")
    if ctype == "text/html":
        try:
            html = msg.get_content()
        except (LookupError, UnicodeDecodeError, KeyError):
            html = msg.get_payload(decode=True).decode("utf-8", errors="replace")
        return _strip_html(html)
    return ""


def _strip_html(html: str) -> str:
    """Very small HTML → text fallback. Good enough for forwarded emails."""
    text = re.sub(r"<\s*br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</\s*p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return text


def _walk_attachments(msg: Message) -> list[AttachmentSummary]:
    out: list[AttachmentSummary] = []
    if not msg.is_multipart():
        return out
    for part in msg.walk():
        if part.get_content_disposition() != "attachment":
            continue
        filename = part.get_filename() or "(unnamed)"
        ctype = part.get_content_type() or "application/octet-stream"
        try:
            size = len(part.get_payload(decode=True) or b"")
        except Exception:
            size = 0
        out.append(
            AttachmentSummary(filename=filename, content_type=ctype, size_bytes=size)
        )
    return out


def _parse_message(msg: Message) -> ParsedEmail:
    # Hard-block MRI/DICOM attachments BEFORE any redaction or body extraction.
    for att in _walk_attachments(msg):
        if _BLOCK_ATTACHMENT.match(att.filename):
            raise BlockedByRedactor(
                f"MRI/DICOM attachment '{att.filename}' refused at intake"
            )

    body_raw = _extract_body_text(msg)
    redacted = redact_or_block(body_raw)

    return ParsedEmail(
        sender=msg.get("From"),
        to=_split_addrs(msg.get("To")),
        cc=_split_addrs(msg.get("Cc")),
        subject=msg.get("Subject"),
        date=msg.get("Date"),
        body_text=redacted.text,
        attachments=_walk_attachments(msg),
        redactions_count=redacted.redactions_count,
    )


def parse_eml(raw_bytes: bytes) -> ParsedEmail:
    """Parse a forwarded email from raw .eml bytes."""
    msg = message_from_bytes(raw_bytes, policy=policy.default)
    return _parse_message(msg)


def parse_eml_text(raw_str: str) -> ParsedEmail:
    """Parse a forwarded email from a string (already decoded)."""
    msg = message_from_string(raw_str, policy=policy.default)
    return _parse_message(msg)


__all__ = ["ParsedEmail", "AttachmentSummary", "parse_eml", "parse_eml_text"]
