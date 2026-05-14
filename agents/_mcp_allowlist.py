"""
MCP allowlist enforcement — Phase 0 (FND-06).

Reads MCP-INVENTORY.csv and exposes:
  - allowed_mcps(agent_name) -> list[str]
  - is_allowed(agent_name, mcp_name) -> bool
  - guard(agent_name, mcp_name) -> raises MCPAllowlistError if not allowed

Pattern in MCP-INVENTORY.csv:
  - allowed_agents = '*'                          → every agent
  - allowed_agents = 'spider'                     → just spider
  - allowed_agents = 'analyzer|hypothesis'        → multiple agents (pipe-separated)

Used by every agent factory in agents/*.py before binding MCP tools to
the CrewAI Agent instance. A BLOCKED call writes a `runs` row with
exit_status='blocked_by_allowlist' so violations are visible in audit.
"""
from __future__ import annotations

import csv
import logging
import os
from pathlib import Path
from typing import Iterable

log = logging.getLogger("aleksandra_brain.allowlist")

INVENTORY_PATH = Path(__file__).resolve().parent.parent / "MCP-INVENTORY.csv"


class MCPAllowlistError(RuntimeError):
    """Raised when an agent tries to use an MCP it isn't allowlisted for."""


def _load_inventory() -> dict[str, set[str]]:
    """Return {mcp_name: {allowed_agent, ...}}; '*' means every agent."""
    if not INVENTORY_PATH.exists():
        raise FileNotFoundError(
            f"MCP-INVENTORY.csv missing at {INVENTORY_PATH}. "
            "Every MCP usage must be allowlisted (FND-06)."
        )
    table: dict[str, set[str]] = {}
    with INVENTORY_PATH.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mcp = row["mcp_name"].strip()
            agents_field = row["allowed_agents"].strip()
            agents = {a.strip() for a in agents_field.split("|") if a.strip()}
            table[mcp] = agents
    return table


# Cached at import time; reload by deleting the attribute.
_INVENTORY: dict[str, set[str]] = _load_inventory()


def reload() -> None:
    """Force reload of MCP-INVENTORY.csv (useful in tests / after edits)."""
    global _INVENTORY
    _INVENTORY = _load_inventory()


def allowed_mcps(agent_name: str) -> list[str]:
    """Return every MCP this agent is allowed to call."""
    return sorted(
        mcp
        for mcp, agents in _INVENTORY.items()
        if "*" in agents or agent_name in agents
    )


def is_allowed(agent_name: str, mcp_name: str) -> bool:
    agents = _INVENTORY.get(mcp_name)
    if agents is None:
        return False  # Unknown MCP = denied (fail closed).
    return "*" in agents or agent_name in agents


def guard(agent_name: str, mcp_name: str) -> None:
    """Raise MCPAllowlistError if the call would violate the allowlist."""
    if is_allowed(agent_name, mcp_name):
        return
    log.warning(
        "BLOCKED — agent %r tried to call MCP %r (not in MCP-INVENTORY.csv).",
        agent_name,
        mcp_name,
    )
    _record_block(agent_name, mcp_name)
    raise MCPAllowlistError(
        f"agent {agent_name!r} is not allowlisted for MCP {mcp_name!r}. "
        "Edit MCP-INVENTORY.csv to grant access."
    )


def filter_tools(agent_name: str, mcp_tools: Iterable) -> list:
    """
    Convenience: given a list of CrewAI-style tools each carrying a
    `.mcp_name` attribute, drop any the agent isn't allowlisted for.
    """
    kept: list = []
    for tool in mcp_tools:
        mcp_name = getattr(tool, "mcp_name", None) or getattr(tool, "name", "")
        if is_allowed(agent_name, mcp_name):
            kept.append(tool)
        else:
            log.info("filter_tools: drop %s for %s (not allowlisted)", mcp_name, agent_name)
    return kept


def _record_block(agent_name: str, mcp_name: str) -> None:
    """
    Best-effort write to Supabase `runs` so blocks are visible in audit.
    Silent on failure — never break a runtime path because audit is down.
    """
    try:
        import httpx  # local import — avoid hard dep if Supabase isn't configured
    except ImportError:
        return
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not supabase_url or not supabase_key:
        return
    try:
        httpx.post(
            f"{supabase_url}/rest/v1/runs",
            json={
                "kind": "agent_run",
                "agent_id": agent_name,
                "exit_status": "blocked_by_allowlist",
                "exit_reason": f"attempted MCP: {mcp_name}",
            },
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            timeout=3,
        )
    except Exception:
        pass


if __name__ == "__main__":
    # CLI: python -m agents._mcp_allowlist [agent_name]
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else None
    if target:
        print(f"MCPs allowed for {target!r}:")
        for mcp in allowed_mcps(target):
            print(f"  - {mcp}")
    else:
        print("MCP inventory:")
        for mcp, agents in sorted(_INVENTORY.items()):
            scope = "*" if "*" in agents else ",".join(sorted(agents))
            print(f"  {mcp:<20} → {scope}")
