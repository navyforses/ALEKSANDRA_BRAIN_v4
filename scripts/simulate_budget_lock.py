"""
simulate_budget_lock — insert a budget_lock row into Supabase `runs`.

Used by the FND-04 fire drill to bypass the n8n workflow's HTTP node when
its template-substitution config is being debugged. The row this script
writes is functionally identical to what daily-budget-gate.json would
write when the daily spend exceeds the cap.

After running this, `fire_drill --budget` should detect the lock row
within ~2 seconds and halt with exit_status='killed_by_budget_gate'.

Usage:
    python -m scripts.simulate_budget_lock
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
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


def main() -> int:
    _load_dotenv()
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        print("ERROR: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing in .env")
        return 1

    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "kind": "budget_lock",
        "agent_id": "simulate_budget_lock",
        "exit_status": "killed_by_budget_gate",
        "exit_reason": "simulated lock — fire drill verification",
        "start_time": now,
        "end_time": now,
        "token_cost": 0,
    }

    r = httpx.post(
        f"{url}/rest/v1/runs",
        json=payload,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        timeout=10,
    )

    if r.status_code in (200, 201):
        try:
            row_id = r.json()[0]["id"]
        except Exception:
            row_id = "?"
        print(f"[OK] budget_lock row inserted (id={row_id}, at={now})")
        return 0
    print(f"[FAIL] HTTP {r.status_code}: {r.text[:300]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
