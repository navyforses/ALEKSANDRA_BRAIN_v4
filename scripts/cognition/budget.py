"""
budget.py — Phase 2.5 sub-phase 2.5A daily-budget reader.

Reads the day's accumulated Anthropic spend from the `runs` table (the
same surface n8n's daily-budget-gate cron uses — see [viewer/app/page.tsx]
which advertises "n8n daily-budget-gate active (cron every 30 min)") and
exposes a single helper that the LLM wrappers in scripts.cognition.llm
call before each Anthropic request.

Why this lives in code AND in n8n: defence in depth. n8n's gate writes a
`kind='budget_lock'` row that pauses workflows when daily spend exceeds
the cap. Code-side `check_daily_budget()` raises before the SDK call so
no money is ever spent during the polling gap. Both paths read the same
`runs.token_cost` column — there is intentionally no separate
`daily_budget_log` table to drift out of sync.

Public surface
--------------
    BudgetExceeded
        Raised by `check_daily_budget(raise_on_over=True)`.

    check_daily_budget(threshold_usd=DEFAULT_DAILY_BUDGET_USD,
                       raise_on_over=False) -> tuple[float, bool]
        Returns (today_spend_usd, is_over_budget). Today = since 00:00 UTC.
        If `raise_on_over=True` and over, raises BudgetExceeded.

    DEFAULT_DAILY_BUDGET_USD = 1.50
        Conservative default. Override per-call or via the DAILY_BUDGET_USD
        env var (read on each call so n8n can change it without process
        restart).

Failure modes
-------------
Supabase unreachable / credentials missing → returns (0.0, False) and
logs to stderr. Failing CLOSED on budget read would block every LLM call
on intermittent network glitches, which costs more in halted research
than a stale read would in overspend. The n8n cron is the harder gate.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import httpx

from scripts.ledger import _supabase_creds, _supabase_headers, load_env


DEFAULT_DAILY_BUDGET_USD: float = 1.50


class BudgetExceeded(RuntimeError):
    """Raised when today's accumulated runs.token_cost exceeds the cap."""

    def __init__(self, today_spend_usd: float, threshold_usd: float) -> None:
        self.today_spend_usd = today_spend_usd
        self.threshold_usd = threshold_usd
        super().__init__(
            f"Daily LLM budget exceeded: "
            f"${today_spend_usd:.6f} > ${threshold_usd:.6f}. "
            f"Halt new Anthropic calls. Override via DAILY_BUDGET_USD env "
            f"or wait for UTC midnight."
        )


def _resolve_threshold(explicit: float | None) -> float:
    """Caller arg > DAILY_BUDGET_USD env > DEFAULT_DAILY_BUDGET_USD."""
    if explicit is not None:
        return float(explicit)
    raw = os.environ.get("DAILY_BUDGET_USD", "").strip()
    if raw:
        try:
            return float(raw)
        except ValueError:
            print(
                f"[budget] DAILY_BUDGET_USD={raw!r} not numeric; "
                f"using DEFAULT_DAILY_BUDGET_USD=${DEFAULT_DAILY_BUDGET_USD}",
                file=sys.stderr,
            )
    return DEFAULT_DAILY_BUDGET_USD


def _today_utc_iso() -> str:
    """Midnight UTC of the current day, ISO 8601 with timezone."""
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def check_daily_budget(
    threshold_usd: float | None = None,
    *,
    raise_on_over: bool = False,
) -> tuple[float, bool]:
    """
    Sum `runs.token_cost` since 00:00 UTC today and compare to threshold.

    Returns:
        (today_spend_usd, is_over_budget)

    Raises:
        BudgetExceeded: only if `raise_on_over=True` AND is_over_budget.
    """
    load_env()
    cap = _resolve_threshold(threshold_usd)
    try:
        url, key = _supabase_creds()
    except RuntimeError as e:
        print(f"[budget] supabase creds missing: {e}", file=sys.stderr)
        return 0.0, False

    today_iso = _today_utc_iso()
    try:
        r = httpx.get(
            f"{url}/rest/v1/runs",
            params={
                "select": "token_cost",
                "start_time": f"gte.{today_iso}",
            },
            headers=_supabase_headers(key, prefer="count=none"),
            timeout=5,
        )
        if r.status_code != 200:
            print(
                f"[budget] HTTP {r.status_code}: {r.text[:200]}",
                file=sys.stderr,
            )
            return 0.0, False
        rows = r.json()
    except Exception as e:
        print(
            f"[budget] read failed: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return 0.0, False

    total = 0.0
    for row in rows:
        v = row.get("token_cost")
        if v is None:
            continue
        try:
            total += float(v)
        except (TypeError, ValueError):
            continue

    over = total > cap
    if over and raise_on_over:
        raise BudgetExceeded(total, cap)
    return total, over


__all__ = [
    "BudgetExceeded",
    "DEFAULT_DAILY_BUDGET_USD",
    "check_daily_budget",
]
