"""
Phase 0 smoke test — verify all 5 CrewAI agents initialize.

Run:
    python scripts/test_crew.py

Expected:
    ✅ All 5 agents initialized
    Spider, Analyzer, Hypothesis, Repurposing, Communicator all report ready.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `agents/` importable when run from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.crew import build_crew


def main() -> int:
    print("=== ALEKSANDRA_BRAIN — Phase 0 smoke test ===\n")
    try:
        crew = build_crew()
    except Exception as exc:
        print(f"❌ Crew failed to build: {exc}")
        return 1

    agent_count = len(crew.agents)
    if agent_count != 5:
        print(f"❌ Expected 5 agents, got {agent_count}")
        return 1

    for agent in crew.agents:
        print(f"  ✅ {agent.role:<35} initialized")

    print("\n✅ All 5 agents initialized.")
    print("Next: wire tools (PubMed, Crawl4AI, Supabase, Qdrant, Graphiti, n8n).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
