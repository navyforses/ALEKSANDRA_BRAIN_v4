"""
fire_drill — Phase 0 exit gate (FND-03 / FND-04 verification)

Simulates a runaway agent that calls Claude API every second for 60s.
The drill PASSES when either the Telegram `/stop` kill-switch OR the n8n
daily budget gate halts execution within 60 seconds. Worst-case cost is
bounded by Anthropic's quickest haiku call (~$0.001/call × 60 = $0.06).

Run modes:
  python -m scripts.fire_drill --telegram   # expects user to send /stop in Telegram
  python -m scripts.fire_drill --budget     # expects daily-budget-gate to write budget_lock
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
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    """Best-effort .env loader (utf-8) without external deps."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


_load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

DURATION_SECONDS = 60
TICK_SECONDS = 0.5

# Track Telegram updates that existed BEFORE the drill started so that we only
# halt on a fresh `/stop`, not on a stale one from a previous run.
_telegram_baseline_update_id: int = 0


def _supabase_insert(payload: dict) -> str | None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
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
    except Exception:
        pass
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


def _telegram_seed_baseline() -> None:
    """Read current update_id so we only react to NEW /stop messages."""
    global _telegram_baseline_update_id
    if not TELEGRAM_BOT_TOKEN:
        return
    try:
        r = httpx.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
            params={
                "timeout": 0,
                "offset": -1,
                "limit": 1,
                "allowed_updates": '["message","channel_post"]',
            },
            timeout=3,
        )
        for upd in r.json().get("result", []):
            _telegram_baseline_update_id = max(
                _telegram_baseline_update_id, int(upd.get("update_id", 0))
            )
    except Exception:
        pass


def _check_telegram_stop() -> bool:
    """
    Poll Telegram for a fresh `/stop` newer than baseline. Handles both group
    `message` updates and `channel_post` updates (the family chat is a Telegram
    channel where bots receive channel_post events when admin).
    """
    global _telegram_baseline_update_id
    if not TELEGRAM_BOT_TOKEN:
        return False
    try:
        r = httpx.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
            params={
                "timeout": 0,
                "offset": _telegram_baseline_update_id + 1,
                "allowed_updates": '["message","channel_post"]',
            },
            timeout=3,
        )
        hit = False
        for upd in r.json().get("result", []):
            uid = int(upd.get("update_id", 0))
            _telegram_baseline_update_id = max(_telegram_baseline_update_id, uid)
            msg = upd.get("message") or upd.get("channel_post") or {}
            text = (msg.get("text") or "").strip().lower()
            chat = str(msg.get("chat", {}).get("id", ""))
            if chat == str(TELEGRAM_CHAT_ID) and text.startswith("/stop"):
                hit = True
        return hit
    except Exception:
        return False


def _check_budget_locked(since_iso: str) -> bool:
    """
    Check Supabase `runs` for a budget_lock row written since the drill started.
    The daily-budget-gate n8n workflow writes `kind='budget_lock'` when today's
    summed token_cost exceeds the cap.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    try:
        r = httpx.get(
            f"{SUPABASE_URL}/rest/v1/runs",
            params={
                "select": "id,start_time,kind",
                "kind": "eq.budget_lock",
                "start_time": f"gte.{since_iso}",
                "limit": "1",
            },
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            },
            timeout=3,
        )
        return r.status_code == 200 and len(r.json()) > 0
    except Exception:
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
            # Haiku 4.5: $0.80/M input + $4/M output tokens
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
    ap.add_argument("--budget", action="store_true", help="expect budget_lock row")
    ap.add_argument("--dry-run", action="store_true", help="no real Anthropic calls")
    args = ap.parse_args()

    mode = "telegram" if args.telegram else "budget" if args.budget else "manual"
    started = datetime.now(timezone.utc)
    started_iso = started.isoformat()

    if args.telegram:
        _telegram_seed_baseline()

    _supabase_insert(
        {
            "kind": "fire_drill",
            "agent_id": f"fire_drill_{mode}",
            "exit_status": "in_progress",
            "start_time": started_iso,
        }
    )

    _telegram(
        f"🔥 fire_drill started ({mode}). Calling Anthropic every {TICK_SECONDS}s "
        f"for up to {DURATION_SECONDS}s unless halted. Send /stop to halt."
    )
    print(
        f"fire_drill ({mode}) started at {started_iso}. "
        f"Will tick every {TICK_SECONDS}s for {DURATION_SECONDS}s."
    )

    total_cost = 0.0
    calls = 0
    halt_reason = "timeout"
    t0 = time.monotonic()

    while time.monotonic() - t0 < DURATION_SECONDS:
        if args.telegram and _check_telegram_stop():
            halt_reason = "killed_by_panic_stop"
            break
        if args.budget and _check_budget_locked(started_iso):
            halt_reason = "killed_by_budget_gate"
            break
        total_cost += _anthropic_ping(args.dry_run)
        calls += 1
        elapsed_now = round(time.monotonic() - t0, 1)
        print(f"  [{elapsed_now:>5}s] call #{calls} cost=${total_cost:.4f}")
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
            "start_time": started_iso,
            "end_time": ended.isoformat(),
        }
    )

    verdict = "PASSED" if ok else "FAILED"
    # Console print stays ASCII-only because the default Windows code page
    # (cp1252) cannot encode emoji and would crash the script on exit.
    console_summary = (
        f"fire_drill {verdict} ({mode}).\n"
        f"  calls = {calls}\n"
        f"  cost  = ${total_cost:.4f}\n"
        f"  halt  = {halt_reason}\n"
        f"  time  = {elapsed}s"
    )
    telegram_summary = "🔥 " + console_summary
    print(console_summary)
    _telegram(telegram_summary)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
