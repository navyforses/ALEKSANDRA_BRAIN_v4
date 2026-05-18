"""
tests/test_manager_briefing.py — Phase 5 Day 6 morning briefing tests.

Pure-Python composition tests run without DB or Telegram. The single
live-DB smoke test uses dry_run=True so nothing is sent and no audit
rows are written.
"""

from __future__ import annotations

import os

import pytest

from scripts.ledger import load_env
from scripts.manager.briefing import (
    WORD_CAP,
    BriefMessage,
    compose,
)


# ---------------------------------------------------------------------------
# compose() — deterministic word-cap behavior
# ---------------------------------------------------------------------------
def test_compose_with_full_data():
    msg = compose(
        today_events=[
            {
                "event_date": "2026-05-24",
                "event_type": "appointment",
                "title": "BMC neurology",
                "institution": "BMC",
            },
        ],
        last_24h_evidence_count=3,
        top_therapy="Vigabatrin",
        pending_outreach_count=2,
    )
    assert isinstance(msg, BriefMessage)
    assert msg.word_count <= WORD_CAP
    assert len(msg.bullets) == 3
    assert "BMC neurology" in msg.text
    assert "Vigabatrin" in msg.text
    assert "2 drafts" in msg.text


def test_compose_quiet_morning():
    msg = compose(
        today_events=[],
        last_24h_evidence_count=0,
        top_therapy=None,
        pending_outreach_count=0,
    )
    assert msg.word_count <= WORD_CAP
    assert "no appointments" in msg.text.lower()
    assert "quiet last 24h" in msg.text
    assert "inbox clear" in msg.text


def test_compose_truncates_when_over_50_words():
    """Long appointment title still produces a <=50w message."""
    long_title = " ".join(["very-long-appointment-title"] * 20)
    msg = compose(
        today_events=[
            {
                "event_date": "2026-05-24",
                "event_type": "appointment",
                "title": long_title,
                "institution": "BMC",
            },
        ],
        last_24h_evidence_count=99,
        top_therapy="something with a long name",
        pending_outreach_count=12,
    )
    assert msg.word_count <= WORD_CAP


def test_compose_singular_vs_plural_drafts():
    one = compose(
        today_events=[],
        last_24h_evidence_count=0,
        top_therapy=None,
        pending_outreach_count=1,
    )
    assert "1 draft awaiting" in one.text  # singular
    two = compose(
        today_events=[],
        last_24h_evidence_count=0,
        top_therapy=None,
        pending_outreach_count=2,
    )
    assert "2 drafts awaiting" in two.text


def test_word_cap_constant_documented():
    assert WORD_CAP == 50


# ---------------------------------------------------------------------------
# dry-run live-DB smoke — never sends Telegram, never writes briefs row
# ---------------------------------------------------------------------------
def _db_available() -> bool:
    load_env()
    return bool(os.environ.get("SUPABASE_DB_URL"))


@pytest.mark.skipif(
    not _db_available(),
    reason="SUPABASE_DB_URL not set",
)
def test_run_dry_run_smoke():
    from scripts.manager.briefing import run

    result = run(dry_run=True)
    assert result["dry_run"] is True
    assert result["telegram_message_id"] is None
    assert result["briefs_id"] is None
    assert isinstance(result["bullets"], list) and len(result["bullets"]) == 3
    assert result["word_count"] <= WORD_CAP
    assert result["text"].startswith("Good morning")
