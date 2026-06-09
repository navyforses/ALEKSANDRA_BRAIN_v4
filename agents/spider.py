"""
Spider Agent — Research Paper Hunter

Runs every 6 hours. Searches PubMed, bioRxiv, medRxiv, ClinicalTrials.gov,
and 11 additional academic sources for new HIE-relevant publications, including
cross-disease inference (e.g. surfacing diabetes drugs with neuroprotective signals).
"""

from __future__ import annotations

from crewai import Agent

from scripts.cognition import models

from agents.tools.spider_tools import check_ledger_new, trigger_chunking

# Phase 2 cross-cutting wiring (sub-phase 2-cross). These two tools let the
# Spider check what Phase 1's perception_tick dropped in evidence_ledger
# during the last cron window and kick off Phase 2A chunking for any rows
# that haven't been chunked yet. Phase 3 will add a PubMed-search tool.
TOOLS: list = [check_ledger_new, trigger_chunking]

BACKSTORY = """
You hunt scientific literature for Aleksandra Jintcharadze, a child born on
August 28, 2025 with severe HIE and diffuse cystic encephalomalacia. Her
brainstem is preserved. The 0-2 year neuroplasticity window is open.

You search broadly — HIE directly, and adjacent fields (stroke, neuroinflammation,
metabolic disease) where a treatment might cross over. Metformin's neuroprotective
signal was found by exactly this cross-disease pattern.

You are tireless, systematic, and never assume a search is "done".
""".strip()


def build_spider(llm_model: str | None = None) -> Agent:
    llm_model = llm_model or models.crew_llm("worker")  # 🔧 worker tier
    return Agent(
        role="Research Paper Hunter",
        goal=(
            "Discover every published paper, preprint, and trial relevant to "
            "pediatric HIE — directly or by cross-disease inference."
        ),
        backstory=BACKSTORY,
        tools=TOOLS,
        llm=llm_model,
        verbose=True,
        allow_delegation=False,
        max_iter=15,
    )
