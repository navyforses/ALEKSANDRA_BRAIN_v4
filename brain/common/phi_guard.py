"""Phase 7.5 Rule #6 - PHI pre-prompt regex guard.

Extends Phase 6 redactor (viewer/lib/phi_redactor + brain/common
ancestors). The guard runs BEFORE any string reaches an LLM, Telegram
message, Gmail draft, PDF section, or external log.

Three entry points:

    * ``redact_phi(text)`` - returns ``(redacted_text, matches)``.
    * ``assert_no_phi(text, source=...)`` - raises PHIDetectedError
      if any pattern matches.
    * ``PHI_PATTERNS`` - exposed dict of named compiled regexes so
      callers can extend the conservative defaults.

Patterns are CONSERVATIVE: over-redaction is preferred to leakage.
False positives surface as ``[REDACTED:<name>]`` tokens in the output;
they do not block the call.

Patient-specific safety nets:
    * Aleksandra Jincharadze's BMC MRN is 7616818 - explicit
      `\\b76168\\d{2,}\\b` net in addition to the general MRN pattern.

Reference:
    .claude/agents/v7-constitution.md Rule #6 row
    CLAUDE.md Phase VI redactor (Phase 6 KA / EN PHI lexicon)
"""

from __future__ import annotations

import re
from typing import Pattern


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class PHIDetectedError(RuntimeError):
    """Raised when assert_no_phi finds at least one PHI match."""


# ---------------------------------------------------------------------------
# Pattern catalog
# ---------------------------------------------------------------------------
# Keyed by short name; value is a compiled regex. Each match is replaced
# with `[REDACTED:<name>]`. Names appear in error messages so debugging
# is possible without exposing the raw matched string.
PHI_PATTERNS: dict[str, Pattern[str]] = {
    # Generic MRN label
    "mrn_labeled": re.compile(r"\bMRN[:\s]*\d{6,}\b"),
    # Aleksandra-specific BMC MRN net (defense-in-depth)
    "mrn_bmc_aleksandra": re.compile(r"\b76168\d{2,}\b"),
    # Doctor names - covers "Dr. Hien", "Dr Jack Maypole", etc.
    "doctor_name": re.compile(r"\bDr\.?\s+[A-Z][a-zA-Z\-]+(?:\s+[A-Z][a-zA-Z\-]+)*\b"),
    # Date of birth-like patterns: 1-2/1-2/4-digit-year
    "dob_slash": re.compile(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b"),
    # SSN-like (US 3-2-4)
    "ssn_like": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    # Email - conservative net
    "email": re.compile(
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
    ),
    # US phone with parens or dashes
    "phone_us": re.compile(
        r"\b(?:\(\d{3}\)\s*|\d{3}[-.\s])\d{3}[-.\s]\d{4}\b"
    ),
}


def redact_phi(text: str) -> tuple[str, list[str]]:
    """Replace each PHI match with ``[REDACTED:<pattern_name>]``.

    Args:
        text: arbitrary input string.

    Returns:
        ``(redacted_text, matches)`` where matches is a list of
        ``"<pattern_name>:<original_match>"`` strings. The original
        matched text appears in the returned list so callers can audit
        what was redacted (this list MUST NOT be logged to stdout / a
        third-party API; it is intended for in-memory inspection only).
    """
    if not isinstance(text, str):
        raise TypeError(
            f"redact_phi expects str; got {type(text).__name__}"
        )
    matches: list[str] = []
    out = text
    for name, pat in PHI_PATTERNS.items():
        def _sub(m: re.Match[str], _name: str = name) -> str:
            matches.append(f"{_name}:{m.group(0)}")
            return f"[REDACTED:{_name}]"

        out = pat.sub(_sub, out)
    return out, matches


def assert_no_phi(text: str, *, source: str = "unknown") -> None:
    """Raise PHIDetectedError if `text` contains any PHI pattern match.

    Args:
        text: arbitrary input string.
        source: caller-supplied label used in the error message
            (does NOT include the raw matched text).

    Raises:
        PHIDetectedError: at least one pattern matched. The exception
            message lists the pattern names that fired (NOT the raw
            content) so the error is loggable without leaking PHI.
    """
    _, matches = redact_phi(text)
    if matches:
        names = sorted({m.split(":", 1)[0] for m in matches})
        raise PHIDetectedError(
            f"Phase 7.5 Rule #6: PHI detected in source={source!r} - "
            f"pattern hits: {names}; total matches: {len(matches)}"
        )


__all__ = [
    "PHIDetectedError",
    "PHI_PATTERNS",
    "redact_phi",
    "assert_no_phi",
]
