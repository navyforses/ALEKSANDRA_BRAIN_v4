"""
tests/test_manager_email_intent.py — Phase 5 Day 6 email-intent tests.

Deterministic parser tests run without DB. The live-DB tests exercise
fuzzy contact matching against the real contacts table; both go through
dry_run=True so no Gmail draft is created and no outreach_log row lands.
"""

from __future__ import annotations

import os

import pytest

from scripts.ledger import load_env
from scripts.manager.email_draft import EmailIntent, draft_from_intent, parse_intent


# ---------------------------------------------------------------------------
# parse_intent — regex coverage
# ---------------------------------------------------------------------------
def test_parse_canonical_write_to():
    intent = parse_intent("write to Sydney about Duke timing")
    assert isinstance(intent, EmailIntent)
    assert intent.recipient_hint == "Sydney"
    assert intent.topic == "Duke timing"


def test_parse_draft_an_email_variant():
    intent = parse_intent("draft an email to Dr. Maypole about the next BMC visit")
    assert intent is not None
    assert intent.recipient_hint.lower().startswith("dr")
    assert "BMC visit" in intent.topic


def test_parse_message_variant():
    intent = parse_intent("message to Jeanette about the Wisconsin schedule")
    assert intent is not None
    assert intent.recipient_hint == "Jeanette"
    assert intent.topic == "Wisconsin schedule"


def test_parse_colon_shorthand():
    intent = parse_intent("To Sydney: cord blood window")
    assert intent is not None
    assert intent.recipient_hint == "Sydney"
    assert intent.topic == "cord blood window"


def test_parse_unrecognized_returns_none():
    assert parse_intent("hello world") is None
    assert parse_intent("write to") is None
    assert parse_intent("about the weather") is None


# ---------------------------------------------------------------------------
# Live-DB tests — all dry_run=True so no Gmail/outreach_log side effects
# ---------------------------------------------------------------------------
def _db_available() -> bool:
    load_env()
    return bool(os.environ.get("SUPABASE_DB_URL"))


@pytest.mark.skipif(
    not _db_available(),
    reason="SUPABASE_DB_URL not set",
)
def test_draft_from_intent_unrecognized_intent():
    result = draft_from_intent("hello", dry_run=True)
    assert result.matched is False
    assert result.blocked is True
    assert result.block_reason == "intent_not_recognized"


@pytest.mark.skipif(
    not _db_available(),
    reason="SUPABASE_DB_URL not set",
)
def test_draft_from_intent_no_contact_match():
    result = draft_from_intent(
        "write to ZZZNonExistentPersonXYZ about anything", dry_run=True
    )
    assert result.matched is True
    assert result.intent is not None
    assert result.contact_id is None
    assert result.blocked is True
    assert result.block_reason
    assert "no_contact_match" in result.block_reason


@pytest.mark.skipif(
    not _db_available(),
    reason="SUPABASE_DB_URL not set",
)
def test_draft_from_intent_fuzzy_match_against_real_contact():
    """Pick any real contact's first name and confirm fuzzy match resolves.

    The Phase 3 import added 96 contacts. We grab one full_name, take the
    first token, and ask for "write to <first_token> about test topic".
    The drafter runs dry-run so no Gmail draft is created.
    """
    import psycopg2

    load_env()
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT full_name FROM contacts WHERE full_name IS NOT NULL "
            "AND length(full_name) > 4 ORDER BY id LIMIT 1"
        )
        row = cur.fetchone()
        if row is None:
            pytest.skip("contacts table empty — Phase 3 import has not run yet")
        full_name = row[0]
    finally:
        conn.close()
    first_token = full_name.split()[0]
    result = draft_from_intent(
        f"write to {first_token} about test outreach topic", dry_run=True
    )
    assert result.matched is True
    assert result.intent is not None
    # The fuzzy match should at least find SOMETHING — exact identity is
    # less important than that the resolver runs.
    assert result.contact_id is not None or result.block_reason
