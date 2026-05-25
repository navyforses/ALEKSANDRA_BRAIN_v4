"""Phase 7.5 Rule #7 - Budget hard stop guard.

Extends the Phase 6.1 LiteLLM gate and the Phase 2.5
`scripts/cognition/budget.py` ledger. Pure-Python module: no I/O in the
core check so unit tests stay infrastructure-free.

Caps (from CLAUDE.md "ხარჯი" section):
    * Project total: $60 across the v7 lifecycle.
    * Phase-7.5 daily cap (operational guardrail): $5.
    * Monthly cap (Anthropic console mirror): $60.

The DAILY cap is the constitutional-rule trigger; the monthly cap is
informational. ``check_budget_or_raise`` enforces both.

Two enforcement entry points:

    * ``check_budget_before_call(*, daily_spend, monthly_spend,
       estimated_call_cost)`` - pure function (no I/O). Raises
       ``BudgetError`` if either projected sum exceeds its cap.

    * ``check_budget_or_raise(*, estimated_call_cost)`` - convenience
       wrapper: looks up current spend via ``query_current_spend()``
       (DRY_RUN -> (0.0, 0.0) when SUPABASE_DB_URL unset).

Reference:
    CLAUDE.md "ხარჯი" + Phase 6.1 i18n budget gate
    scripts/cognition/budget.py (Phase 2.5 runs ledger)
"""

from __future__ import annotations

import os
import sys
from typing import Optional

try:
    import psycopg2  # type: ignore
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Caps
# ---------------------------------------------------------------------------
MONTHLY_BUDGET_USD: float = 60.0  # project cap from CLAUDE.md
DAILY_BUDGET_USD: float = 5.0     # operational guardrail


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class BudgetError(RuntimeError):
    """Raised when a projected LLM call would breach the daily / monthly cap."""


# ---------------------------------------------------------------------------
# Pure guard (no I/O)
# ---------------------------------------------------------------------------
def check_budget_before_call(
    *,
    daily_spend: float,
    monthly_spend: float,
    estimated_call_cost: float,
) -> None:
    """Raise BudgetError if `estimated_call_cost` would breach either cap.

    Pure function. Does NOT read env, DB, or filesystem. Callers pre-load
    the two spend totals (``query_current_spend()`` is one source).

    Args:
        daily_spend: USD spent so far today.
        monthly_spend: USD spent so far this calendar month.
        estimated_call_cost: USD the next call is projected to spend.

    Raises:
        BudgetError: ``daily_spend + estimated_call_cost > DAILY`` OR
            ``monthly_spend + estimated_call_cost > MONTHLY``. The error
            message names which cap was breached.
    """
    if estimated_call_cost < 0:
        raise ValueError(
            f"estimated_call_cost must be >= 0; got {estimated_call_cost}"
        )
    projected_daily = daily_spend + estimated_call_cost
    projected_monthly = monthly_spend + estimated_call_cost
    if projected_daily > DAILY_BUDGET_USD:
        raise BudgetError(
            f"Phase 7.5 Rule #7: daily cap breach - "
            f"daily_spend ${daily_spend:.2f} + call ${estimated_call_cost:.4f} "
            f"= ${projected_daily:.4f} > ${DAILY_BUDGET_USD:.2f}"
        )
    if projected_monthly > MONTHLY_BUDGET_USD:
        raise BudgetError(
            f"Phase 7.5 Rule #7: monthly cap breach - "
            f"monthly_spend ${monthly_spend:.2f} + call ${estimated_call_cost:.4f} "
            f"= ${projected_monthly:.4f} > ${MONTHLY_BUDGET_USD:.2f}"
        )


# ---------------------------------------------------------------------------
# DRY_RUN-aware current-spend lookup
# ---------------------------------------------------------------------------
def _dsn() -> Optional[str]:
    return os.environ.get("SUPABASE_DB_URL")


def _is_dry_run() -> bool:
    return not _dsn()


def query_current_spend() -> tuple[float, float]:
    """Return ``(daily_spend_usd, monthly_spend_usd)`` from the runs ledger.

    DRY_RUN fallback: when SUPABASE_DB_URL is unset, returns ``(0.0, 0.0)``
    so unit tests and code-complete-mode verifiers do not require infra.

    Production path: reads ``runs.cost_usd`` aggregated by calendar day
    + calendar month. Phase 2.5 wrote this ledger; Phase 7.5 only reads.
    """
    if _is_dry_run():
        return 0.0, 0.0
    if psycopg2 is None:
        print(
            "[budget_guard] psycopg2 not importable; returning (0.0, 0.0) - "
            "rule #7 enforcement degraded",
            file=sys.stderr,
        )
        return 0.0, 0.0

    conn = psycopg2.connect(_dsn(), sslmode="require")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  COALESCE(SUM(cost_usd) FILTER
                    (WHERE created_at >= date_trunc('day', NOW())), 0),
                  COALESCE(SUM(cost_usd) FILTER
                    (WHERE created_at >= date_trunc('month', NOW())), 0)
                FROM runs
                """
            )
            row = cur.fetchone()
            if not row:
                return 0.0, 0.0
            return float(row[0]), float(row[1])
    finally:
        conn.close()


def check_budget_or_raise(*, estimated_call_cost: float = 0.05) -> None:
    """Convenience: query current spend + run the pure guard.

    Args:
        estimated_call_cost: USD the next call is projected to spend
            (default $0.05 = roughly a single Sonnet 4.5 short prompt).

    Raises:
        BudgetError: see ``check_budget_before_call``.
    """
    daily, monthly = query_current_spend()
    check_budget_before_call(
        daily_spend=daily,
        monthly_spend=monthly,
        estimated_call_cost=estimated_call_cost,
    )


__all__ = [
    "BudgetError",
    "DAILY_BUDGET_USD",
    "MONTHLY_BUDGET_USD",
    "check_budget_before_call",
    "check_budget_or_raise",
    "query_current_spend",
]
