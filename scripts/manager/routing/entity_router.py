"""
entity_router.py — Phase 5 Day 4 entity → target-table router.

Given a list of Entity objects from any of the intake parsers, decide
which Supabase table each one belongs in and what the before/after
payload should look like.

Routing rules
-------------
- MedicationEntity → therapies (match by name fuzzy ≥ 0.6; create if no
  match). Updates ALWAYS preview, never auto-execute (Day 4 hard rule).
- CalendarEntity   → aleksandra_timeline (event_type='appointment').
  Auto-execute when confidence ≥ 0.9.
- ContactEntity    → contacts (match by full_name OR email). Preview
  required.
- TimelineEntity   → aleksandra_timeline (event_type=category or
  'observation'). Auto-execute when confidence ≥ 0.9.

All Postgres reads happen with a single connection per route call; no
N+1 query per entity. Therapies are loaded once at the top of the call.

Public surface
--------------
    route_entities(entities, *, intake_drop_id=None,
                   manager_user_id=None) -> list[ProposedAction]
"""

from __future__ import annotations

import os
from typing import Any

import psycopg2

from scripts.ledger import load_env
from scripts.manager.intake._shared import (
    CalendarEntity,
    ContactEntity,
    Entity,
    MedicationEntity,
    TimelineEntity,
)
from scripts.manager.routing._shared import (
    ProposedAction,
    decide_auto_execute,
    fuzzy_best_match,
)


def _open() -> psycopg2.extensions.connection:
    load_env()
    return psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")


def _load_therapy_catalog(
    cur: psycopg2.extensions.cursor,
) -> list[tuple[str, str, list[str]]]:
    cur.execute("SELECT id, name, COALESCE(name_aliases, '{}'::text[]) FROM therapies")
    return [(str(r[0]), r[1] or "", list(r[2] or [])) for r in cur.fetchall()]


