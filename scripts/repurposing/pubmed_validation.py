"""
pubmed_validation.py — Phase 2 sub-phase 2D step 2.

For each therapy with aleksandra_status='evaluating' and
evidence_in_hie='theoretical', query PubMed via NCBI E-utilities for the
intersection of (drug name) AND (HIE OR neonatal brain injury) and
record the literature footprint.

Updates the therapy row with:
  - evidence_in_hie:    upgraded from 'theoretical' to one of
                        {'preclinical','experimental','promising','proven'}
                        based on the count + recency + study-type
                        signals found.
  - evidence_summary:   short prose dossier from the LLM
  - ai_assessment:      JSON with prior_evidence_count, recent_year,
                        has_pediatric_data, top PMIDs

Uses scripts.fetch_pubmed helpers (configure_entrez, _esearch_pmids,
_efetch_xml, _xml_to_metadata) so NCBI rate limits + the registered
api_key stay consistent with PRC-01.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import httpx

from scripts.cognition.llm import call_claude
from scripts.fetch_pubmed import (
    _efetch_xml,
    _esearch_pmids,
    _xml_to_metadata,
    configure_entrez,
)
from scripts.ledger import _supabase_creds, _supabase_headers, load_env

MODEL = "claude-sonnet-4-5"
TEMPERATURE = 0.2
MAX_TOKENS = 1500
PUBMED_RETMAX = 5  # top-5 hits per drug; small enough to stay polite

# Heuristic upgrade table from PubMed signals
HIE_QUERY_SUFFIX = (
    "AND (hypoxic ischemic encephalopathy OR neonatal brain injury "
    "OR cystic encephalomalacia OR HIE)"
)
PEDIATRIC_TERMS = ("infant", "neonat", "newborn", "pediatric", "child")


def _query_pubmed(drug_name: str) -> dict:
    """Return {pmids, top_meta, recent_year, has_pediatric_data}."""
    q = f'"{drug_name}" {HIE_QUERY_SUFFIX}'
    try:
        pmids = _esearch_pmids(q, retmax=PUBMED_RETMAX)
    except Exception as e:
        return {
            "pmids": [],
            "top_meta": [],
            "recent_year": None,
            "has_pediatric_data": False,
            "error": str(e),
        }

    top_meta: list[dict] = []
    recent_year: int | None = None
    has_pediatric_data = False
    for pmid in pmids:
        try:
            xml = _efetch_xml(pmid)
            meta = _xml_to_metadata(xml, pmid)
            year = meta.get("publication_year")
            if year and (recent_year is None or int(year) > recent_year):
                recent_year = int(year)
            text = " ".join(
                str(v) for v in (meta.get("title"), meta.get("abstract"))
            ).lower()
            if any(t in text for t in PEDIATRIC_TERMS):
                has_pediatric_data = True
            top_meta.append(
                {
                    "pmid": pmid,
                    "title": meta.get("title"),
                    "year": year,
                    "journal": meta.get("journal"),
                }
            )
            time.sleep(0.12)  # NCBI 10 req/sec ceiling with api_key
        except Exception:
            continue
    return {
        "pmids": pmids,
        "top_meta": top_meta,
        "recent_year": recent_year,
        "has_pediatric_data": has_pediatric_data,
    }


def _classify_evidence(signals: dict) -> str:
    """Map PubMed signals -> evidence_in_hie CHECK constraint value."""
    n = len(signals.get("pmids") or [])
    recent = signals.get("recent_year") or 0
    pediatric = signals.get("has_pediatric_data") or False
    if n >= 3 and recent >= 2020 and pediatric:
        return "promising"
    if n >= 2 and recent >= 2018:
        return "experimental"
    if n >= 1:
        return "preclinical"
    return "theoretical"


def _llm_dossier(name: str, signals: dict, hyp_context: str) -> str:
    """One-paragraph clinician-readable dossier."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return f"PubMed: {len(signals['pmids'])} hits; recent year {signals.get('recent_year')}; pediatric data {signals.get('has_pediatric_data')}."
    sys_msg = (
        "Write a single 4-6 sentence clinician dossier for the named "
        "repurposing candidate. Use only the supplied PubMed signals and "
        "hypothesis context. State plainly whether the literature supports "
        "or doesn't support pursuing this in HIE. No fabricated PMIDs."
    )
    user = (
        f"## Candidate\n{name}\n\n"
        f"## Hypothesis context\n{hyp_context}\n\n"
        f"## PubMed signals\n{json.dumps(signals, indent=2)}\n\n"
        "Write the dossier paragraph."
    )
    # call_claude() appends one runs row (kind='llm_call',
    # agent_id='repurposing_dossier') with token+cost telemetry.
    return call_claude(
        prompt=user,
        agent_id="repurposing_dossier",
        model=MODEL,
        system=sys_msg,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    ).strip()


def _fetch_candidates_to_validate() -> list[dict]:
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/therapies",
        params={
            "select": "id,name,name_aliases,mechanism_of_action,ai_assessment,evidence_in_hie,aleksandra_status",
            "evidence_in_hie": "eq.theoretical",
            "aleksandra_status": "eq.evaluating",
        },
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def _update_therapy(t_id: str, body: dict) -> bool:
    url, key = _supabase_creds()
    r = httpx.patch(
        f"{url}/rest/v1/therapies",
        params={"id": f"eq.{t_id}"},
        json=body,
        headers={**_supabase_headers(key), "Prefer": "return=representation"},
        timeout=30,
    )
    if r.status_code in (200, 204):
        return True
    print(f"  patch fail HTTP {r.status_code}: {r.text[:200]}")
    return False


def run(limit: int | None = None) -> dict:
    load_env()
    configure_entrez()
    cands = _fetch_candidates_to_validate()
    if limit:
        cands = cands[:limit]
    print(f"candidates to validate: {len(cands)}")
    summary = {
        "seen": len(cands),
        "validated": 0,
        "upgraded_evidence": 0,
        "errors": 0,
    }
    for c in cands:
        name = c.get("name") or ""
        if not name:
            continue
        print(f"  ↪ {name}")
        try:
            signals = _query_pubmed(name)
            new_ev = _classify_evidence(signals)
            existing = (
                json.loads(c.get("ai_assessment") or "{}")
                if isinstance(c.get("ai_assessment"), str)
                else (c.get("ai_assessment") or {})
            )
            dossier = _llm_dossier(
                name,
                signals,
                hyp_context=c.get("mechanism_of_action") or "",
            )
            new_ai = {
                **existing,
                "validated_at": datetime.now(timezone.utc).isoformat(),
                "pubmed_signals": signals,
                "dossier": dossier,
            }
            updated = _update_therapy(
                c["id"],
                {
                    "evidence_in_hie": new_ev,
                    "evidence_summary": dossier[:2000],
                    "ai_assessment": json.dumps(new_ai),
                },
            )
            if updated:
                summary["validated"] += 1
                if new_ev != "theoretical":
                    summary["upgraded_evidence"] += 1
                print(
                    f"     → {new_ev}  ({len(signals['pmids'])} pmids, recent {signals.get('recent_year')})"
                )
        except Exception as e:
            summary["errors"] += 1
            print(f"     [err] {type(e).__name__}: {e}")
    return summary


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()
    summary = run(limit=args.limit)
    print("\n=== pubmed_validation summary ===")
    for k, v in summary.items():
        print(f"  {k:>22}  {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
