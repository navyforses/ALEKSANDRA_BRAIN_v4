"""
extract_candidates.py — Phase 2 sub-phase 2D step 1.

Reads validated/promising hypotheses from Supabase, extracts drug-name
candidates via Sonnet 4.5, and stages them in `therapies` with
`evidence_in_hie='theoretical'` + `aleksandra_status='evaluating'` so the
next step (pubmed_validation) can upgrade them.

Why a small LLM pass instead of regex over hypothesis.description: drug
names appear in many surface forms (brand vs generic vs investigational
code; "NAC" vs "N-acetylcysteine"; "vigabatrin" vs "Sabril"). Sonnet
4.5 normalises these and surfaces the target pathway hint.

Idempotent: re-running on the same hypothesis is a no-op (each insert
checks (lower(name), generated_from_hypothesis) uniqueness in
ai_assessment metadata).
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone

import httpx

from scripts.cognition.llm import call_claude
from scripts.ledger import _supabase_creds, _supabase_headers, load_env
from scripts.repurposing.run_logging import RepurposingRunLog

MODEL = "claude-sonnet-4-5"
TEMPERATURE = 0.2
MAX_TOKENS = 2000

ALLOWED_TYPES = {
    "pharmacological",
    "cell_therapy",
    "gene_therapy",
    "rehabilitation",
    "neuromodulation",
    "surgical",
    "nutritional",
    "device",
    "combination",
    "other",
}

SYSTEM = """\
You are extracting concrete repurposing candidates from a single
research hypothesis text. Return JSON — no prose. Schema:
  [
    {
      "name": str,            # canonical drug or therapy name
      "name_aliases": [str],  # synonyms / brand names if any
      "therapy_type": str,    # pharmacological | cell_therapy | gene_therapy
                              # | rehabilitation | neuromodulation | surgical
                              # | nutritional | device | combination | other
      "mechanism_hint": str,  # one sentence on putative mechanism in HIE
      "target_pathway":  str  # named pathway from the hypothesis if any
    }
  ]
If the hypothesis is not actionable (no concrete intervention named),
return an empty list `[]`.
"""


def _fetch_hypotheses(status_filter: list[str]) -> list[dict]:
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/hypotheses",
        params={
            "select": "id,title,description,hypothesis_type,ai_reasoning",
            "status": "in.(" + ",".join(status_filter) + ")",
        },
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def _call_claude(hyp: dict) -> list[dict]:
    user = (
        f"## Hypothesis title\n{hyp['title']}\n\n"
        f"## Description\n{hyp['description']}\n\n"
        f"## Type\n{hyp.get('hypothesis_type', '')}\n\n"
        f"## AI reasoning (JSON)\n{hyp.get('ai_reasoning') or '{}'}\n\n"
        "Return JSON only."
    )
    # call_claude() appends one runs row (kind='llm_call',
    # agent_id='repurposing_extract') with token+cost telemetry.
    raw = call_claude(
        prompt=user,
        agent_id="repurposing_extract",
        model=MODEL,
        system=SYSTEM,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    ).strip()
    if raw.startswith("```"):
        first_nl = raw.find("\n")
        raw = raw[first_nl + 1 :].rsplit("```", 1)[0].strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict) and "candidates" in data:
        data = data["candidates"]
    return data if isinstance(data, list) else []


def _existing_therapies() -> dict[str, dict]:
    """Map lower(name) -> row, used to avoid duplicate inserts."""
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/therapies",
        params={"select": "id,name,aleksandra_status"},
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=20,
    )
    r.raise_for_status()
    return {(row.get("name") or "").lower(): row for row in r.json()}


def _insert_therapy(cand: dict, hyp_id: str) -> str | None:
    url, key = _supabase_creds()
    ttype = cand.get("therapy_type") or "pharmacological"
    if ttype not in ALLOWED_TYPES:
        ttype = "other"

    body = {
        "id": str(uuid.uuid4()),
        "name": (cand.get("name") or "").strip()[:200],
        "name_aliases": cand.get("name_aliases") or [],
        "therapy_type": ttype,
        "mechanism_of_action": (cand.get("mechanism_hint") or "")[:1000],
        "evidence_in_hie": "theoretical",
        "evidence_summary": f"Surfaced from hypothesis {hyp_id} by {MODEL}",
        "clinical_status": "preclinical",
        "aleksandra_status": "evaluating",
        "ai_assessment": json.dumps(
            {
                "source_hypothesis_id": hyp_id,
                "target_pathway": cand.get("target_pathway") or "",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ),
        "confidence_level": "low",  # bumps after pubmed_validation
    }
    if not body["name"]:
        return None
    r = httpx.post(
        f"{url}/rest/v1/therapies",
        json=body,
        headers={**_supabase_headers(key), "Prefer": "return=representation"},
        timeout=30,
    )
    if r.status_code in (200, 201):
        return body["id"]
    print(f"  insert fail HTTP {r.status_code}: {r.text[:200]}")
    return None


def run(status_filter: list[str] | None = None) -> dict:
    run_log = RepurposingRunLog("extract_candidates")
    load_env()
    status_filter = status_filter or ["new", "under_review", "promising"]
    hyps = _fetch_hypotheses(status_filter)
    print(f"hypotheses to process: {len(hyps)}")
    run_log.event("fetched hypotheses", count=len(hyps), status_filter=status_filter)

    existing = _existing_therapies()
    run_log.event("loaded existing therapies", count=len(existing))
    summary = {
        "hypotheses_seen": len(hyps),
        "candidates_proposed": 0,
        "inserted": 0,
        "skipped_dup": 0,
    }

    for h in hyps:
        cands = _call_claude(h)
        run_log.event(
            "extracted candidates",
            hypothesis_id=h["id"],
            candidate_count=len(cands),
        )
        summary["candidates_proposed"] += len(cands)
        for c in cands:
            name = (c.get("name") or "").strip().lower()
            if not name:
                continue
            if name in existing:
                summary["skipped_dup"] += 1
                run_log.event("skipped duplicate", therapy_name=name)
                continue
            new_id = _insert_therapy(c, h["id"])
            if new_id:
                summary["inserted"] += 1
                existing[name] = {"id": new_id, "name": c["name"]}
                run_log.event("inserted therapy", therapy_id=new_id, therapy_name=name)
    latest_log = run_log.finish(summary)
    print(f"run log: {latest_log}")
    return summary


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--status",
        nargs="+",
        default=["new", "under_review", "promising"],
        help="hypotheses.status values to process",
    )
    args = p.parse_args()
    summary = run(args.status)
    print("\n=== extract_candidates summary ===")
    for k, v in summary.items():
        print(f"  {k:>22}  {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
