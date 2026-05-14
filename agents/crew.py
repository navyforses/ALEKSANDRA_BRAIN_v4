"""
ALEKSANDRA_BRAIN — Crew orchestration

Composes all 5 agents into a CrewAI Crew with sequential process.
Phase 0: smoke-test the crew (no tools yet, no real tasks) + verify the
MCP allowlist (FND-06) is loaded before any agent can act.
Phase I+: tools wired, real workflows run on schedule via n8n.
"""
from __future__ import annotations

from crewai import Crew, Process, Task

from agents._mcp_allowlist import allowed_mcps
from agents.spider import build_spider
from agents.analyzer import build_analyzer
from agents.hypothesis import build_hypothesis
from agents.repurposing import build_repurposing
from agents.communicator import build_communicator


def build_crew() -> Crew:
    spider = build_spider()
    analyzer = build_analyzer()
    hypothesis = build_hypothesis()
    repurposing = build_repurposing()
    communicator = build_communicator()

    # FND-06 — print the allowlist so misconfigurations show up in the smoke log.
    for name in ("spider", "analyzer", "hypothesis", "repurposing", "communicator"):
        mcps = allowed_mcps(name)
        print(f"[allowlist] {name:<13} → {', '.join(mcps) if mcps else '(none yet)'}")

    # Phase 0 smoke test: each agent reports status.
    status_tasks = [
        Task(
            description=f"Report your status, role, and readiness.",
            agent=agent,
            expected_output="One sentence: <role> ready.",
        )
        for agent in (spider, analyzer, hypothesis, repurposing, communicator)
    ]

    return Crew(
        agents=[spider, analyzer, hypothesis, repurposing, communicator],
        tasks=status_tasks,
        process=Process.sequential,
        verbose=True,
    )


if __name__ == "__main__":
    crew = build_crew()
    result = crew.kickoff()
    print("\n=== Crew kickoff result ===")
    print(result)
