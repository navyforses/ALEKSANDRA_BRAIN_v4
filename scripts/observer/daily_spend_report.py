"""
daily_spend_report — Phase 4 OBS-03 daily spend visibility.

Once per day (08:00 ET via n8n cron + Railway HTTP worker route),
aggregate the previous 24 hours of `runs.token_cost` grouped by `kind`,
format a three-line Georgian Telegram message, and post it to the
family channel. Then write a single audit row to `runs`
(`kind='daily_spend_report'`, `token_cost=0`) so verify_phase4 OBS-03
can confirm delivery.

The message format is deliberately tight (3 lines, ≤200 chars total):

    📊 ALEKSANDRA_BRAIN — გუშინდელი ხარჯი
    LLM: 12 ცდა · $0.4321 (ბიუჯეტი 28.8%)
    Cron: 4 perception · 1 weekly · 0 urgent

When spend exceeds the daily cap, the LLM line is prefixed with `⚠️`
and a follow-up line `მიეცეს გადახედვა` is appended. Phase 4 contract:
exception-only attention; no celebratory zero-spend nags.

Idempotency: if a `daily_spend_report` row already exists within the
last 4 hours, the function returns the prior result without re-posting.
This protects against n8n retries and accidental double-fires from the
Railway worker.

Quiet-hours: ACD-02 quiet hours (22:00–07:00 Boston) apply to T2/T3
tiers only. `daily_spend_report` is system-tier and exempt; the 08:00 ET
fire window is by design.

Run locally:
    .venv/Scripts/python.exe -X utf8 -m scripts.observer.daily_spend_report
    .venv/Scripts/python.exe -X utf8 -m scripts.observer.daily_spend_report --dry-run

Triggered via Railway HTTP worker (Day 5 wiring):
    curl -X POST $PERCEPTION_WORKER_URL/daily-spend-report
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import psycopg2

from scripts.cognition.budget import DEFAULT_DAILY_BUDGET_USD
from scripts.ledger import load_env


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
IDEMPOTENCY_WINDOW_HOURS = 4
LOOKBACK_HOURS = 24


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
@dataclass
class SpendSummary:
    """Aggregated spend over the prior LOOKBACK_HOURS window."""

    window_hours: int
    llm_calls: int
    llm_spend_usd: float
    cron_runs: dict[str, int]  # {'perception_tick': 4, 'weekly_brief_trigger': 1, ...}
    budget_cap_usd: float
    pct_of_cap: float
    over_cap: bool


def _collect_window(conn: psycopg2.extensions.connection) -> SpendSummary:
    """Single SQL pass over runs for the prior 24h window."""
    cap = DEFAULT_DAILY_BUDGET_USD
    cur = conn.cursor()

    # LLM calls + cost
    cur.execute(
        f"""
        SELECT COUNT(*)::int, COALESCE(SUM(token_cost), 0)::float
        FROM runs
        WHERE kind = 'llm_call'
          AND start_time >= now() - interval '{LOOKBACK_HOURS} hours'
        """
    )
    llm_calls, llm_spend = cur.fetchone()

    # Cron-style runs grouped by kind (everything that is NOT llm_call)
    cur.execute(
        f"""
        SELECT kind, COUNT(*)::int
        FROM runs
        WHERE kind != 'llm_call'
          AND start_time >= now() - interval '{LOOKBACK_HOURS} hours'
        GROUP BY kind
        """
    )
    cron_runs = {kind: count for kind, count in cur.fetchall()}
    cur.close()

    spend = float(llm_spend or 0.0)
    pct = (spend / cap * 100.0) if cap > 0 else 0.0
    return SpendSummary(
        window_hours=LOOKBACK_HOURS,
        llm_calls=int(llm_calls or 0),
        llm_spend_usd=spend,
        cron_runs=cron_runs,
        budget_cap_usd=cap,
        pct_of_cap=pct,
        over_cap=spend > cap,
    )


# ---------------------------------------------------------------------------
# Message formatting
# ---------------------------------------------------------------------------
def _format_message(s: SpendSummary) -> str:
    """Compose the three-line Georgian Telegram message."""
    warn = "⚠️ " if s.over_cap else ""
    llm_line = (
        f"{warn}LLM: {s.llm_calls} ცდა · ${s.llm_spend_usd:.4f} "
        f"(ბიუჯეტი {s.pct_of_cap:.1f}%)"
    )

    # Cron summary: only show kinds that fired ≥1 time, with friendly labels
    label_map = {
        "perception_tick": "perception",
        "weekly_brief_trigger": "weekly",
        "weekly_brief": "weekly",
        "urgent_alert": "urgent",
        "daily_digest": "digest",
        "fire_drill": "fire-drill",
        "budget_lock": "budget-lock",
        "agent_run": "agent",
        "validation_workflow": "validation",
        "daily_spend_report": "spend-report",
    }
    parts: list[str] = []
    for kind, count in sorted(s.cron_runs.items()):
        label = label_map.get(kind, kind)
        parts.append(f"{count} {label}")
    cron_line = "Cron: " + (" · ".join(parts) if parts else "0 runs")

    lines = [
        "📊 ALEKSANDRA_BRAIN — გუშინდელი ხარჯი",
        llm_line,
        cron_line,
    ]
    if s.over_cap:
        lines.append("მიეცეს გადახედვა")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Idempotency check
# ---------------------------------------------------------------------------
def _recent_report_exists(conn: psycopg2.extensions.connection) -> bool:
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT 1 FROM runs
        WHERE kind = 'daily_spend_report'
          AND start_time >= now() - interval '{IDEMPOTENCY_WINDOW_HOURS} hours'
        LIMIT 1
        """
    )
    hit = cur.fetchone() is not None
    cur.close()
    return hit


