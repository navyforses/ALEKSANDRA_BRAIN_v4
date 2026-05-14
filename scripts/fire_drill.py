"""
fire_drill — Phase 0 exit gate (FND-03 / FND-04 verification)

Simulates a runaway agent that calls Claude API every second for 60s.
The drill PASSES when either the Telegram `/stop` kill-switch OR the n8n
daily budget gate halts execution within 60 seconds. Worst-case cost is
bounded by Anthropic's quickest haiku call (~$0.001/call × 60 = $0.06).

Run modes:
  python -m scripts.fire_drill --telegram   # expects user to send /stop in Telegram
  python -m scripts.fire_drill --budget     # expects daily-budget-gate to flip BUDGET_LOCKED
  python -m scripts.fire_drill --dry-run    # no real Anthropic calls; print + sleep only

The script writes a row to Supabase `runs` at start and on exit. Use
docs/PHASE_0_EXIT_REPORT.md as the human-readable companion log.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone

import httpx

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
N8N_URL = os.getenv("N8N_URL", "").rstrip("/")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

DURATION_SECONDS = 60
TICK_SECONDS = 1


def _supabase_insert(payload: dict) -> str | None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    r = httpx.post(
        f"{SUPABASE_URL}/rest/v1/runs",
        json=payload,
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        timeout=5,
    )
    if r.status_code in (200, 201):
        try:
            return r.json()[0]["id"]
        except Exception:
            return None
    return None


def _telegram(msg: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        httpx.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
            timeout=5,
        )
    except Exception:
        pass


def _check_telegram_stop() -> bool:
    """Poll Telegram getUpdates for a fresh `/stop` from the family channel."""
    if not TELEGRAM_BOT_TOKEN:
        return False
    try:
        r = httpx.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
            params={"timeout": 0, "offset": -1},
            timeout=3,
        )
        for upd in r.json().get("result", []):
            text = upd.get("message", {}).get("text", "").strip().lower()
            chat = str(upd.get("message", {}).get("chat", {}).get("id", ""))
            if chat == str(TELEGRAM_CHAT_ID) and text in ("/stop", "/stop@bot"):
                return True
    except Exception:
        pass
    return False


def _check_budget_locked() -> bool:
    """Read BUDGET_LOCKED static variable from n8n."""
    if not N8N_URL or not N8N_API_KEY:
        return False
    try:
        r = httpx.get(
            f"{N8N_URL}/api/v1/variables",
            headers={"X-N8N-API-KEY": N8N_API_KEY},
            timeout=3,
        )
        for var in r.json().get("data", []):
            if (
                var.get("key") == "BUDGET_LOCKED"
                and str(var.get("value")).lower() == "true"
            ):
                return True
    except Exception:
        pass
    return False


def _anthropic_ping(dry_run: bool) -> float:
    """Make one cheap haiku call. Return cost in USD."""
    if dry_run or not ANTHROPIC_API_KEY:
        return 0.0
    try:
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 8,
                "messages": [{"role": "user", "content": "say hi"}],
            },
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        if r.status_code == 200:
            # Rough USD: $0.80/M input + $4/M output tokens (haiku 4.5)
            usage = r.json().get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            return (input_tokens * 0.80 + output_tokens * 4.0) / 1_000_000
    except Exception:
        pass
    return 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--telegram", action="store_true", help="expect /stop within 60s")
    ap.add_argument("--budget", action="store_true", help="expect BUDGET_LOCKED flip")
    ap.add_argument("--dry-run", action="store_true", help="no real Anthropic calls")
    args = ap.parse_args()

    mode = "telegram" if args.telegram else "budget" if args.budget else "manual"
    started = datetime.now(timezone.utc)

    _supabase_insert(
        {
            "kind": "fire_drill",
            "agent_id": f"fire_drill_{mode}",
            "exit_status": "in_progress",
            "start_time": started.isoformat(),
        }
    )

    _telegram(
        f"🔥 fire_drill started ({mode}). I will call Anthropic every {TICK_SECONDS}s "
        f"for up to {DURATION_SECONDS}s unless halted. Send /stop to halt."
    )

    total_cost = 0.0
    calls = 0
    halt_reason = "timeout"
    t0 = time.monotonic()

    while time.monotonic() - t0 < DURATION_SECONDS:
        if args.telegram and _check_telegram_stop():
            halt_reason = "killed_by_panic_stop"
            break
        if args.budget and _check_budget_locked():
            halt_reason = "killed_by_budget_gate"
            break
        total_cost += _anthropic_ping(args.dry_run)
        calls += 1
        time.sleep(TICK_SECONDS)

    ended = datetime.now(timezone.utc)
    elapsed = round((ended - started).total_seconds(), 1)
    ok = halt_reason != "timeout" if (args.telegram or args.budget) else True

    _supabase_insert(
        {
            "kind": "fire_drill",
            "agent_id": f"fire_drill_{mode}",
            "exit_status": halt_reason if halt_reason != "timeout" else "completed",
            "exit_reason": f"calls={calls} cost_usd={total_cost:.4f} mode={mode}",
            "token_cost": total_cost,
            "start_time": started.isoformat(),
            "end_time": ended.isoformat(),
        }
    )

    summary = (
        f"🔥 fire_drill {'PASSED' if ok else 'FAILED'} ({mode}).\n"
        f"  calls = {calls}\n"
        f"  cost  = ${total_cost:.4f}\n"
        f"  halt  = {halt_reason}\n"
        f"  time  = {elapsed}s"
    )
    print(summary)
    _telegram(summary)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
