"""Voice note (Whisper transcript) -> BeliefEvidence adapter (Phase 7.0 Days 16-17).

Reads Phase 5 `intake_drops` rows where `input_type='voice'` and emits
BeliefEvidence for:

  - muscle_tone_hammersmith (Normal)      -> {"observations": [score]}
  - eye_tracking_seconds   (Gamma)        -> {"observations": [sec]}
  - head_control_seconds   (Normal)       -> {"observations": [sec]}
  - feeding_stage          (Categorical)  -> {"observations": [stage_idx]}

Voice notes are typically Georgian-language transcripts (the family is in
Boston but speaks Georgian). Parsing handles BOTH Georgian (KA) and
English (EN) numeric mentions. Real Whisper output usually emits Arabic
numerals even from Georgian speech, so the regexes target Arabic digits
adjacent to KA verb forms — e.g.:

  "Aleksandra held her head for 8 seconds"
  "ალექსანდრამ თვალი 5 წამი დაიჭირა"
  "she ate 3 spoonfuls of puree today"

Phase 5 schema (migration 011) note:
  intake_drops has a column `input_type` (NOT `source`) with the
  allowed values {'pdf','photo','voice','email','text'}. The DB stores
  'voice' but the BeliefEvidence enum (persistence.ALLOWED_EVIDENCE_SOURCES)
  uses 'voice_note'. The adapter maps the former to the latter automatically.

Hard rules from `.claude/agents/v7-bayes.md`:
  - NO PHI in logs (only field names + extraction status)
  - Idempotency via BeliefEvidence.evidence_hash
  - Failed extraction returns None + logger.warning; never raise
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Callable, Optional

from pydantic import BaseModel, ConfigDict

from brain.belief.persistence import (
    BeliefEvidence,
    compute_evidence_hash,
    get_dimension_by_name,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Row shape callers must hand in
# ---------------------------------------------------------------------------
class IntakeDropRow(BaseModel):
    """Caller-supplied Phase 5 `intake_drops` shape (subset).

    Field names mirror the migration 011 column names so callers can pass
    `dict(row)` from a `RealDictCursor` directly:
      id            : UUID primary key.
      input_type    : 'pdf'|'photo'|'voice'|'email'|'text' (CHECK constraint).
      raw_content   : redacted parsed text (≤100 kB per migration 011).
      created_at    : drives `BeliefEvidence.observed_at`.
      phi_redacted  : must be TRUE before write (CHECK enforces this DB-side).
    """

    model_config = ConfigDict(extra="ignore")  # allow extra cols from RealDictCursor

    id: str
    input_type: str
    raw_content: str
    created_at: datetime
    phi_redacted: bool = True


# ---------------------------------------------------------------------------
# Bilingual (EN + KA) extraction regexes
# ---------------------------------------------------------------------------
# Notes on Georgian patterns:
#   თვალი / თვალს   = "eye / eye(acc)"
#   თავი / თავს     = "head / head(acc)"
#   დაიჭირა         = "held / fixated"   (perfective, 3sg)
#   შეაჩერა         = "stopped (gaze) on" (perfective, 3sg)
#   აიყვანა         = "lifted up"
#   წამი            = "second(s)"
#   კოვზი           = "spoon(ful)"
#   შეჭამა          = "ate" (perfective)
# Whisper outputs Arabic digits even from Georgian speech.

# Eye tracking — EN: "eye contact for 8 seconds" / KA: "თვალი 5 წამი"
_EYE_TRACK_REGEX = re.compile(
    r"(?:"
    r"eye(?:s)?\s+(?:contact|track\w*|follow\w*|gaze|fixation)"
    r"|"
    r"(?:visual(?:ly)?\s+)?track\w*\s+(?:for|object|target)"
    r"|"
    r"თვალი\w*"
    r")"
    r"[^.0-9]{0,40}?(\d{1,3})\s*(?:sec(?:onds?)?|წამი|s\b)",
    re.IGNORECASE | re.UNICODE,
)

# Head control — EN: "held her head for 8 seconds" / KA: "თავი 10 წამი"
_HEAD_CONTROL_REGEX = re.compile(
    r"(?:"
    r"(?:held|holds|holding|keeping)\s+(?:her|his|the)?\s*head"
    r"|"
    r"head\s+(?:control|up|vertical|hold|holding)"
    r"|"
    r"თავი\w*"
    r")"
    r"[^.0-9]{0,40}?(\d{1,3})\s*(?:sec(?:onds?)?|წამი|s\b)",
    re.IGNORECASE | re.UNICODE,
)

# Hammersmith / HINE muscle-tone score — EN-only (clinical score is universally numeric)
_TONE_REGEX = re.compile(
    r"(?:Hammersmith(?:\s+score)?|HINE(?:\s+score)?|tone\s+score)"
    r"\s*[:=]?\s*(\d{1,3})",
    re.IGNORECASE,
)

# Feeding stage keyword classifier (0=NG, 1=partial-oral, 2=puree, 3=solid)
# Priority: NG > partial-oral > puree > solid (specific before generic).
_FEEDING_STAGE_KEYWORDS: dict[int, list[str]] = {
    0: [
        "ng tube",
        "ng-tube",
        "nasogastric",
        "g-tube",
        "g tube",
        "gastrostomy",
        "ნაზოგასტრალური",
        "ნაზოგასტრალურით",
    ],
    1: [
        "partial oral",
        "partial-oral",
        "few bites",
        "few spoonfuls",
        "tasted",
        "1 spoonful",
        "2 spoonful",
        "2 spoonfuls",
        "3 spoonful",
        "3 spoonfuls",
        "კოვზი",
        "ცოტა შეჭამა",
    ],
    2: [
        "pureed",
        "puree",
        "thicker textures",
        "ate puree",
        "ate pureed",
        "მოხარშული",
        "მოხარშულ",
    ],
    3: [
        "solid food",
        "solid foods",
        "table food",
        "full meal",
        "ate solid",
        "მყარი საკვები",
        "ate a full meal",
    ],
}


# ---------------------------------------------------------------------------
# Per-dimension extractors
# ---------------------------------------------------------------------------
def _make_numeric_evidence(
    drop: IntakeDropRow,
    dim_id: int,
    obs_value: float,
    confidence: float,
    *,
    extra_value_keys: Optional[dict[str, Any]] = None,
) -> BeliefEvidence:
    """Shared builder for numeric voice evidence (eye, head, tone)."""
    value: dict[str, Any] = {"observations": [obs_value]}
    if extra_value_keys:
        value.update(extra_value_keys)
    evidence_hash = compute_evidence_hash(
        dimension_id=dim_id,
        source="voice_note",
        source_ref=str(drop.id),
        value=value,
    )
    return BeliefEvidence(
        dimension_id=dim_id,
        source="voice_note",
        source_ref=str(drop.id),
        value=value,
        evidence_hash=evidence_hash,
        confidence=confidence,
        observed_at=drop.created_at,
    )


def extract_eye_tracking(drop: IntakeDropRow, dim_id: int) -> Optional[BeliefEvidence]:
    """Eye-tracking seconds -> Gamma evidence (observations strictly positive)."""
    match = _EYE_TRACK_REGEX.search(drop.raw_content)
    if not match:
        logger.warning(
            "eye_tracking_seconds extraction: no pattern match (intake_drop id=%s)",
            drop.id,
        )
        return None
    try:
        seconds = float(match.group(1))
    except (TypeError, ValueError):
        logger.warning(
            "eye_tracking_seconds extraction: non-numeric capture (intake_drop id=%s)",
            drop.id,
        )
        return None
    # Gamma likelihood requires strictly positive observations
    if seconds <= 0:
        logger.warning(
            "eye_tracking_seconds extraction: non-positive value=%.1f (intake_drop id=%s)",
            seconds,
            drop.id,
        )
        return None
    # confidence=0.85 — explicit numeric in transcript
    return _make_numeric_evidence(drop, dim_id, seconds, confidence=0.85)


def extract_head_control(drop: IntakeDropRow, dim_id: int) -> Optional[BeliefEvidence]:
    """Head-control seconds -> Normal evidence."""
    match = _HEAD_CONTROL_REGEX.search(drop.raw_content)
    if not match:
        logger.warning(
            "head_control_seconds extraction: no pattern match (intake_drop id=%s)",
            drop.id,
        )
        return None
    try:
        seconds = float(match.group(1))
    except (TypeError, ValueError):
        return None
    if seconds < 0:
        return None
    return _make_numeric_evidence(drop, dim_id, seconds, confidence=0.85)


def extract_muscle_tone(drop: IntakeDropRow, dim_id: int) -> Optional[BeliefEvidence]:
    """Hammersmith/HINE tone score -> Normal evidence."""
    match = _TONE_REGEX.search(drop.raw_content)
    if not match:
        logger.warning(
            "muscle_tone_hammersmith extraction: no pattern match (intake_drop id=%s)",
            drop.id,
        )
        return None
    try:
        score = float(match.group(1))
    except (TypeError, ValueError):
        return None
    if not (0 <= score <= 100):
        logger.warning(
            "muscle_tone_hammersmith extraction: out-of-range score=%.1f (intake_drop id=%s)",
            score,
            drop.id,
        )
        return None
    # confidence=0.85 — clinical score is explicit numeric
    return _make_numeric_evidence(drop, dim_id, score, confidence=0.85)


def extract_feeding_stage(drop: IntakeDropRow, dim_id: int) -> Optional[BeliefEvidence]:
    """Feeding-stage keyword classifier -> Categorical evidence (0-3)."""
    text = drop.raw_content.lower()
    matched_stage: Optional[int] = None
    # Priority order: 0 (NG) -> 1 (partial) -> 2 (puree) -> 3 (solid)
    for stage in (0, 1, 2, 3):
        for kw in _FEEDING_STAGE_KEYWORDS[stage]:
            if kw.lower() in text:
                matched_stage = stage
                break
        if matched_stage is not None:
            break
    if matched_stage is None:
        logger.warning(
            "feeding_stage extraction: no keyword match (intake_drop id=%s)",
            drop.id,
        )
        return None
    value: dict[str, Any] = {"observations": [matched_stage]}
    evidence_hash = compute_evidence_hash(
        dimension_id=dim_id,
        source="voice_note",
        source_ref=str(drop.id),
        value=value,
    )
    return BeliefEvidence(
        dimension_id=dim_id,
        source="voice_note",
        source_ref=str(drop.id),
        value=value,
        evidence_hash=evidence_hash,
        confidence=0.65,  # keyword-based classification
        observed_at=drop.created_at,
    )


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------
# Accept BOTH 'voice' (Phase 5 DB schema value, migration 011 CHECK) and
# 'voice_note' (BeliefEvidence.source enum value) for caller convenience —
# the test spec in the task brief uses 'voice_note', while the live DB
# stores 'voice'. Either is acceptable input.
_ACCEPTED_VOICE_INPUT_TYPES = frozenset({"voice", "voice_note"})


def adapt_voice_note(
    drop: IntakeDropRow,
    *,
    dimension_loader: Optional[Callable[[str], Any]] = None,
) -> list[BeliefEvidence]:
    """Run all 4 voice extractors and return successful BeliefEvidence rows.

    Parameters
    ----------
    drop : IntakeDropRow
        Caller-supplied Phase 5 intake_drops row. Must have
        `input_type in {'voice', 'voice_note'}` — other types short-circuit
        to an empty list with a warning.
    dimension_loader : optional callable name -> BeliefDimension|None
        Injectable for tests so they don't hit the live DB. Defaults to
        `persistence.get_dimension_by_name`.

    Returns
    -------
    list[BeliefEvidence]
        Zero to four evidence rows depending on which extractors succeeded.
        Order: eye, head, tone, feeding.
    """
    if drop.input_type not in _ACCEPTED_VOICE_INPUT_TYPES:
        logger.warning(
            "voice adapter called on non-voice drop (input_type=%s, intake_drop id=%s)",
            drop.input_type,
            drop.id,
        )
        return []
    loader = dimension_loader or get_dimension_by_name
    evidences: list[BeliefEvidence] = []

    extractors: list[
        tuple[str, Callable[[IntakeDropRow, int], Optional[BeliefEvidence]]]
    ] = [
        ("eye_tracking_seconds", extract_eye_tracking),
        ("head_control_seconds", extract_head_control),
        ("muscle_tone_hammersmith", extract_muscle_tone),
        ("feeding_stage", extract_feeding_stage),
    ]

    for dim_name, extractor in extractors:
        dim = loader(dim_name)
        if dim is None or getattr(dim, "id", None) is None:
            logger.warning(
                "dimension %s not in catalog; skipping (intake_drop id=%s)",
                dim_name,
                drop.id,
            )
            continue
        ev = extractor(drop, dim.id)
        if ev is not None:
            evidences.append(ev)

    return evidences


__all__ = [
    "IntakeDropRow",
    "extract_eye_tracking",
    "extract_head_control",
    "extract_muscle_tone",
    "extract_feeding_stage",
    "adapt_voice_note",
]
