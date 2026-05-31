"""Phase 7.4 Day 6 — Weekly rate limiter (constitutional rule #11).

Hard cap: 3 questions per ISO week. Spec §1 Day 7, §4 check 6.

DRY_RUN fallback: when `SUPABASE_DB_URL` is unset, all read/write goes to
an in-process dict keyed by ISO week. This lets the verifier and pytest
suite exercise the rate-limit logic without infrastructure.

Production path: when SUPABASE_DB_URL is set, the same API hits
`active_rate_log` (migration 020) via the spec §2.4 UPSERT pattern.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Optional

try:
    import psycopg2  # type: ignore
    import psycopg2.extras  # type: ignore
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[assignment]


WEEKLY_CAP = 3  # constitutional rule #11

# In-process state for DRY_RUN mode. Reset via `reset_dry_run_state()`.
_DRY_RUN_RATE: dict[str, int] = {}


def _dsn() -> Optional[str]:
    return os.environ.get("SUPABASE_DB_URL")


def _is_dry_run() -> bool:
    return not _dsn()


def reset_dry_run_state() -> None:
    """Testing helper: clear the in-process counter."""
    _DRY_RUN_RATE.clear()


# ---------------------------------------------------------------------------
# ISO week helpers
# ---------------------------------------------------------------------------
def iso_week_of(dt: datetime) -> str:
    """Return ISO 8601 week tag `YYYY-W##` for `dt`."""
    iso_year, iso_week, _ = dt.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def weekly_sent_count(week_iso: str) -> int:
    """Return how many questions have been sent in the given ISO week."""
    if _is_dry_run():
        return _DRY_RUN_RATE.get(week_iso, 0)
    # Production path
    conn = psycopg2.connect(_dsn(), sslmode="require")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT questions_sent FROM active_rate_log WHERE week_iso = %s",
                (week_iso,),
            )
            row = cur.fetchone()
            return int(row[0]) if row else 0
    finally:
        conn.close()


def can_send_question(week_iso: str) -> bool:
    """True iff the weekly cap has not yet been reached for `week_iso`."""
    return weekly_sent_count(week_iso) < WEEKLY_CAP


def record_sent(week_iso: str) -> None:
    """Increment the per-week counter. Fails closed on cap breach."""
    if not can_send_question(week_iso):
        print(
            f"[rate_limiter] refusing to record send for {week_iso}: "
            f"cap {WEEKLY_CAP} already reached",
            file=sys.stderr,
        )
        return
    if _is_dry_run():
        _DRY_RUN_RATE[week_iso] = _DRY_RUN_RATE.get(week_iso, 0) + 1
        return
    # Production path
    conn = psycopg2.connect(_dsn(), sslmode="require")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO active_rate_log (week_iso, questions_sent, cap)
                VALUES (%s, 1, %s)
                ON CONFLICT (week_iso) DO UPDATE
                  SET questions_sent = active_rate_log.questions_sent + 1
                  WHERE active_rate_log.questions_sent < active_rate_log.cap
                """,
                (week_iso, WEEKLY_CAP),
            )
        conn.commit()
    finally:
        conn.close()


__all__ = [
    "WEEKLY_CAP",
    "iso_week_of",
    "weekly_sent_count",
    "can_send_question",
    "record_sent",
    "reset_dry_run_state",
]
