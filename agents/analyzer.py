"""
Analyzer Agent — Evidence Quality Assessor

Processes every paper Spider finds. Parses PDFs (tables + figures), extracts
entities (drugs, genes, pathways, brain regions), assigns relevance scores,
stores everything in a temporal knowledge graph with confidence decay.

A 2019 case report carries less weight than a 2025 RCT — the graph remembers.
"""

from __future__ import annotations

from crewai import Agent

from agents.tools.analyzer_tools import neo4j_stats, run_graphiti

# Phase 2 cross-cutting wiring. Analyzer turns a chunked paper into typed
# Graphiti entities + RELATES_TO facts; neo4j_stats lets the agent monitor
# how the hie_research subgraph is growing (or stagnating).
TOOLS: list = [run_graphiti, neo4j_stats]

BACKSTORY = """
You read papers the way a careful clinician reads charts: every claim earns
its place by evidence level, sample size, and time-of-publication. You are
suspicious of single case reports and reverent toward well-powered RCTs.

Your output is structured — every paper becomes a node in the knowledge
graph with extracted entities, relevance score (0-1), evidence level (1-7),
key findings, limitations, and explicit implications for Aleksandra.

You never invent a finding the paper does not support.
""".strip()


def build_analyzer(llm_model: str = "claude-sonnet-4-5") -> Agent:
    return Agent(
        role="Evidence Quality Assessor",
        goal=(
            "Parse, score, and structure every paper into the temporal "
            "knowledge graph with extracted entities and explicit relevance."
        ),
        backstory=BACKSTORY,
        tools=TOOLS,
        llm=llm_model,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )
