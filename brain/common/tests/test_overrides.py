"""Tests for brain.common.overrides (Phase 7.5 meta - overrides API)."""

from __future__ import annotations

import os
from unittest import mock

import pytest
from pydantic import ValidationError

from brain.common.overrides import (
    DEFAULT_TTL_HOURS,
    OverrideRecord,
    is_rule_currently_overridden,
    issue_override,
    list_active_overrides,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ensure_dry_run() -> None:
    os.environ.pop("SUPABASE_DB_URL", None)


# ---------------------------------------------------------------------------
# issue_override
# ---------------------------------------------------------------------------
def test_issue_override_dry_run_returns_sentinel():
    _ensure_dry_run()
    sentinel = issue_override(
        rule_number=9,
        reason="confirmed-hypothesis backfill window for HIE cohort",
        overridden_by="shako",
        notify_wife=False,
    )
    assert sentinel.startswith("DRY_RUN:")
    assert len(sentinel) > len("DRY_RUN:")


def test_issue_override_short_reason_fails():
    _ensure_dry_run()
    with pytest.raises(ValidationError):
        issue_override(
            rule_number=1,
            reason="short",  # < 20 chars
            overridden_by="shako",
            notify_wife=False,
        )


def test_issue_override_rule_zero_fails():
    _ensure_dry_run()
    with pytest.raises(ValidationError):
        issue_override(
            rule_number=0,
            reason="rule_number must be in 1..13 range for sure",
            overridden_by="shako",
            notify_wife=False,
        )


def test_issue_override_rule_fourteen_fails():
    _ensure_dry_run()
    with pytest.raises(ValidationError):
        issue_override(
            rule_number=14,
            reason="rule_number must be in 1..13 range for sure",
            overridden_by="shako",
            notify_wife=False,
        )


def test_issue_override_with_notify_wife_returns_sentinel():
    _ensure_dry_run()
    sentinel = issue_override(
        rule_number=11,
        reason="urgent clinical question outside weekly cap window",
        overridden_by="shako",
        notify_wife=True,
    )
    assert sentinel.startswith("DRY_RUN:")


def test_issue_override_deterministic_dry_run_hash():
    _ensure_dry_run()
    a = issue_override(
        rule_number=3,
        reason="prefilled citation pending Cochrane confirmation",
        overridden_by="shako",
        notify_wife=False,
    )
    b = issue_override(
        rule_number=3,
        reason="prefilled citation pending Cochrane confirmation",
        overridden_by="shako",
        notify_wife=False,
    )
    assert a == b


# ---------------------------------------------------------------------------
# is_rule_currently_overridden / list_active_overrides
# ---------------------------------------------------------------------------
def test_is_rule_currently_overridden_dry_run_false():
    _ensure_dry_run()
    assert is_rule_currently_overridden(7) is False


def test_is_rule_currently_overridden_invalid_rule():
    with pytest.raises(ValueError):
        is_rule_currently_overridden(99)


def test_list_active_overrides_dry_run_empty():
    _ensure_dry_run()
    assert list_active_overrides() == []


# ---------------------------------------------------------------------------
# OverrideRecord directly
# ---------------------------------------------------------------------------
def test_override_record_constants_present():
    assert DEFAULT_TTL_HOURS == 24


def test_override_record_fields():
    from datetime import datetime, timedelta, timezone

    rec = OverrideRecord(
        rule_number=5,
        reason="bilingual parity escape - locale rollout follow-up",
        overridden_by="shako",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    assert rec.rule_number == 5
    assert rec.notified_wife_at is None