def _load_therapy_row(
    cur: psycopg2.extensions.cursor, therapy_id: str
) -> dict[str, Any] | None:
    cur.execute(
        """
        SELECT id, name, name_aliases, therapy_type, mechanism_of_action,
               evidence_in_hie, evidence_summary, clinical_status,
               aleksandra_eligible, aleksandra_status, aleksandra_notes
        FROM therapies WHERE id = %s
        """,
        (therapy_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    cols = [
        "id",
        "name",
        "name_aliases",
        "therapy_type",
        "mechanism_of_action",
        "evidence_in_hie",
        "evidence_summary",
        "clinical_status",
        "aleksandra_eligible",
        "aleksandra_status",
        "aleksandra_notes",
    ]
    return {c: (str(v) if c == "id" else v) for c, v in zip(cols, row)}


def _load_contact_catalog(
    cur: psycopg2.extensions.cursor,
) -> list[tuple[str, str, list[str]]]:
    cur.execute("SELECT id, COALESCE(full_name,''), COALESCE(email,'') FROM contacts")
    out: list[tuple[str, str, list[str]]] = []
    for rid, name, email in cur.fetchall():
        aliases: list[str] = []
        if email:
            aliases.append(email)
        out.append((str(rid), name, aliases))
    return out


# ---------------------------------------------------------------------------
# Per-entity routers
# ---------------------------------------------------------------------------
def _route_medication(
    e: MedicationEntity, cur: psycopg2.extensions.cursor
) -> ProposedAction:
    catalog = _load_therapy_catalog(cur)
    hit = fuzzy_best_match(e.name, catalog, threshold=0.6)
    if hit is None:
        # CREATE — bring a new therapy in as 'evaluating' so Shako reviews.
        after = {
            "name": e.name,
            "therapy_type": None,
            "aleksandra_status": "evaluating",
            "evidence_in_hie": "unknown",
            "aleksandra_notes": (
                f"Imported from Phase 5 intake (drop). "
                f"Dose hint: {e.dose}; frequency: {e.frequency}."
            ),
        }
        conf = min(e.confidence, 0.7)
        auto, warns = decide_auto_execute(
            target_table="therapies",
            after_payload=after,
            before_payload=None,
            confidence=conf,
            source_entity_kind="medication",
        )
        return ProposedAction(
            action_type="create",
            target_table="therapies",
            target_record_id=None,
            before_payload=None,
            after_payload=after,
            confidence=conf,
            auto_execute=auto,
            rationale=f"No therapy match for {e.name!r} (best fuzzy < 0.6). Propose create.",
            source_entity_kind="medication",
            warnings=warns,
        )

    therapy_id, score = hit
    before = _load_therapy_row(cur, therapy_id) or {}
    # We DO NOT change name or dose — only update aleksandra_notes to
    # record the new observation. Dose changes stay manual per trust policy.
    appended_note = (
        f"Phase 5 intake observation: dose={e.dose}, freq={e.frequency}, "
        f"confidence={e.confidence:.2f}."
    )
    existing_notes = (before.get("aleksandra_notes") or "").strip()
    after_notes = (
        f"{existing_notes}\n{appended_note}".strip()
        if existing_notes
        else appended_note
    )
    after = {**before, "aleksandra_notes": after_notes}
    conf = min(e.confidence, score)
    auto, warns = decide_auto_execute(
        target_table="therapies",
        after_payload=after,
        before_payload=before,
        confidence=conf,
        source_entity_kind="medication",
    )
    return ProposedAction(
        action_type="update",
        target_table="therapies",
        target_record_id=therapy_id,
        before_payload=before,
        after_payload=after,
        confidence=conf,
        auto_execute=auto,
        rationale=(
            f"Fuzzy match {score:.2f} on therapy {before.get('name', '?')!r}. "
            "Note appended; dose/name NOT changed."
        ),
        source_entity_kind="medication",
        warnings=warns,
    )


def _route_calendar(
    e: CalendarEntity, cur: psycopg2.extensions.cursor
) -> ProposedAction:
    after = {
        "event_date": e.date,
        "event_type": "appointment",
        "title": e.title,
        "description": e.clinician or e.location,
        "institution": e.location,
    }
    auto, warns = decide_auto_execute(
        target_table="aleksandra_timeline",
        after_payload=after,
        before_payload=None,
        confidence=e.confidence,
        source_entity_kind="calendar",
    )
    return ProposedAction(
        action_type="add_event",
        target_table="aleksandra_timeline",
        target_record_id=None,
        before_payload=None,
        after_payload=after,
        confidence=e.confidence,
        auto_execute=auto,
        rationale=f"Calendar entry → aleksandra_timeline. date={e.date}",
        source_entity_kind="calendar",
        warnings=warns,
    )


def _route_contact(e: ContactEntity, cur: psycopg2.extensions.cursor) -> ProposedAction:
    catalog = _load_contact_catalog(cur)
    needle = e.email or e.full_name
    hit = fuzzy_best_match(needle, catalog, threshold=0.75)
    if hit is None:
        after = {
            "full_name": e.full_name,
            "email": e.email,
            "contact_type": e.role or "researcher",
            "institution": e.institution,
        }
        auto, warns = decide_auto_execute(
            target_table="contacts",
            after_payload=after,
            before_payload=None,
            confidence=e.confidence,
            source_entity_kind="contact",
        )
        return ProposedAction(
            action_type="add_contact",
            target_table="contacts",
            target_record_id=None,
            before_payload=None,
            after_payload=after,
            confidence=e.confidence,
            auto_execute=auto,
            rationale=f"No contact match for {needle!r}; propose add.",
            source_entity_kind="contact",
            warnings=warns,
        )
    cid, score = hit
    after = {"full_name": e.full_name, "email": e.email}
    auto, warns = decide_auto_execute(
        target_table="contacts",
        after_payload=after,
        before_payload={"id": cid},
        confidence=min(e.confidence, score),
        source_entity_kind="contact",
    )
    return ProposedAction(
        action_type="update",
        target_table="contacts",
        target_record_id=cid,
        before_payload={"id": cid},
        after_payload=after,
        confidence=min(e.confidence, score),
        auto_execute=auto,
        rationale=f"Fuzzy contact match {score:.2f}. Propose enrich.",
        source_entity_kind="contact",
        warnings=warns,
    )


def _route_timeline(
    e: TimelineEntity, cur: psycopg2.extensions.cursor
) -> ProposedAction:
    after = {
        "event_date": e.when,
        "event_type": e.category or "observation",
        "title": e.note[:80],
        "description": e.note,
    }
    auto, warns = decide_auto_execute(
        target_table="aleksandra_timeline",
        after_payload=after,
        before_payload=None,
        confidence=e.confidence,
        source_entity_kind="timeline",
    )
    return ProposedAction(
        action_type="add_milestone",
        target_table="aleksandra_timeline",
        target_record_id=None,
        before_payload=None,
        after_payload=after,
        confidence=e.confidence,
        auto_execute=auto,
        rationale="Timeline observation → aleksandra_timeline.",
        source_entity_kind="timeline",
        warnings=warns,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def route_entities(
    entities: list[Entity],
    *,
    intake_drop_id: str | None = None,
    manager_user_id: str | None = None,
) -> list[ProposedAction]:
    """Map entities → list of ProposedAction. Single Postgres connection."""
    _ = manager_user_id  # reserved for per-operator catalog scoping
    if not entities:
        return []
    out: list[ProposedAction] = []
    conn = _open()
    try:
        with conn.cursor() as cur:
            for ent in entities:
                if isinstance(ent, MedicationEntity):
                    pa = _route_medication(ent, cur)
                elif isinstance(ent, CalendarEntity):
                    pa = _route_calendar(ent, cur)
                elif isinstance(ent, ContactEntity):
                    pa = _route_contact(ent, cur)
                elif isinstance(ent, TimelineEntity):
                    pa = _route_timeline(ent, cur)
                else:
                    # PHIBlock or unknown — nothing to route.
                    continue
                pa.intake_drop_id = intake_drop_id
                out.append(pa)
    finally:
        conn.close()
    return out


__all__ = ["route_entities"]
