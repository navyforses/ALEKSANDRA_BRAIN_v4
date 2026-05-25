"""Phase 7.4 Day 6 — rate_limiter tests."""

from __future__ import annotations

from datetime import datetime

import pytest

from brain.active.rate_limiter import (
    WEEKLY_CAP,
    can_send_question,
    iso_week_of,
    record_sent,
    reset_dry_run_state,
    weekly_sent_count,
)


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    # Force DRY_RUN mode for every test in this module.
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    reset_dry_run_state()
    yield
    reset_dry_run_state()


def test_can_send_for_fresh_week() -> None:
    assert can_send_question("2026-W45") is True
    assert weekly_sent_count("2026-W45") == 0


def test_cap_enforced_after_three_records() -> None:
    """Verifier check 6: 4th send in same week is rate_limited."""
    week = "2026-W45"
    record_sent(week)
    record_sent(week)
    record_sent(week)
    assert weekly_sent_count(week) == 3
    assert can_send_question(week) is False
    # The 4th `record_sent` is rejected fail-closed (no exception, no count change)
    record_sent(week)
    assert weekly_sent_count(week) == 3


def test_record_increments() -> None:
    week = "2026-W46"
    assert weekly_sent_count(week) == 0
    record_sent(week)
    assert weekly_sent_count(week) == 1
    record_sent(week)
    assert weekly_sent_count(week) == 2


def test_different_weeks_counted_separately() -> None:
    record_sent("2026-W45")
    record_sent("2026-W45")
    record_sent("2026-W46")
    assert weekly_sent_count("2026-W45") == 2
    assert weekly_sent_count("2026-W46") == 1
    assert can_send_question("2026-W45") is True
    assert can_send_question("2026-W46") is True


def test_iso_week_of_format() -> None:
    # 2026-01-05 is a Monday, ISO week 02
    dt = datetime(2026, 1, 5)
    assert iso_week_of(dt) == "2026-W02"
    # 2025-12-29 (Monday) ISO week 01 of 2026
    dt2 = datetime(2025, 12, 29)
    assert iso_week_of(dt2).startswith("2026-W")


def test_weekly_cap_constant() -> None:
    assert WEEKLY_CAP == 3
