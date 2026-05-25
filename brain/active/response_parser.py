"""Phase 7.4 Day 8 — Response parser.

Voice / text transcripts arrive in mixed Georgian + English. Each registered
expected_format has its own parser:

    integer_seconds    "8 წამი" | "5-6 წამი დაიჭირა" | "12 seconds" -> int
    integer_count      bare integer; multiple -> largest
    float_value        decimal number; supports KA decimal commas (5,5 -> 5.5)
    boolean            KA კი/დიახ/ხო / არა / არ ; EN yes/y/true/no/n/false
    categorical_choice fuzzy match against caller-supplied options
    scale_0_5          integer 0..5 ; out-of-range -> confidence 0

`ParsedResponse.confidence` is a heuristic ∈ [0, 1]:
    * 0.95+ exact, unambiguous
    * 0.6-0.9 multiple numbers (we picked the largest), boolean shortform
    * 0.4 noisy extraction
    * 0.0 unparseable / out-of-range
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


ParsedValueT = Union[int, float, bool, str, list[float], None]


class ParsedResponse(BaseModel):
    """Result of parsing one raw transcript."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    expected_format: str
    raw_text: str
    parsed_value: Any = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    notes: str = ""


# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------
_INT_RE = re.compile(r"(\d+)")
_FLOAT_RE = re.compile(r"(\d+(?:[.,]\d+)?)")
_SEC_UNIT_RE = re.compile(r"\d+\s*(?:წამ|წამი|sec|seconds?|s\b)", re.IGNORECASE)

_KA_YES = {"კი", "დიახ", "ხო", "ხოო"}
_KA_NO = {"არა", "არ"}
_EN_YES = {"yes", "y", "true", "1", "yep", "yeah"}
_EN_NO = {"no", "n", "false", "0", "nope", "nah"}

# Mkhedruli number words -> digit (just in case parent writes "ხუთი")
_KA_NUMBER_WORDS = {
    "ერთი": 1,
    "ორი": 2,
    "სამი": 3,
    "ოთხი": 4,
    "ხუთი": 5,
    "ექვსი": 6,
    "შვიდი": 7,
    "რვა": 8,
    "ცხრა": 9,
    "ათი": 10,
    "თერთმეტი": 11,
    "თორმეტი": 12,
}


# ---------------------------------------------------------------------------
# Individual parsers
# ---------------------------------------------------------------------------
def _extract_all_ints(text: str) -> list[int]:
    digits = [int(m.group(1)) for m in _INT_RE.finditer(text)]
    word_hits = [
        v for word, v in _KA_NUMBER_WORDS.items() if word in text
    ]
    return digits + word_hits


def _parse_integer_seconds(text: str) -> ParsedResponse:
    ints = _extract_all_ints(text)
    if not ints:
        return ParsedResponse(
            expected_format="integer_seconds",
            raw_text=text,
            parsed_value=None,
            confidence=0.0,
            notes="no integers found",
        )
    largest = max(ints)
    unit_match = _SEC_UNIT_RE.search(text)
    if len(ints) == 1 and unit_match:
        return ParsedResponse(
            expected_format="integer_seconds",
            raw_text=text,
            parsed_value=largest,
            confidence=0.95,
            notes="single integer with unit",
        )
    if len(ints) == 1:
        return ParsedResponse(
            expected_format="integer_seconds",
            raw_text=text,
            parsed_value=largest,
            confidence=0.9,
            notes="single integer no explicit unit",
        )
    # Multiple numbers -> range. Pick the largest; confidence drops.
    return ParsedResponse(
        expected_format="integer_seconds",
        raw_text=text,
        parsed_value=largest,
        confidence=0.6,
        notes=f"multiple integers {ints}; picked largest",
    )


def _parse_integer_count(text: str) -> ParsedResponse:
    ints = _extract_all_ints(text)
    if not ints:
        return ParsedResponse(
            expected_format="integer_count",
            raw_text=text,
            parsed_value=None,
            confidence=0.0,
            notes="no integers",
        )
    if len(ints) == 1:
        return ParsedResponse(
            expected_format="integer_count",
            raw_text=text,
            parsed_value=ints[0],
            confidence=0.95,
            notes="single integer",
        )
    return ParsedResponse(
        expected_format="integer_count",
        raw_text=text,
        parsed_value=max(ints),
        confidence=0.6,
        notes=f"multiple integers {ints}; picked largest",
    )


def _parse_float_value(text: str) -> ParsedResponse:
    matches = _FLOAT_RE.findall(text)
    if not matches:
        return ParsedResponse(
            expected_format="float_value",
            raw_text=text,
            parsed_value=None,
            confidence=0.0,
            notes="no numbers",
        )
    nums = [float(m.replace(",", ".")) for m in matches]
    if len(nums) == 1:
        return ParsedResponse(
            expected_format="float_value",
            raw_text=text,
            parsed_value=nums[0],
            confidence=0.9,
            notes="single float",
        )
    return ParsedResponse(
        expected_format="float_value",
        raw_text=text,
        parsed_value=max(nums),
        confidence=0.5,
        notes=f"multiple floats {nums}; picked largest",
    )


