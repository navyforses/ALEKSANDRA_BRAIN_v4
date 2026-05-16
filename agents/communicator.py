"""
Communicator Agent — Family Liaison

Bridges the system and the family. Urgent findings → Telegram. Weekly briefs
→ email. Borderline evidence → two-way question:
"Include this paper in analysis? [Yes/No]"

The family stays informed and in control. The AI proposes, the family disposes.
"""

from __future__ import annotations

from crewai import Agent

from scripts.communicator.language import detect as detect_language
from scripts.communicator.phi_redactor import redact as redact_phi
from scripts.communicator.summarize import generate_summary

# Day 3 tool registry — callable directly by the verifier, Day 5 outreach
# drafter, and Day 6 weekly brief. CrewAI @tool decoration is intentionally
# deferred until the Crew is actually run; at that point each entry below
# becomes a Tool() instance with the same signature.
COMMUNICATOR_TOOLS = {
    "generate_summary": generate_summary,
    "redact_phi": redact_phi,
    "detect_language": detect_language,
}

TOOLS: list = []  # CrewAI Tool() instances populated when the Crew runs.

BACKSTORY = """
You write for Shalva, Aleksandra's father — a software developer, not a
clinician. Your tone is precise, sourced, and never alarmist. You never
hide bad news; you also never invent good news.

You always cite. You never write "studies show" without naming the studies.
You never write "experts agree" — you name the experts or you say "I don't know".

You translate Latin and clinical jargon into Georgian when relevant, and
you can fall back to English when precision matters more than fluency.
""".strip()


def build_communicator(llm_model: str = "claude-sonnet-4-5") -> Agent:
    return Agent(
        role="Family Liaison",
        goal=(
            "Deliver findings to the family with precision, sourcing, and "
            "appropriate urgency — never alarmist, never hidden."
        ),
        backstory=BACKSTORY,
        tools=TOOLS,
        llm=llm_model,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )
