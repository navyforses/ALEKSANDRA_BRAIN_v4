"""
tests/test_routing_entity_router.py — Phase 5 Day 4 entity-router tests.

Mostly deterministic unit tests on pure-Python paths (no LLM, no DB):

  - fuzzy_best_match returns best match above threshold
  - decide_auto_execute respects the trust-boundary rules
  - card builder + reverse round-trips the ProposedAction shape

A single live-DB smoke test exercises the calendar router with a
synthetic CalendarEntity. It is SKIPPED if SUPABASE_DB_URL is unset.
"""

from __future__ import annotations

import os

import pytest

from scripts.ledger import load_env
from scripts.manager.intake._shared import (
    CalendarEntity,
    ContactEntity,
    MedicationEntity,
    TimelineEntity,
)
from scripts.manager.routing._shared import (
    ALLOWED_TARGET_TABLES,
    ProposedAction,
    decide_auto_execute,
    fuzzy_best_match,
)
from scripts.manager.routing.preview_builder import build_cards, card_to_action


def _db_available() -> bool:
    load_env()
    return bool(os.environ.get("SUPABASE_DB_URL"))


# ---------------------------------------------------------------------------
# fuzzy_best_match
# ---------------------------------------------------------------------------
def test_fuzzy_best_match_hits_canonical_name():
    candidates = [
        ("u1", "Vigabatrin", ["VGB"]),
        ("u2", "Erythropoietin", ["EPO", "Procrit"]),
    ]
    hit = fuzzy_best_match("vigabatrin", candidates)
    assert hit is not None
    assert hit[0] == "u1"
    assert hit[1] >= 0.6


def test_fuzzy_best_match_hits_alias():
    candidates = [("u1", "Erythropoietin", ["EPO", "Procrit"])]
    hit = fuzzy_best_match("Procrit", candidates)
    assert hit is not None
    assert hit[0] == "u1"


def test_fuzzy_best_match_misses_when_below_threshold():
    candidates = [("u1", "Cord Blood Infusion", [])]
    assert fuzzy_best_match("aspirin", candidates, threshold=0.8) is None


# ---------------------------------------------------------------------------
# decide_auto_execute — trust-boundary tier
# ---------------------------------------------------------------------------
def test_low_confidence_blocks_auto():
    ok, _ = decide_auto_execute(
        target_table="aleksandra_timeline",
        after_payload={"event_date": "2026-06-01"},
        before_payload=None,
        confidence=0.85,
        source_entity_kind="calendar",
    )
    assert ok is False


def test_calendar_entity_auto_executes_at_high_confidence():
    ok, _ = decide_auto_execute(
        target_table="aleksandra_timeline",
        after_payload={"event_date": "2026-06-01", "event_type": "appointment"},
        before_payload=None,
        confidence=0.95,
        source_entity_kind="calendar",
    )
    assert ok is True


def test_medication_dose_change_never_auto():
    ok, warns = decide_auto_execute(
        target_table="therapies",
        after_payload={"dose": "60 mg"},
        before_payload={"dose": "50 mg"},
        confidence=0.99,
        source_entity_kind="medication",
    )
    assert ok is False
    assert any("dose" in w.lower() for w in warns)


def test_drug_name_change_never_auto():
    ok, warns = decide_auto_execute(
        target_table="therapies",
        after_payload={"name": "Vigabatrin XR"},
        before_payload={"name": "Vigabatrin"},
        confidence=0.99,
        source_entity_kind="medication",
    )
    assert ok is False
    assert warns  # at least one warning


def test_contact_update_never_auto():
    ok, _ = decide_auto_execute(
        target_table="contacts",
        after_payload={"email": "x@y"},
        before_payload={"email": None},
        confidence=0.99,
        source_entity_kind="contact",
    )
    assert ok is False


# ---------------------------------------------------------------------------
# Card builder round-trip
# ---------------------------------------------------------------------------
def test_card_round_trip_preserves_action():
    a = ProposedAction(
        action_type="add_event",
        target_table="aleksandra_timeline",
        target_record_id=None,
        before_payload=None,
        after_payload={"event_date": "2026-06-03", "title": "BMC follow-up"},
        confidence=0.92,
        auto_execute=True,
        rationale="cal entity",
        source_entity_kind="calendar",
    )
    cards = build_cards([a])
    assert len(cards) == 1
    card = cards[0]
    assert card["confidence_band"] == "high"
    assert any(
        d["field"] == "title" and d["after"] == "BMC follow-up" for d in card["diff"]
    )
    # Reverse round-trip — apply route uses this path
    back = card_to_action(card)
    assert back.action_type == a.action_type
    assert back.target_table == a.target_table
    assert back.after_payload == a.after_payload


def test_card_confidence_band_low_threshold():
    a = ProposedAction(
        action_type="create",
        target_table="therapies",
        target_record_id=None,
        before_payload=None,
        after_payload={"name": "x"},
        confidence=0.55,
        auto_execute=False,
        rationale="r",
        source_entity_kind="medication",
    )
    cards = build_cards([a])
    assert cards[0]["confidence_band"] == "low"


# ---------------------------------------------------------------------------
# Allow-list sanity
# ---------------------------------------------------------------------------
def test_allowed_target_tables_is_locked_down():
    # Anything that holds PHI or that the family does NOT routinely
    # mutate (runs, alerts_log, briefs) must NOT be in the allow list.
    forbidden = {"runs", "alerts_log", "briefs", "manager_actions", "intake_drops"}
    assert forbidden.isdisjoint(ALLOWED_TARGET_TABLES)


# ---------------------------------------------------------------------------
# Live-DB smoke (transactional, rolled back). Skipped if env missing.
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    not _db_available(),
    reason="SUPABASE_DB_URL not set",
)
def test_route_calendar_entity_against_live_db():
    from scripts.manager.routing.entity_router import route_entities

    e = CalendarEntity(
        title="BMC neurology check",
        date="2026-06-15",
        clinician="Dr. Hien",
        location="Boston Medical Center",
        confidence=0.93,
    )
    actions = route_entities([e])
    assert len(actions) == 1
    pa = actions[0]
    assert pa.target_table == "aleksandra_timeline"
    assert pa.action_type == "add_event"
    assert pa.auto_execute is True
    assert pa.after_payload.get("event_date") == "2026-06-15"


@pytest.mark.skipif(
    not _db_available(),
    reason="SUPABASE_DB_URL not set",
)
def test_route_timeline_entity_against_live_db():
    from scripts.manager.routing.entity_router import route_entities

    e = TimelineEntity(
        when="2026-05-17",
        note="Weight measured 7.2 kg",
        category="observation",
        confidence=0.91,
    )
    actions = route_entities([e])
    assert len(actions) == 1
    pa = actions[0]
    assert pa.target_table == "aleksandra_timeline"
    assert pa.auto_execute is True


@pytest.mark.skipif(
    not _db_available(),
    reason="SUPABASE_DB_URL not set",
)
def test_route_medication_never_auto_even_when_no_match():
    from scripts.manager.routing.entity_router import route_entities

    e = MedicationEntity(
        name="ZZZTotallyMadeUpDrug123",
        dose="10 mg",
        frequency="BID",
        confidence=0.98,
    )
    actions = route_entities([e])
    assert len(actions) == 1
    pa = actions[0]
    assert pa.target_table == "therapies"
    assert pa.auto_execute is False


@pytest.mark.skipif(
    not _db_available(),
    reason="SUPABASE_DB_URL not set",
)
def test_route_contact_never_auto():
    from scripts.manager.routing.entity_router import route_entities

    e = ContactEntity(
        full_name="Brand New Person",
        email="brandnew@example.org",
        role="researcher",
        confidence=0.95,
    )
    actions = route_entities([e])
    assert len(actions) == 1
    assert actions[0].auto_execute is False