def _parse_boolean(text: str) -> ParsedResponse:
    lowered = text.lower().strip().strip(".,!?")
    tokens = re.split(r"\s+", lowered)
    token_set = set(tokens)
    # KA exact match
    if token_set & _KA_YES:
        return ParsedResponse(
            expected_format="boolean", raw_text=text, parsed_value=True, confidence=0.95
        )
    if token_set & _KA_NO:
        return ParsedResponse(
            expected_format="boolean", raw_text=text, parsed_value=False, confidence=0.95
        )
    # EN exact match
    if token_set & _EN_YES:
        return ParsedResponse(
            expected_format="boolean", raw_text=text, parsed_value=True, confidence=0.95
        )
    if token_set & _EN_NO:
        return ParsedResponse(
            expected_format="boolean", raw_text=text, parsed_value=False, confidence=0.95
        )
    # Substring fallback
    for w in _KA_YES | _EN_YES:
        if w in lowered:
            return ParsedResponse(
                expected_format="boolean", raw_text=text, parsed_value=True, confidence=0.5
            )
    for w in _KA_NO | _EN_NO:
        if w in lowered:
            return ParsedResponse(
                expected_format="boolean", raw_text=text, parsed_value=False, confidence=0.5
            )
    return ParsedResponse(
        expected_format="boolean",
        raw_text=text,
        parsed_value=None,
        confidence=0.0,
        notes="no yes/no token",
    )


def _parse_scale_0_5(text: str) -> ParsedResponse:
    ints = _extract_all_ints(text)
    if not ints:
        return ParsedResponse(
            expected_format="scale_0_5",
            raw_text=text,
            parsed_value=None,
            confidence=0.0,
            notes="no integer",
        )
    val = ints[0]
    if 0 <= val <= 5:
        return ParsedResponse(
            expected_format="scale_0_5",
            raw_text=text,
            parsed_value=val,
            confidence=0.95,
        )
    return ParsedResponse(
        expected_format="scale_0_5",
        raw_text=text,
        parsed_value=None,
        confidence=0.0,
        notes=f"value {val} outside 0-5 range",
    )


def _parse_categorical_choice(
    text: str, *, options: Optional[list[str]] = None
) -> ParsedResponse:
    options = options or []
    if not options:
        return ParsedResponse(
            expected_format="categorical_choice",
            raw_text=text,
            parsed_value=text.strip(),
            confidence=0.3,
            notes="no options supplied; returning raw text",
        )
    lowered = text.lower()
    # Exact match first
    for opt in options:
        if opt.lower() in lowered:
            return ParsedResponse(
                expected_format="categorical_choice",
                raw_text=text,
                parsed_value=opt,
                confidence=0.95,
            )
    # Fuzzy via SequenceMatcher
    best_opt: Optional[str] = None
    best_score = 0.0
    for opt in options:
        score = SequenceMatcher(None, lowered, opt.lower()).ratio()
        if score > best_score:
            best_score = score
            best_opt = opt
    if best_opt is not None and best_score >= 0.4:
        return ParsedResponse(
            expected_format="categorical_choice",
            raw_text=text,
            parsed_value=best_opt,
            confidence=float(best_score),
            notes=f"fuzzy match score {best_score:.2f}",
        )
    return ParsedResponse(
        expected_format="categorical_choice",
        raw_text=text,
        parsed_value=None,
        confidence=0.0,
        notes="no fuzzy match above threshold",
    )


# ---------------------------------------------------------------------------
# Public dispatch
# ---------------------------------------------------------------------------
_PARSERS = {
    "integer_seconds": _parse_integer_seconds,
    "integer_count": _parse_integer_count,
    "float_value": _parse_float_value,
    "boolean": _parse_boolean,
    "scale_0_5": _parse_scale_0_5,
}


def parse_response(
    raw: str,
    *,
    expected_format: str,
    options: Optional[list[str]] = None,
) -> ParsedResponse:
    """Dispatch to the per-format parser."""
    if not isinstance(raw, str):
        raw = str(raw)
    if expected_format == "categorical_choice":
        return _parse_categorical_choice(raw, options=options)
    parser = _PARSERS.get(expected_format)
    if parser is None:
        return ParsedResponse(
            expected_format=expected_format,
            raw_text=raw,
            parsed_value=None,
            confidence=0.0,
            notes=f"unknown expected_format {expected_format!r}",
        )
    return parser(raw)


__all__ = [
    "ParsedResponse",
    "parse_response",
]
