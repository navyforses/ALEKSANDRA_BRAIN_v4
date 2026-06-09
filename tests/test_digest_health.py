"""
test_digest_health.py — Phase E digest health-check.

The daily spend digest must shout when many LLM calls recorded $0 total spend —
the exact signature of the 2026-06-09 outage (a failed call records cost=0).
"""

from __future__ import annotations

from scripts.observer.daily_spend_report import SpendSummary, _format_message


def _summary(*, calls: int, spend: float) -> SpendSummary:
    return SpendSummary(
        window_hours=24,
        llm_calls=calls,
        llm_spend_usd=spend,
        cron_runs={},
        budget_cap_usd=5.0,
        pct_of_cap=(spend / 5.0 * 100.0),
        over_cap=spend > 5.0,
    )


def test_all_failing_signature_is_flagged():
    msg = _format_message(_summary(calls=1000, spend=0.0))
    assert "ALL LLM CALLS FAILING" in msg


def test_healthy_spend_not_flagged():
    msg = _format_message(_summary(calls=100, spend=0.42))
    assert "ALL LLM CALLS FAILING" not in msg


def test_few_calls_zero_spend_not_flagged():
    # A quiet window with only a handful of (failed) calls is not the outage
    # signature — don't cry wolf below the threshold.
    msg = _format_message(_summary(calls=3, spend=0.0))
    assert "ALL LLM CALLS FAILING" not in msg
