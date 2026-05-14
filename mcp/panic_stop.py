"""
panic_stop — emergency kill-switch for ALEKSANDRA_BRAIN

Listens for `/stop` from the family Telegram channel and halts every running
n8n workflow + records the event in Supabase `runs` (append-only).

Phase 0 requirement: FND-03 — `/stop` must halt all agents and cancel the next
cron tick within 60 seconds.

Run as a FastMCP server (Claude Code uses it as a tool):

    python -m mcp.panic_stop          # one-shot RPC mode
    python -m mcp.panic_stop --listen # long-running Telegram poller

Environment variables (loaded from .env):
  TELEGRAM_BOT_TOKEN       — family Telegram bot
  TELEGRAM_CHAT_ID         — family channel ID
  N8N_URL                  — base URL of n8n instance (Railway)
  N8N_API_KEY              — n8n REST API key
  SUPABASE_URL             — for runs ledger
  SUPABASE_SERVICE_ROLE_KEY
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from fastmcp import FastMCP

mcp = FastMCP("panic-stop")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
N8N_URL = os.getenv("N8N_URL", "").rstrip("/")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


def _record_kill(reason: str) -> dict[str, Any]:
    """Append a kill-switch event to Supabase runs (append-only)."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return {"recorded": False, "reason": "supabase not configured"}
    payload = {
        "kind": "kill_switch",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "exit_status": f"killed_by_panic_stop:{reason}",
        "token_cost": 0,
    }
    r = httpx.post(
        f"{SUPABASE_URL}/rest/v1/runs",
        json=payload,
        headers={
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        timeout=10,
    )
    return {"recorded": r.status_code in (201, 204), "status": r.status_code}


def _stop_n8n_workflows() -> dict[str, Any]:
    """Deactivate every n8n workflow so the next cron tick will not fire."""
    if not N8N_URL or not N8N_API_KEY:
        return {"stopped": 0, "error": "n8n not configured"}
    headers = {"X-N8N-API-KEY": N8N_API_KEY}
    listing = httpx.get(f"{N8N_URL}/api/v1/workflows", headers=headers, timeout=10)
    if listing.status_code != 200:
        return {"stopped": 0, "error": f"list {listing.status_code}"}
    stopped = 0
    for wf in listing.json().get("data", []):
        if wf.get("active"):
            r = httpx.post(
                f"{N8N_URL}/api/v1/workflows/{wf['id']}/deactivate",
                headers=headers,
                timeout=10,
            )
            if r.status_code in (200, 204):
                stopped += 1
    return {"stopped": stopped}


def _telegram_reply(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    httpx.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
        timeout=10,
    )


@mcp.tool()
def panic_stop(reason: str = "manual") -> dict[str, Any]:
    """
    Kill-switch: deactivate every n8n workflow, record the event, notify family.
    Returns a summary so callers can confirm.
    """
    started = time.monotonic()
    n8n_result = _stop_n8n_workflows()
    supabase_result = _record_kill(reason)
    _telegram_reply(
        "🛑 გავაჩერე ყველაფერი.\n"
        f"მიზეზი: {reason}\n"
        f"გათიშული workflow-ები: {n8n_result.get('stopped', 0)}\n"
        "შემდეგი cron ვერ გაეშვება. ხელახლა ჩასართავად — n8n dashboard."
    )
    return {
        "reason": reason,
        "n8n": n8n_result,
        "supabase": supabase_result,
        "elapsed_seconds": round(time.monotonic() - started, 2),
    }


@mcp.tool()
def kill_switch_status() -> dict[str, Any]:
    """Report whether n8n is reachable and whether any workflows are still active."""
    if not N8N_URL or not N8N_API_KEY:
        return {"reachable": False, "error": "n8n not configured"}
    r = httpx.get(
        f"{N8N_URL}/api/v1/workflows",
        headers={"X-N8N-API-KEY": N8N_API_KEY},
        timeout=10,
    )
    if r.status_code != 200:
        return {"reachable": False, "status": r.status_code}
    active = [wf["name"] for wf in r.json().get("data", []) if wf.get("active")]
    return {"reachable": True, "active_workflows": active, "count": len(active)}


def _poll_telegram() -> None:
    """
    Long-running mode: poll Telegram getUpdates and trigger panic_stop on `/stop`.
    Used when running this module as a daemon outside the MCP context.
    """
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN missing — cannot listen", file=sys.stderr)
        sys.exit(1)
    offset = 0
    print("Listening for /stop ...", file=sys.stderr)
    while True:
        try:
            r = httpx.get(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
                params={"timeout": 25, "offset": offset},
                timeout=30,
            )
            for update in r.json().get("result", []):
                offset = update["update_id"] + 1
                text = update.get("message", {}).get("text", "")
                chat = str(update.get("message", {}).get("chat", {}).get("id", ""))
                if chat != str(TELEGRAM_CHAT_ID):
                    continue
                if text.strip().lower() in ("/stop", "/stop@bot"):
                    print(f"[{datetime.now()}] /stop received", file=sys.stderr)
                    result = panic_stop(reason="telegram_/stop")
                    print(result, file=sys.stderr)
        except Exception as e:
            print(f"poll error: {e}", file=sys.stderr)
            time.sleep(5)


if __name__ == "__main__":
    if "--listen" in sys.argv:
        _poll_telegram()
    else:
        mcp.run()
