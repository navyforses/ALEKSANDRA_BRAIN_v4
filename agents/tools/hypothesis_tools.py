"""
hypothesis_tools.py — Phase 2 Hypothesis agent tools.

Two wrappers around the 2C pipeline:

  run_hypothesis_generation()  → kicks off the GoT-lite pipeline once. Sonnet
      4.5 reads the graph snapshot + retrievals, drafts 3-5 hypotheses, and
      inserts them as Supabase rows with status='new'.

  validate_hypothesis(hypothesis_id) → reads one row from Supabase and runs
      deterministic sanity rules (does every supporting_paper round-trip to
      evidence_ledger? does the title contain a Drug/Disease/Pathway entity
      that exists in Neo4j?). Returns a checklist dict the human can flip
      to 'promising' or 'rejected'.
"""

from __future__ import annotations

import json
import os

import httpx
from crewai.tools import tool
from neo4j import GraphDatabase

from scripts.hypothesis.validate import validate
from scripts.ledger import _supabase_creds, _supabase_headers, load_env


@tool("run_hypothesis_generation")
def run_hypothesis_generation(max_hypotheses: int = 5) -> str:
    """Run the GoT-lite hypothesis pipeline once. Sonnet 4.5 generates 3-5
    hypotheses grounded in the current graph + recent retrievals and writes
    them to Supabase hypotheses with status='new'. Returns JSON summary."""
    from scripts.hypothesis.got_pipeline import run_first

    load_env()
    summary = run_first(max_hypotheses=max_hypotheses)
    return json.dumps({k: v for k, v in summary.items() if k != "raw_first_500"})


@tool("validate_hypothesis")
def validate_hypothesis(hypothesis_id: str) -> str:
    """Deterministic 5-rule sanity check on one hypothesis row. Returns a
    JSON checklist plus a `passing` boolean (≥3/5 rules satisfied)."""
    load_env()
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/hypotheses",
        params={
            "select": "id,title,description,confidence_level,supporting_papers,"
            "novelty_score,contact_researcher,recommended_action",
            "id": f"eq.{hypothesis_id}",
            "limit": "1",
        },
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=15,
    )
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return json.dumps({"error": f"hypothesis {hypothesis_id} not found"})
    h = rows[0]

    # Rule 3 input: which supporting_papers resolve in evidence_ledger.
    sp = h.get("supporting_papers") or []
    real: set[str] = set()
    if sp:
        id_list = ",".join(f'"{i}"' for i in sp)
        r = httpx.get(
            f"{url}/rest/v1/evidence_ledger",
            params={"select": "id", "id": f"in.({id_list})"},
            headers=_supabase_headers(key, prefer="count=none"),
            timeout=15,
        )
        real = {str(row["id"]) for row in r.json()} if r.status_code == 200 else set()

    # Rule 4 input: does the title ground in a real Neo4j entity?
    drv = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
    )
    title_words = {
        w.strip(".,;:()[]").lower()
        for w in (h.get("title") or "").split()
        if len(w) > 3
    }
    matched_entity: str | None = None
    with drv.session() as s:
        for word in title_words:
            row = s.run(
                "MATCH (n:Entity {group_id:'hie_research'}) "
                "WHERE toLower(n.name) CONTAINS $w "
                "RETURN n.name AS name LIMIT 1",
                w=word,
            ).single()
            if row:
                matched_entity = row["name"]
                break
    drv.close()

    # Single source of truth: the same pure rules got_pipeline gates on.
    result = validate(h, ledger_ids=real, entity_match=matched_entity is not None)
    return json.dumps(
        {
            "hypothesis_id": hypothesis_id,
            "title": h.get("title"),
            "checks": result["checks"],
            "passing": result["passing"],
            "passing_count": result["passing_count"],
            "matched_entity": matched_entity,
        }
    )


__all__ = ["run_hypothesis_generation", "validate_hypothesis"]
