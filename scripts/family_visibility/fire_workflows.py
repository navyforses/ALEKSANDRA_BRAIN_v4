"""
Local fire helper for Phase 2.5C family-visible workflows.

The n8n JSON files are the deployed automation contract. This helper is the
auditable local equivalent used when closing the gate before n8n deployment:
it composes PHI-free summaries, appends `runs` rows, and optionally sends
Telegram messages if `--telegram` is passed.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from scripts.ledger import _supabase_creds, _supabase_headers, load_env


def _get(path: str, params: dict[str, str]) -> list[dict[str, Any]]:
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/{path}",
        params=params,
        headers=_supabase_headers(key),
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []


def _append_run(kind: str, agent_id: str, reason: str) -> None:
    url, key = _supabase_creds()
    payload = {
        "kind": kind,
        "agent_id": agent_id,
        "exit_status": "completed",
        "exit_reason": reason[:900],
        "tokens_input": 0,
        "tokens_output": 0,
        "token_cost": 0,
    }
    r = httpx.post(
        f"{url}/rest/v1/runs",
        json=payload,
        headers={**_supabase_headers(key), "Prefer": "return=minimal"},
        timeout=30,
    )
    r.raise_for_status()


def _send_telegram(text: str) -> None:
    import os

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing")
    r = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=30,
    )
    r.raise_for_status()


def compose_daily_digest() -> str:
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    papers = _get(
        "papers",
        {
            "select": "title,relevance_score,pmid,ct_id",
            "order": "relevance_score.desc.nullslast",
            "limit": "3",
        },
    )
    runs = _get(
        "runs",
        {
            "select": "kind,token_cost,start_time",
            "kind": "eq.llm_call",
            "start_time": f"gte.{since}",
            "limit": "1000",
        },
    )
    spend = sum(float(r.get("token_cost") or 0) for r in runs)
    top = "; ".join(
        f"{p.get('relevance_score')}: {p.get('title', '')[:90]}" for p in papers
    )
    return (
        "ALEKSANDRA_BRAIN daily digest: "
        f"top_papers={len(papers)}; llm_calls={len(runs)}; spend=${spend:.6f}; "
        f"top={top or 'none'}"
    )


def compose_urgent_alert() -> str:
    since = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    papers = _get(
        "papers",
        {
            "select": "title,relevance_score,pmid,ct_id",
            "relevance_score": "gte.0.9",
            "order": "relevance_score.desc.nullslast",
            "limit": "3",
        },
    )
    confirmed = _get(
        "hypotheses",
        {
            "select": "title,status,reviewed_at",
            "status": "eq.confirmed",
            "reviewed_at": f"gte.{since}",
            "limit": "5",
        },
    )
    top = "; ".join(
        f"{p.get('relevance_score')}: {p.get('title', '')[:90]}" for p in papers
    )
    return (
        "ALEKSANDRA_BRAIN urgent-alert check: "
        f"high_relevance_papers={len(papers)}; recent_confirmed={len(confirmed)}; "
        f"top={top or 'none'}"
    )


def run(*, telegram: bool = False) -> int:
    load_env()

    digest = compose_daily_digest()
    if telegram:
        _send_telegram(digest)
    _append_run("daily_digest", "family_visibility", digest)
    print(f"daily_digest: {digest}")

    urgent = compose_urgent_alert()
    if telegram:
        _send_telegram(urgent)
    _append_run("urgent_alert", "family_visibility", urgent)
    print(f"urgent_alert: {urgent}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--telegram",
        action="store_true",
        help="Also send Telegram messages. Default only appends runs rows.",
    )
    args = parser.parse_args()
    return run(telegram=args.telegram)


if __name__ == "__main__":
    raise SystemExit(main())
