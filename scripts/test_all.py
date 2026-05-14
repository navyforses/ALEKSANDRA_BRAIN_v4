"""
ALEKSANDRA_BRAIN — Phase 0 final verification (§8)

Runs the 10-point checklist from PHASE_0_HANDOUT.md §8.
Each check returns PASS / FAIL. Final verdict at the bottom.

Run:
    python scripts/test_all.py
"""

from __future__ import annotations

import os
import sys
from typing import Callable


def check_supabase() -> tuple[bool, str]:
    return False, "TODO §1.1 — Supabase not yet wired"


def check_neo4j() -> tuple[bool, str]:
    return False, "TODO §1.2 — Neo4j not yet wired"


def check_qdrant() -> tuple[bool, str]:
    return False, "TODO §1.3 — Qdrant not yet wired"


def check_n8n() -> tuple[bool, str]:
    return False, "TODO §2.1 — n8n not yet wired"


def check_telegram() -> tuple[bool, str]:
    return False, "TODO §2.2 — Telegram not yet wired"


def check_crewai() -> tuple[bool, str]:
    try:
        from agents.crew import build_crew

        crew = build_crew()
        return (len(crew.agents) == 5, f"{len(crew.agents)} agents initialized")
    except Exception as exc:
        return False, f"crew build failed: {exc}"


def check_mem0() -> tuple[bool, str]:
    return False, "TODO §3.3 — mem0 not yet wired"


def check_mcp() -> tuple[bool, str]:
    try:
        from mcp import hello_brain  # noqa: F401

        return True, "hello_brain importable"
    except Exception as exc:
        return False, f"import failed: {exc}"


def check_vercel() -> tuple[bool, str]:
    return False, "TODO §4.2 — Vercel not yet wired"


def check_docker() -> tuple[bool, str]:
    return False, "TODO §4.3 — docker-compose not verified"


CHECKS: list[tuple[str, Callable[[], tuple[bool, str]]]] = [
    ("Supabase", check_supabase),
    ("Neo4j", check_neo4j),
    ("Qdrant", check_qdrant),
    ("n8n", check_n8n),
    ("Telegram", check_telegram),
    ("CrewAI", check_crewai),
    ("mem0", check_mem0),
    ("FastMCP", check_mcp),
    ("Vercel", check_vercel),
    ("Docker", check_docker),
]


def main() -> int:
    print("=== Phase 0 — Final verification ===\n")
    passed = 0
    for name, check in CHECKS:
        ok, msg = check()
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {status}  {name:<12} — {msg}")
        passed += int(ok)

    print(f"\n{passed}/{len(CHECKS)} checks passed.")
    if passed == len(CHECKS):
        print("✅ Phase 0 complete. Ready for Phase I (Research Intelligence).")
        return 0
    return 1


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.exit(main())
