"""
text_extractor.py — Phase 5 Day 2 free-text entity extractor.

Sends a plain-text observation/note to Claude Sonnet 4.5 with a strict
JSON-output prompt that requests typed entities matching the Phase 5
schema (MedicationEntity / CalendarEntity / ContactEntity / TimelineEntity).

The text is run through the PHI redactor BEFORE the LLM call so no PHI
ever reaches Anthropic's servers — both a code-side discipline AND a
defense against prompt-injection variants that would otherwise smuggle
PHI back out via the LLM's response.

Cost model
----------
One sync ``call_claude`` per ``extract(...)``. Claude Sonnet 4.5 at
$3 / $15 per 1M tokens. A typical 200-word note × 4096 max output
tokens = ~$0.02 / call. Day 2 fixture set is sized to stay under $1.

Public surface
--------------
    extract(text, *, agent_id='manager.text_extractor') -> list[Entity]
"""

from __future__ import annotations

import json
import re
from typing import Any

from scripts.cognition.llm import call_claude
from scripts.manager.intake._shared import (
    CalendarEntity,
    ContactEntity,
    Entity,
    MedicationEntity,
    TimelineEntity,
    redact_or_block,
)


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = (
    "You are a medical-text entity extractor for ALEKSANDRA_BRAIN. "
    "Given a short free-text note from the family caregiver, you return "
    "ONLY a JSON object that conforms to the schema below. No prose, no "
    "Markdown fences, no commentary. If the note contains no medical or "
    'scheduling content, return {"entities": []}.\n\n'
    "Schema (every kind is optional; include only what the text supports):\n"
    "{\n"
    '  "entities": [\n'
    '    {"kind": "medication", "name": str, "dose": str|null, '
    '"frequency": str|null, "confidence": float},\n'
    '    {"kind": "calendar",   "title": str, "date": str|null, '
    '"time": str|null, "clinician": str|null, "location": str|null, '
    '"confidence": float},\n'
    '    {"kind": "contact",    "full_name": str, "role": str|null, '
    '"email": str|null, "institution": str|null, "confidence": float},\n'
    '    {"kind": "timeline",   "when": str, "note": str, '
    '"category": str|null, "confidence": float}\n'
    "  ]\n"
    "}\n\n"
    "Rules:\n"
    "- Dates: prefer ISO-8601 (YYYY-MM-DD). If only month/year, use "
    "YYYY-MM.\n"
    "- Confidences: 0.00-1.00. Reserve >=0.90 for unambiguous extractions; "
    "<=0.60 for guesses.\n"
    "- NEVER invent a medication, dose, or clinician name not present in "
    "the text. If unsure, omit the entity.\n"
    "- The note is PRE-REDACTED so patient identifiers are already "
    "stripped — treat any '[REDACTED:*]' tokens as opaque placeholders."
)


def _strip_code_fence(s: str) -> str:
    """Tolerate ```json fences even though the prompt forbids them."""
    s = s.strip()
    if s.startswith("```"):
        # drop the first fence line and trailing fence
        s = re.sub(r"^```(?:json)?\s*\n", "", s)
        s = re.sub(r"\n```\s*$", "", s)
    return s


def _coerce_entity(raw: dict[str, Any]) -> Entity | None:
    kind = raw.get("kind")
    try:
        if kind == "medication":
            return MedicationEntity(
                name=str(raw["name"]),
                dose=raw.get("dose"),
                frequency=raw.get("frequency"),
                confidence=float(raw.get("confidence", 0.0) or 0.0),
            )
        if kind == "calendar":
            return CalendarEntity(
                title=str(raw["title"]),
                date=raw.get("date"),
                time=raw.get("time"),
                clinician=raw.get("clinician"),
                location=raw.get("location"),
                confidence=float(raw.get("confidence", 0.0) or 0.0),
            )
        if kind == "contact":
            return ContactEntity(
                full_name=str(raw["full_name"]),
                role=raw.get("role"),
                email=raw.get("email"),
                institution=raw.get("institution"),
                confidence=float(raw.get("confidence", 0.0) or 0.0),
            )
        if kind == "timeline":
            return TimelineEntity(
                when=str(raw["when"]),
                note=str(raw["note"]),
                category=raw.get("category"),
                confidence=float(raw.get("confidence", 0.0) or 0.0),
            )
    except (KeyError, TypeError, ValueError):
        return None
    return None


def extract(text: str, *, agent_id: str = "manager.text_extractor") -> list[Entity]:
    """Run the full text → entity-list pipeline.

    Steps:
      1. redact_or_block — PHI redaction (raises if blocked)
      2. call_claude with the JSON-output prompt
      3. parse + coerce → list[Entity]

    Returns an empty list if the LLM produces an unparseable response;
    never raises on parse errors (the caller decides whether empty
    is acceptable).
    """
    redacted = redact_or_block(text)
    if not redacted.text.strip():
        return []

    raw = call_claude(
        prompt=redacted.text,
        agent_id=agent_id,
        system=_SYSTEM_PROMPT,
        max_tokens=2048,
        temperature=0.1,
    )

    body = _strip_code_fence(raw)
    try:
        obj = json.loads(body)
    except json.JSONDecodeError:
        return []

    items = obj.get("entities") if isinstance(obj, dict) else None
    if not isinstance(items, list):
        return []

    entities: list[Entity] = []
    for raw_item in items:
        if not isinstance(raw_item, dict):
            continue
        ent = _coerce_entity(raw_item)
        if ent is not None:
            entities.append(ent)
    return entities


__all__ = ["extract"]
