"""
got_pipeline.py — Phase 2 sub-phase 2C.

A minimal Graph-of-Thoughts style cross-disease hypothesis generator
implemented as a single Sonnet 4.5 prompt over the graph snapshot.

Why one prompt instead of a 4-step DSPy DAG: at our current scale (≈200
typed entities / 307 facts) the entity neighbourhood that any hypothesis
spans fits comfortably inside one Claude context — the latency, cost,
and prompt-engineering surface area of a multi-step DAG isn't justified.
This module preserves the GoT data contract (decompose -> retrieve ->
evaluate -> prune surfaces as four discrete sections of the JSON output)
so when perception scales to N>1000 papers a real
graphiti -> AGoT pipeline can drop in without changing the hypotheses
table writer.

Inputs (read-only):
  - Neo4j hie_research subgraph (entities + facts from sub-phase 2B)
  - scripts.rag.retrieve.retrieve()  (chunk-level supporting evidence
    for the LLM to ground each hypothesis in)

Output (write):
  - Supabase `hypotheses` rows with status='new' (Phase 0 schema):
      title, description, hypothesis_type, supporting_papers[],
      confidence_level, novelty_score, feasibility_score,
      ai_reasoning, discovery_method, recommended_action,
      generated_by_model, generated_at

Run:
  python -m scripts.hypothesis.got_pipeline run-first
  python -m scripts.hypothesis.got_pipeline run-first --max-hypotheses 5
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone

import httpx
from neo4j import GraphDatabase

from scripts.cognition.llm import call_llm
from scripts.ledger import _supabase_creds, _supabase_headers, load_env
from scripts.rag.retrieve import retrieve

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
MODEL = "claude-sonnet-4-5"  # per CLAUDE.md default
TEMPERATURE = 0.4
MAX_TOKENS = 8192
GROUP_ID = "hie_research"

# Hypothesis types from the Phase 0 schema CHECK constraint:
ALLOWED_HYPOTHESIS_TYPES = {
    "drug_repurposing",
    "pathway_target",
    "combination_therapy",
    "timing_optimization",
    "cross_disease_inference",
    "plasticity_mechanism",
    "biomarker_discovery",
    "technology_application",
    "rehabilitation_innovation",
    "other",
}
ALLOWED_CONFIDENCE = {"high", "moderate", "low", "very_low"}
ALLOWED_URGENCY = {"immediate", "short_term", "medium_term", "long_term"}


# ------------------------------------------------------------------
# Step 1: snapshot the graph for the prompt
# ------------------------------------------------------------------
def _snapshot_graph(limit_entities: int = 60, limit_facts: int = 80) -> dict:
    """
    Lightweight dump of the most-mentioned typed entities + the most
    densely-connected RELATES_TO facts. Used as the seed context that
    the LLM reasons over.
    """
    drv = GraphDatabase.driver(
        os.environ["NEO4J_URI"].replace("localhost", "127.0.0.1"),
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
    )
    with drv.session() as s:
        # Entities grouped by ontology type, top-N by MENTIONS degree
        ent_rows = s.run(
            """
            MATCH (n:Entity {group_id:$gid})
            OPTIONAL MATCH (n)<-[m:MENTIONS]-()
            WITH n, count(m) AS mentions
            RETURN
              n.uuid AS uuid,
              n.name AS name,
              [l IN labels(n) WHERE l <> 'Entity'][0] AS type,
              n.summary AS summary,
              mentions
            ORDER BY mentions DESC
            LIMIT $lim
            """,
            gid=GROUP_ID,
            lim=limit_entities,
        ).data()

        fact_rows = s.run(
            """
            MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity)
            WHERE r.group_id = $gid
            RETURN
              a.name AS source,
              [l IN labels(a) WHERE l <> 'Entity'][0] AS source_type,
              b.name AS target,
              [l IN labels(b) WHERE l <> 'Entity'][0] AS target_type,
              r.fact AS fact,
              toString(r.valid_at) AS valid_at
            ORDER BY r.created_at DESC
            LIMIT $lim
            """,
            gid=GROUP_ID,
            lim=limit_facts,
        ).data()
    drv.close()
    return {"entities": ent_rows, "facts": fact_rows}


# ------------------------------------------------------------------
# Step 2: build the prompt
# ------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are the Hypothesis agent inside ALEKSANDRA_BRAIN, a research system
for Aleksandra Jincharadze — a 9-month-old child with severe
hypoxic-ischemic encephalopathy (HIE), diffuse cystic encephalomalacia,
and a preserved brainstem. Your job is to propose cross-disease, drug-
repurposing, and pathway-level hypotheses the family's clinicians could
investigate.

You must:
  - GROUND every hypothesis in the entities and facts provided. Cite
    the source paper IDs you used.
  - PRIORITISE actionability. The family can pursue trials (Duke EAP),
    repurposed compounds with safety data, and rehabilitation
    innovations. Pure theoretical biology is lower priority.
  - NEVER fabricate citations. If the supplied graph + retrieval do
    not justify a hypothesis, do not invent one.
  - NEVER recommend off-label medications directly to the family. The
    clinician decides; your job is to surface candidates.
  - Avoid "limited outcomes" framing. The 0-2 year neuroplasticity
    window is the operating premise.

Return JSON only — no prose, no markdown fences, no preamble.
Schema (a list of 3-5 objects):
  {
    "title":              str,   # one-line summary
    "description":        str,   # 3-6 sentences, includes mechanism
    "hypothesis_type":    str,   # one of: drug_repurposing, pathway_target,
                                  # combination_therapy, timing_optimization,
                                  # cross_disease_inference, plasticity_mechanism,
                                  # biomarker_discovery, technology_application,
                                  # rehabilitation_innovation, other
    "supporting_source_ids": [str],   # PMID / NCT / DOI strings you cited
    "confidence_level":   str,   # high | moderate | low | very_low
    "novelty_score":      float, # 0..1 (rough self-estimate)
    "feasibility_score":  float, # 0..1
    "urgency":            str,   # immediate | short_term | medium_term | long_term
    "discovery_method":   str,   # one sentence: how you arrived at this
    "ai_reasoning":       str,   # 2-4 sentence chain of thought
    "recommended_action": str,   # what the family / clinician should do next
    "contact_researcher": str    # optional; "" if unknown
  }
"""


