"""
scripts.manager.routing._shared — Phase 5 Day 4 ProposedAction + helpers.

Trust boundaries enforced
-------------------------
1. ``auto_execute`` is False whenever the action touches a medication
   dose or drug name — those decisions stay with the operator regardless
   of confidence (Phase 5 plan §"Day 4" hard rule).

2. The only ``target_table`` values this router emits are the ones
   listed in ``ALLOWED_TARGET_TABLES``. A typo in the entity router
   that proposed writes to, say, ``runs`` would be rejected before
   the SQL ever ran.

3. ``ProposedAction.confidence`` is the minimum of the entity's own
   extraction confidence and the routing confidence (e.g. fuzzy-match
   score against the therapies catalog). The UI uses this scalar to
   gray out low-confidence cards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Literal

# Tables the entity router is permitted to propose writes against.
# Anything else (runs, manager_actions, intake_drops itself, etc.) is
# refused by apply_action.
ALLOWED_TARGET_TABLES: frozenset[str] = frozenset(
    {"aleksandra_timeline", "therapies", "contacts", "hypotheses", "kv_state"}
)

ActionType = Literal[
    "create",
    "update",
    "add_event",
    "add_milestone",
    "add_contact",
    "log_pattern",
]


@dataclass
class ProposedAction:
    """A single change the entity router suggests applying.

    Always ships with both the proposed after_payload and (when the
    action is an update) the pre-image snapshot fetched from the live
    target_record_id. That pre-image is what the undo path replays.
    """

    action_type: ActionType
    target_table: str
    target_record_id: str | None  # uuid string for update; None for create
    before_payload: dict[str, Any] | None
    after_payload: dict[str, Any]
    confidence: float
    auto_execute: bool
    rationale: str
    source_entity_kind: str  # 'medication' | 'calendar' | 'contact' | 'timeline'
    intake_drop_id: str | None = None
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Fuzzy-match helper — used by the entity router for therapy + contact
# matching. Pure stdlib; no Qdrant/Neo4j dependency for the deterministic
# path. Qdrant kicks in only when fuzzy returns no hit AND the operator
# explicitly enables embedding-match (Day 4 ships the fuzzy path; Qdrant
# is an enhancement for a later phase).
# ---------------------------------------------------------------------------
def fuzzy_best_match(
    needle: str,
    candidates: list[tuple[str, str, list[str]]],
    *,
    threshold: float = 0.6,
) -> tuple[str, float] | None:
    """Return (record_id, score) of the best match above threshold.

    Each candidate is (record_id, canonical_name, [aliases]).
    """
    needle_low = needle.strip().lower()
    if not needle_low:
        return None
    best: tuple[str, float] | None = None
    for rid, canonical, aliases in candidates:
        names = [canonical, *aliases]
        for n in names:
            if not n:
                continue
            score = SequenceMatcher(a=needle_low, b=n.lower()).ratio()
            if score >= threshold and (best is None or score > best[1]):
                best = (rid, score)
    return best


# ---------------------------------------------------------------------------
# Confirmation tier — Phase 5 plan §"Day 4" trust-boundary policy.
# ---------------------------------------------------------------------------
def decide_auto_execute(
    *,
    target_table: str,
    after_payload: dict[str, Any],
    before_payload: dict[str, Any] | None,
    confidence: float,
    source_entity_kind: str,
) -> tuple[bool, list[str]]:
    """Return (auto_execute, warnings).

    Rules (in order, first-match wins):
      1. confidence < 0.9 → NEVER auto
      2. action touches medication dose or drug name → NEVER auto
      3. target is contacts/hypotheses → preview required (never auto)
      4. target is aleksandra_timeline AND source is calendar/timeline
         AND confidence ≥ 0.9 → auto
      5. default → preview required
    """
    warnings: list[str] = []
    if confidence < 0.9:
        return False, warnings

    # Medication-dose / drug-name guard.
    if target_table == "therapies":
        # Any change to name or dose is operator-only.
        dose_changed = (
            before_payload is not None
            and ("dose" in after_payload or "approximate_cost" in after_payload)
            and after_payload.get("dose") != (before_payload or {}).get("dose")
        )
        name_changed = (
            before_payload is not None
            and "name" in after_payload
            and after_payload.get("name") != (before_payload or {}).get("name")
        )
        if dose_changed or name_changed:
            warnings.append(
                "medication dose/name change requires explicit operator approval"
            )
            return False, warnings
        # Even a non-dose therapy edit is preview-only.
        return False, warnings

    if target_table in {"contacts", "hypotheses", "kv_state"}:
        return False, warnings

    if target_table == "aleksandra_timeline" and source_entity_kind in {
        "calendar",
        "timeline",
    }:
        return True, warnings

    return False, warnings


__all__ = [
    "ALLOWED_TARGET_TABLES",
    "ActionType",
    "ProposedAction",
    "decide_auto_execute",
    "fuzzy_best_match",
]