# ---------------------------------------------------------------------------
# Audit row writer
# ---------------------------------------------------------------------------
def _insert_audit_row(
    conn: psycopg2.extensions.connection,
    *,
    summary: SpendSummary,
    telegram_message_id: int | None,
    exit_status: str,
    exit_reason: str | None,
) -> str:
    """Append a `daily_spend_report` runs row. Returns its uuid."""
    now = datetime.now(timezone.utc)
    payload = {
        "summary": asdict(summary),
        "telegram_message_id": telegram_message_id,
    }
    cur = conn.cursor()
    # NOTE: `duration_seconds` is a generated column
    # (extract(epoch from end_time - start_time)::int) and MUST NOT be
    # passed in the INSERT — Postgres rejects with errcode 428C9.
    cur.execute(
        """
        INSERT INTO runs (
            kind, agent_id, start_time, end_time,
            token_cost, tokens_input, tokens_output,
            exit_status, exit_reason, draft_link
        ) VALUES (
            'daily_spend_report', 'daily-spend-report', %s, %s,
            0, 0, 0,
            %s, %s, %s
        )
        RETURNING id
        """,
        (now, now, exit_status, exit_reason, json.dumps(payload, default=str)),
    )
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    return str(new_id)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def run(*, dry_run: bool = False) -> dict[str, Any]:
    """Aggregate → format → (optionally) send → audit.

    Returns a JSON-serialisable dict the HTTP wrapper can hand back to n8n.
    """
    load_env()
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        # Aggregate first; we always want to surface the numbers in the
        # response even on idempotent short-circuit.
        summary = _collect_window(conn)
        message = _format_message(summary)

        if dry_run:
            return {
                "exit_status": "dry_run",
                "message": message,
                "summary": asdict(summary),
                "telegram_message_id": None,
                "runs_id": None,
            }

        if _recent_report_exists(conn):
            return {
                "exit_status": "idempotent_skip",
                "message": message,
                "summary": asdict(summary),
                "telegram_message_id": None,
                "runs_id": None,
                "reason": (
                    f"daily_spend_report already fired in last "
                    f"{IDEMPOTENCY_WINDOW_HOURS}h"
                ),
            }

        # Telegram send: import lazily so the module can load in CI
        # without TELEGRAM_BOT_TOKEN set (verify_phase4 imports this).
        from scripts.communicator.telegram_sender import _send_telegram

        try:
            message_id = _send_telegram(message)
            audit_id = _insert_audit_row(
                conn,
                summary=summary,
                telegram_message_id=message_id,
                exit_status="sent",
                exit_reason=None,
            )
            return {
                "exit_status": "sent",
                "message": message,
                "summary": asdict(summary),
                "telegram_message_id": message_id,
                "runs_id": audit_id,
            }
        except Exception as e:
            # Write the audit row anyway so we have evidence of the attempt.
            audit_id = _insert_audit_row(
                conn,
                summary=summary,
                telegram_message_id=None,
                exit_status="send_failed",
                exit_reason=f"{type(e).__name__}: {str(e)[:200]}",
            )
            return {
                "exit_status": "send_failed",
                "message": message,
                "summary": asdict(summary),
                "telegram_message_id": None,
                "runs_id": audit_id,
                "error": f"{type(e).__name__}: {str(e)[:200]}",
            }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _serialize(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 4 OBS-03 daily spend report")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute + format, do not send or write audit row",
    )
    args = parser.parse_args(argv)
    result = run(dry_run=args.dry_run)
    print(json.dumps(result, default=_serialize, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