def _build_user_prompt(snapshot: dict, retrievals: list[dict]) -> str:
    """Compose the user message: graph snapshot + retrievals + ask."""
    ent_block = "\n".join(
        f"- [{r.get('type') or 'Entity'}] {r['name']}  ({r.get('mentions', 0)} mentions)  — {(r.get('summary') or '')[:140]}"
        for r in snapshot["entities"]
    )
    fact_block = "\n".join(
        f"- ({r.get('source_type', '?')}){r['source']} → ({r.get('target_type', '?')}){r['target']}: {(r['fact'] or '')[:200]}"
        for r in snapshot["facts"]
    )
    retr_block = "\n\n".join(
        f"### Retrieval seed query: {seed['query']}\n"
        + "\n".join(
            f"- {h['source_type']}/{h['source_id']}: {(h['preview'] or '')[:200]}"
            for h in seed["hits"]
        )
        for seed in retrievals
    )

    return f"""\
# Graph snapshot (Phase 2B, group_id=hie_research)

## Top entities by mention count
{ent_block}

## Recent RELATES_TO facts
{fact_block}

# Retrieval context (top chunks for HIE-relevant seed queries)
{retr_block}

# Task
Propose 3-5 actionable hypotheses for Aleksandra's case using the
entities and facts above. Return the JSON list described in the system
prompt. No prose outside the JSON.
"""


# ------------------------------------------------------------------
# Step 3: run the LLM + parse
# ------------------------------------------------------------------
def _call_claude(system: str, user: str) -> str:
    # call_llm() writes one `runs` row (kind='llm_call', agent_id='hypothesis')
    # per request, capturing tokens + USD cost. See scripts.cognition.llm.
    # 🧠 thinker tier — Opus 4.8, gated: short reasoning prompts run on the
    # cheap worker model, long/complex ones escalate (THINKER_COMPLEXITY_MIN).
    return call_llm(
        prompt=user,
        agent_id="hypothesis",
        task="got",
        complexity=len(user),
        system=system,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    ).strip()


def _parse_hypotheses(raw: str) -> list[dict]:
    """
    Defensive JSON parsing. Sonnet 4.5 typically returns a clean array
    but occasionally wraps in markdown — strip those defensively.
    """
    s = raw.strip()
    if s.startswith("```"):
        first_nl = s.find("\n")
        s = s[first_nl + 1 :]
        s = s.rsplit("```", 1)[0].strip()
    try:
        data = json.loads(s)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"LLM did not return valid JSON: {e}\nraw={raw[:400]}")
    if isinstance(data, dict) and "hypotheses" in data:
        data = data["hypotheses"]
    if not isinstance(data, list):
        raise RuntimeError(f"Expected JSON array, got {type(data).__name__}")
    return data


