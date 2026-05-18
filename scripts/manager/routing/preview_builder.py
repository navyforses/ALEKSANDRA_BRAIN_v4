"""
preview_builder.py — Phase 5 Day 4 ActionCard payload builder.

Translates a list of ProposedAction into UI-ready dictionaries. Adds:

  - per-action field-level diff (before -> after) for the UI to render
    Linear-style side-by-side rows
  - human-readable summary strings ("Append note to Vigabatrin",
    "Add appointment 2026-06-03 at BMC", …)
  - normalized confidence band ('high'/'medium'/'low') for the visual
    treatment

The output is the exact JSON the BRAIN panel POSTs back when the
operator clicks "Apply selected".

Public surface
--------------
    build_cards(actions) -> list[ActionCardPayload]
"""

from __future__ import annotations

from typing import Any

from scripts.manager.routing._shared import ProposedAction


def _band(score: float) -> str:
    if score >= 0.9:
        return "high"
    if score >= 0.7:
        return "medium"
    return "low"


def _diff_payloads(
    before: dict[str, Any] | None, after: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return [{field, before, after, changed}] for each key in `after`."""
    before = before or {}
    rows: list[dict[str, Any]] = []
    for key in sorted(after.keys()):
        b = before.get(key)
        a = after.get(key)
        rows.append(
            {
                "field": key,
                "before": b,
                "after": a,
                "changed": (b != a),
            }
        )
    return rows


def _summary(action: ProposedAction) -> str:
    at = action.action_type
    tbl = action.target_table
    if at == "add_event" and tbl == "aleksandra_timeline":
        title = action.after_payload.get("title", "appointment")
        date = action.after_payload.get("event_date", "?")
        return f"Add appointment '{title}' on {date}"
    if at == "add_milestone" and tbl == "aleksandra_timeline":
        title = action.after_payload.get("title", "observation")
        return f"Log observation '{title}'"
    if at == "create" and tbl == "therapies":
        return f"New therapy candidate: {action.after_payload.get('name', '?')}"
    if at == "update" and tbl == "therapies":
        return f"Append note to therapy {action.after_payload.get('name', '?')}"
    if at == "add_contact":
        return f"Add contact {action.after_payload.get('full_name', '?')}"
    if at == "update" and tbl == "contacts":
        return f"Update contact ({action.after_payload.get('email') or 'name'})"
    if at == "log_pattern":
        return "Log a longitudinal pattern observation"
    return f"{at} on {tbl}"


def build_cards(actions: list[ProposedAction]) -> list[dict[str, Any]]:
    """Translate each ProposedAction into a UI-friendly dict."""
    cards: list[dict[str, Any]] = []
    for i, a in enumerate(actions):
        cards.append(
            {
                "id": f"proposed-{i}",
                "summary": _summary(a),
                "action_type": a.action_type,
                "target_table": a.target_table,
                "target_record_id": a.target_record_id,
                "source_entity_kind": a.source_entity_kind,
                "confidence": round(a.confidence, 3),
                "confidence_band": _band(a.confidence),
                "auto_execute": a.auto_execute,
                "rationale": a.rationale,
                "diff": _diff_payloads(a.before_payload, a.after_payload),
                "warnings": list(a.warnings),
                "intake_drop_id": a.intake_drop_id,
                # The full payloads ride along so the apply route can
                # reconstruct the ProposedAction without re-running the
                # router. The UI never displays these directly.
                "_before_payload": a.before_payload,
                "_after_payload": a.after_payload,
            }
        )
    return cards


def card_to_action(card: dict[str, Any]) -> ProposedAction:
    """Reverse of build_cards — used by apply route after the operator picks."""
    return ProposedAction(
        action_type=card["action_type"],
        target_table=card["target_table"],
        target_record_id=card.get("target_record_id"),
        before_payload=card.get("_before_payload"),
        after_payload=card["_after_payload"],
        confidence=float(card.get("confidence", 0.0)),
        auto_execute=bool(card.get("auto_execute", False)),
        rationale=card.get("rationale", ""),
        source_entity_kind=card.get("source_entity_kind", "unknown"),
        intake_drop_id=card.get("intake_drop_id"),
        warnings=list(card.get("warnings", [])),
    )


__all__ = ["build_cards", "card_to_action"]
