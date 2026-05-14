"""
Hypothesis Agent — Cross-Disease Pattern Finder

Runs weekly. Traverses the knowledge graph looking for patterns humans miss:
"Drug X targets Pathway Y → Pathway Y active in Region Z → Region Z damaged
in Aleksandra but has moderate plasticity. No one has tested Drug X for HIE."

Output ranked by confidence × novelty × feasibility.
"""

from __future__ import annotations

from crewai import Agent

TOOLS: list = []

BACKSTORY = """
You think across disease boundaries. PubMed indexes by diagnosis; you index
by molecular target, pathway, and brain region. Your job is to find the
hypotheses that fall between the cracks of single-disease silos.

Every hypothesis you produce is a structured object: title, mechanism,
supporting evidence (paper IDs with confidence), contradicting evidence,
testability, and feasibility for Aleksandra's specific damage map.

You rank by novelty, but you never sacrifice rigor for novelty.
""".strip()


def build_hypothesis(llm_model: str = "claude-sonnet-4-5") -> Agent:
    return Agent(
        role="Cross-Disease Pattern Finder",
        goal=(
            "Generate testable cross-disease hypotheses by traversing the "
            "knowledge graph for under-explored target/pathway/region overlaps."
        ),
        backstory=BACKSTORY,
        tools=TOOLS,
        llm=llm_model,
        verbose=True,
        allow_delegation=True,
        max_iter=20,
    )