# ------------------------------------------------------------------
# Step 4: write to Supabase
# ------------------------------------------------------------------
def _insert_hypotheses(rows: list[dict]) -> list[str]:
    """Insert into Supabase hypotheses table. Returns new row UUIDs."""
    url, key = _supabase_creds()
    inserted: list[str] = []
    now = datetime.now(timezone.utc).isoformat()

    for h in rows:
        htype = h.get("hypothesis_type") or "other"
        if htype not in ALLOWED_HYPOTHESIS_TYPES:
            htype = "other"
        conf = h.get("confidence_level") or "low"
        if conf not in ALLOWED_CONFIDENCE:
            conf = "low"
        urg = h.get("urgency") or "medium_term"
        if urg not in ALLOWED_URGENCY:
            urg = "medium_term"

        # supporting_papers is UUID[]; the LLM returned source_id strings, not
        # UUIDs. We store the source_id strings in ai_reasoning JSON and leave
        # supporting_papers empty for now — Phase 2.5 will join source_ids
        # back to papers.id and rewrite the array.
        body = {
            "id": str(uuid.uuid4()),
            "title": (h.get("title") or "")[:300],
            "description": (h.get("description") or "")[:4000],
            "hypothesis_type": htype,
            "supporting_papers": [],
            "contradicting_papers": [],
            "related_therapies": [],
            "related_pathways": [],
            "related_brain_regions": [],
            "confidence_level": conf,
            "novelty_score": max(0.0, min(1.0, float(h.get("novelty_score") or 0.5))),
            "feasibility_score": max(
                0.0, min(1.0, float(h.get("feasibility_score") or 0.5))
            ),
            "urgency": urg,
            "ai_reasoning": json.dumps(
                {
                    "reasoning": h.get("ai_reasoning") or "",
                    "discovery_method": h.get("discovery_method") or "",
                    "supporting_source_ids": h.get("supporting_source_ids") or [],
                }
            ),
            "discovery_method": (h.get("discovery_method") or "")[:300],
            "recommended_action": (h.get("recommended_action") or "")[:2000],
            "contact_researcher": (h.get("contact_researcher") or "")[:200],
            "status": "new",
            "generated_by": MODEL,
            "generation_batch": f"phase2c_run_{now}",
        }
        r = httpx.post(
            f"{url}/rest/v1/hypotheses",
            json=body,
            headers={**_supabase_headers(key), "Prefer": "return=representation"},
            timeout=30,
        )
        if r.status_code in (200, 201):
            inserted.append(body["id"])
        else:
            print(f"  insert fail HTTP {r.status_code}: {r.text[:300]}")
    return inserted


# ------------------------------------------------------------------
# Public driver
# ------------------------------------------------------------------
def run_first(max_hypotheses: int = 5) -> dict:
    """One-shot first run. Returns summary dict."""
    load_env()

    seed_queries = [
        "cross-disease neuroprotection in HIE neonates",
        "drug repurposing for cystic encephalomalacia or perinatal brain injury",
        "blood-brain barrier protection in hypoxic ischemic injury",
    ]
    retrievals = []
    for q in seed_queries:
        try:
            res = retrieve(q, top_k=4)
            retrievals.append(
                {
                    "query": q,
                    "hits": [
                        {
                            "source_type": c.source_type,
                            "source_id": c.source_id,
                            "preview": c.text_preview,
                        }
                        for c in res.chunks
                    ],
                }
            )
        except Exception as e:
            print(f"  retrieve fail on {q!r}: {e}")

    snapshot = _snapshot_graph()
    print(
        f"snapshot: {len(snapshot['entities'])} entities, {len(snapshot['facts'])} facts"
    )

    user = _build_user_prompt(snapshot, retrievals)
    raw = _call_claude(SYSTEM_PROMPT, user)

    parsed = _parse_hypotheses(raw)
    parsed = parsed[:max_hypotheses]
    print(f"LLM proposed {len(parsed)} hypotheses")

    ids = _insert_hypotheses(parsed)
    print(f"inserted {len(ids)} rows into Supabase hypotheses")

    return {
        "hypotheses_generated": len(parsed),
        "hypotheses_inserted": len(ids),
        "ids": ids,
        "raw_first_500": raw[:500],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    rf = sub.add_parser("run-first")
    rf.add_argument("--max-hypotheses", type=int, default=5)
    args = p.parse_args()
    if args.cmd == "run-first":
        summary = run_first(max_hypotheses=args.max_hypotheses)
        print("\n=== run-first summary ===")
        for k, v in summary.items():
            if k == "ids":
                print(f"  {k}: {v}")
            elif k == "raw_first_500":
                print(f"  {k}: {v[:200]}...")
            else:
                print(f"  {k}: {v}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
