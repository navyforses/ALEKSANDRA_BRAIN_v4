"""
Small local run logger for Phase 2.5 repurposing diagnostics.

The Phase 2 audit flagged that repurposing had stdout-only traces. This module
adds a file trace without changing the Supabase write contract:

  scripts/repurposing/run_logs/latest.log
  scripts/repurposing/run_logs/<run_id>.json

It is intentionally dependency-light and local-filesystem-only so it does not
overlap with Claude Code's current Phase 2.5 verifier/chunking work.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_LOG_DIR = Path(__file__).resolve().parent / "run_logs"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_run_id(name: str, started_at: datetime) -> str:
    stamp = started_at.strftime("%Y%m%dT%H%M%SZ")
    safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name)
    return f"{stamp}_{safe_name}"


@dataclass
class RepurposingRunLog:
    name: str
    started_at: datetime = field(default_factory=_utc_now)
    events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def run_id(self) -> str:
        return _safe_run_id(self.name, self.started_at)

    def event(self, message: str, **fields: Any) -> None:
        payload: dict[str, Any] = {
            "timestamp": _utc_now().isoformat(),
            "message": message,
        }
        payload.update(fields)
        self.events.append(payload)

    def finish(self, summary: dict[str, Any], *, status: str = "completed") -> Path:
        ended_at = _utc_now()
        payload = {
            "run_id": self.run_id,
            "name": self.name,
            "status": status,
            "started_at": self.started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "duration_seconds": round((ended_at - self.started_at).total_seconds(), 3),
            "summary": summary,
            "events": self.events,
        }

        RUN_LOG_DIR.mkdir(parents=True, exist_ok=True)
        json_path = RUN_LOG_DIR / f"{self.run_id}.json"
        latest_path = RUN_LOG_DIR / "latest.log"
        json_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
        latest_path.write_text(_render_text(payload), encoding="utf-8")
        return latest_path


def _render_text(payload: dict[str, Any]) -> str:
    lines = [
        f"run_id: {payload['run_id']}",
        f"name: {payload['name']}",
        f"status: {payload['status']}",
        f"started_at: {payload['started_at']}",
        f"ended_at: {payload['ended_at']}",
        f"duration_seconds: {payload['duration_seconds']}",
        "",
        "summary:",
    ]
    for key, value in payload["summary"].items():
        lines.append(f"  {key}: {value}")
    if payload["events"]:
        lines.extend(["", "events:"])
        for event in payload["events"]:
            fields = {
                k: v for k, v in event.items() if k not in {"timestamp", "message"}
            }
            suffix = f" {json.dumps(fields, sort_keys=True)}" if fields else ""
            lines.append(f"  - {event['timestamp']} {event['message']}{suffix}")
    lines.append("")
    return "\n".join(lines)
