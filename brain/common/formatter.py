"""Phase 7.5 Rule #4 - Confidence intervals mandatory on every output.

A recommendation that surfaces an `expected_value` (or `predicted_*`)
without a paired `ci_low` / `ci_high` is a category-class lie: it
implies precision the model does not have. Rule #4 makes the omission
physically impossible at the output layer.

Two enforcement entry points:

    1. ``format_recommendation_text(rec, *, lang)`` - renders a
       Recommendation as a single line "<subject>: <expected> [lo, hi]".
       Raises MissingCIError if any of the three numbers is None.

    2. ``reject_output_without_ci(payload)`` - scans an arbitrary dict
       (any nesting) and raises MissingCIError if any key matching
       expected* / predicted* lacks a paired ci_low / ci_high.

Locale-aware decimal: both en and ka render with ASCII "." (matches
Phase 6 i18n decimal convention; Mkhedruli digits are NOT used).

Reference:
    .claude/agents/v7-constitution.md Rule #4 row
    brain/common/schemas.py - Recommendation (the typed companion)
"""

from __future__ import annotations

import re
from typing import Any, Literal, Optional

from brain.common.schemas import Recommendation


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class MissingCIError(ValueError):
    """Raised when an output payload is missing required CI fields.

    Rule #4: any expected_value / predicted_* leaf MUST have ci_low +
    ci_high companions. Bare point estimates are forbidden from any
    surface that reaches a clinician or the wife.
    """


# ---------------------------------------------------------------------------
# Single-recommendation formatter
# ---------------------------------------------------------------------------
def format_recommendation_text(
    rec: Recommendation, *, lang: Literal["en", "ka"]
) -> str:
    """Render a Recommendation as ``"<subject>: <expected> [<lo>, <hi>]"``.

    Args:
        rec: typed Recommendation row (Pydantic-validated upstream).
        lang: target locale tag; both en and ka use ASCII decimal "."
            (Mkhedruli digits not used in Phase 7.5).

    Returns:
        Single-line string suitable for digest body or Telegram message.

    Raises:
        MissingCIError: any of expected_value / ci_low / ci_high is None
            (Pydantic should normally already reject, but the formatter
            doubles as a defence-in-depth check).
    """
    if rec.expected_value is None or rec.ci_low is None or rec.ci_high is None:
        raise MissingCIError(
            "Phase 7.5 Rule #4: cannot format a Recommendation with any of "
            "expected_value / ci_low / ci_high == None"
        )
    if lang not in ("en", "ka"):
        raise ValueError(f"unsupported lang tag {lang!r}; expected 'en' or 'ka'")

    # ASCII decimal in both locales (Phase 6 i18n convention).
    return (
        f"{rec.subject}: {rec.expected_value:.3f} "
        f"[{rec.ci_low:.3f}, {rec.ci_high:.3f}]"
    )


# ---------------------------------------------------------------------------
# Generic payload scanner
# ---------------------------------------------------------------------------
_EXPECTED_KEY_RE = re.compile(r"^(expected|predicted)([_A-Za-z0-9]*)$")
_CI_LOW_KEYS = ("ci_low", "ci_lower", "lower", "lo")
_CI_HIGH_KEYS = ("ci_high", "ci_upper", "upper", "hi")


def _has_ci_companions(parent: dict[str, Any]) -> bool:
    """True iff parent dict carries at least one ci_low + one ci_high marker."""
    has_lo = any(k in parent for k in _CI_LOW_KEYS)
    has_hi = any(k in parent for k in _CI_HIGH_KEYS)
    return has_lo and has_hi


def _walk_for_missing_ci(
    payload: Any,
    path: str,
    bad_paths: list[str],
) -> None:
    """Recursively walk payload; collect paths with expected_* but no CI."""
    if isinstance(payload, dict):
        for k, v in payload.items():
            sub_path = f"{path}.{k}" if path else k
            if isinstance(k, str) and _EXPECTED_KEY_RE.match(k):
                # Found a point-estimate key; need CI companions in parent dict.
                if not _has_ci_companions(payload):
                    bad_paths.append(sub_path)
            _walk_for_missing_ci(v, sub_path, bad_paths)
    elif isinstance(payload, list):
        for i, item in enumerate(payload):
            _walk_for_missing_ci(item, f"{path}[{i}]", bad_paths)


def reject_output_without_ci(payload: dict[str, Any]) -> None:
    """Scan ``payload`` and raise MissingCIError on any naked point estimate.

    Walks the entire payload tree (dicts + lists). Any key matching
    ``expected*`` or ``predicted*`` without a sibling ``ci_low`` (or
    ``ci_lower`` / ``lower`` / ``lo``) AND ``ci_high`` (or ``ci_upper``
    / ``upper`` / ``hi``) in the same parent dict triggers the error.

    Args:
        payload: any JSON-shaped dict (e.g. a weekly-brief draft, a
            Telegram message body, a PDF section).

    Raises:
        MissingCIError: at least one expected_* / predicted_* key lacks
            CI companions; the error message names the violating paths.
    """
    if not isinstance(payload, dict):
        raise TypeError(
            f"reject_output_without_ci expects dict; got {type(payload).__name__}"
        )
    bad_paths: list[str] = []
    _walk_for_missing_ci(payload, "", bad_paths)
    if bad_paths:
        raise MissingCIError(
            f"Phase 7.5 Rule #4: {len(bad_paths)} point-estimate key(s) "
            f"missing ci_low + ci_high companions: {bad_paths}"
        )


__all__ = [
    "MissingCIError",
    "format_recommendation_text",
    "reject_output_without_ci",
]
