"""
hello_brain — first custom MCP server for ALEKSANDRA_BRAIN

Phase 0 placeholder using FastMCP. Three tools:
  - hello_brain        → liveness check
  - brain_stats        → real counts from Supabase
  - system_health      → Neo4j + Qdrant + Supabase reachability

Register in claude_desktop_config.json:
{
  "mcpServers": {
    "aleksandra-brain": {
      "command": "python",
      "args": ["-m", "mcp.hello_brain"]
    }
  }
}
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastmcp import FastMCP

mcp = FastMCP("aleksandra-brain")


@mcp.tool()
def hello_brain() -> str:
    """Liveness check for the ALEKSANDRA_BRAIN system."""
    return "ALEKSANDRA_BRAIN v4.0 is alive."


@mcp.tool()
def brain_stats() -> dict[str, Any]:
    """
    Return real counts from Supabase: papers, contacts, hypotheses, brain_regions.
    Phase 0: returns zeros until Supabase is wired in §1.1.
    """
    # TODO §1.1: from supabase import create_client; ...
    return {
        "papers": 0,
        "contacts": 0,
        "hypotheses": 0,
        "brain_regions": 0,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "note": "Phase 0 placeholder — Supabase not yet connected.",
    }


@mcp.tool()
def system_health() -> dict[str, str]:
    """Check connectivity to Neo4j, Qdrant, Supabase."""
    health: dict[str, str] = {}
    health["neo4j"] = "unknown — wire in §1.2"
    health["qdrant"] = "unknown — wire in §1.3"
    health["supabase"] = "unknown — wire in §1.1"
    health["anthropic_key_present"] = "yes" if os.getenv("ANTHROPIC_API_KEY") else "no"
    return health


if __name__ == "__main__":
    mcp.run()
