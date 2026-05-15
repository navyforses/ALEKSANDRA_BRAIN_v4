"""
Backfill hypotheses.supporting_papers from cited source identifiers.

Phase 2 generated hypotheses with useful citation strings in ai_reasoning
(`supporting_source_ids`) but left the structured UUID[] column empty because
the LLM produced PMID/NCT/DOI/source-id strings, not paper UUIDs.

This helper is intentionally standalone and dry-run by default so it can be
used during Phase 2.5 without touching the active verifier/spend/Qdrant work.

Usage:
    python -m scripts.hypothesis.backfill_supporting_papers
    python -m scripts.hypothesis.backfill_supporting_papers --apply
    python -m scripts.hypothesis.backfill_supporting_papers --overwrite --apply
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from scripts.ledger import _supabase_creds, _supabase_headers, load_env


PMID_RE = re.compile(r"(?:PMID[:\s/]*|pubmed/)?\b(\d{6,9})\b", re.IGNORECASE)
NCT_RE = re.compile(r"\bNCT\d{8}\b", re.IGNORECASE)
DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s,;)\]\}]+", re.IGNORECASE)


@dataclass(frozen=True)
class PaperIndex:
    by_pmid: dict[str, str]
    by_nct: dict[str, str]
    by_doi: dict[str, str]


def _get_json(
    path: str, *, params: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/{path}",
        params=params or {},
        headers=_supabase_headers(key),
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise RuntimeError(
            f"Expected list response from {path}, got {type(data).__name__}"
        )
    return data


def _patch_hypothesis(hypothesis_id: str, supporting_papers: list[str]) -> None:
    url, key = _supabase_creds()
    r = httpx.patch(
        f"{url}/rest/v1/hypotheses",
        params={"id": f"eq.{hypothesis_id}"},
        json={"supporting_papers": supporting_papers},
        headers={**_supabase_headers(key), "Prefer": "return=minimal"},
        timeout=30,
    )
    r.raise_for_status()


def _load_paper_index() -> PaperIndex:
    rows = _get_json(
        "papers",
        params={"select": "id,pmid,doi,ct_id"},
    )
    by_pmid: dict[str, str] = {}
    by_nct: dict[str, str] = {}
    by_doi: dict[str, str] = {}

    for row in rows:
        pid = row.get("id")
        if not pid:
            continue
        pmid = str(row.get("pmid") or "").strip()
        doi = str(row.get("doi") or "").strip().lower()
        nct = str(row.get("ct_id") or "").strip().upper()
        if pmid:
            by_pmid[pmid] = pid
        if doi:
            by_doi[doi] = pid
        if nct:
            by_nct[nct] = pid

    return PaperIndex(by_pmid=by_pmid, by_nct=by_nct, by_doi=by_doi)


def _load_hypotheses() -> list[dict[str, Any]]:
    return _get_json(
        "hypotheses",
        params={
            "select": "id,title,ai_reasoning,supporting_papers",
            "order": "created_at.asc",
        },
    )


def _reasoning_to_text_and_sources(ai_reasoning: Any) -> tuple[str, list[str]]:
    if ai_reasoning is None:
        return "", []

    if isinstance(ai_reasoning, dict):
        sources = ai_reasoning.get("supporting_source_ids") or []
        return json.dumps(ai_reasoning, ensure_ascii=True), [str(s) for s in sources]

    text = str(ai_reasoning)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text, []

    if isinstance(parsed, dict):
        sources = parsed.get("supporting_source_ids") or []
        return text, [str(s) for s in sources]
    return text, []


def _extract_identifiers(ai_reasoning: Any) -> tuple[set[str], set[str], set[str]]:
    text, explicit_sources = _reasoning_to_text_and_sources(ai_reasoning)
    haystack = "\n".join([text, *explicit_sources])

    pmids = {m.group(1) for m in PMID_RE.finditer(haystack)}
    ncts = {m.group(0).upper() for m in NCT_RE.finditer(haystack)}
    dois = {m.group(0).rstrip(".").lower() for m in DOI_RE.finditer(haystack)}

    for source in explicit_sources:
        s = source.strip()
        lower = s.lower()
        if lower.startswith("pubmed/"):
            pmids.add(s.split("/", 1)[1])
        elif lower.startswith("ctgov/"):
            ncts.add(s.split("/", 1)[1].upper())
        elif lower.startswith("doi/"):
            dois.add(s.split("/", 1)[1].lower())

    return pmids, ncts, dois


def _resolve_papers(index: PaperIndex, ai_reasoning: Any) -> list[str]:
    pmids, ncts, dois = _extract_identifiers(ai_reasoning)
    resolved: list[str] = []

    for pmid in sorted(pmids):
        paper_id = index.by_pmid.get(pmid)
        if paper_id:
            resolved.append(paper_id)
    for nct in sorted(ncts):
        paper_id = index.by_nct.get(nct)
        if paper_id:
            resolved.append(paper_id)
    for doi in sorted(dois):
        paper_id = index.by_doi.get(doi)
        if paper_id:
            resolved.append(paper_id)

    return list(dict.fromkeys(resolved))


def run(*, apply: bool = False, overwrite: bool = False) -> int:
    load_env()
    index = _load_paper_index()
    hypotheses = _load_hypotheses()

    scanned = 0
    would_update = 0
    updated = 0
    skipped_existing = 0
    unresolved = 0

    for hypothesis in hypotheses:
        scanned += 1
        hypothesis_id = str(hypothesis["id"])
        existing = hypothesis.get("supporting_papers") or []
        if existing and not overwrite:
            skipped_existing += 1
            continue

        resolved = _resolve_papers(index, hypothesis.get("ai_reasoning"))
        title = str(hypothesis.get("title") or hypothesis_id)[:90]

        if not resolved:
            unresolved += 1
            print(f"UNRESOLVED {hypothesis_id}  {title}")
            continue

        would_update += 1
        print(
            f"{'UPDATE' if apply else 'DRY-RUN'} {hypothesis_id} "
            f"papers={len(resolved)}  {title}"
        )
        if apply:
            _patch_hypothesis(hypothesis_id, resolved)
            updated += 1

    print(
        "summary: "
        f"scanned={scanned} "
        f"would_update={would_update} "
        f"updated={updated} "
        f"skipped_existing={skipped_existing} "
        f"unresolved={unresolved}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill hypotheses.supporting_papers from PMID/NCT/DOI citations."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write supporting_papers updates. Default is dry-run.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing supporting_papers arrays instead of skipping them.",
    )
    args = parser.parse_args()
    return run(apply=args.apply, overwrite=args.overwrite)


if __name__ == "__main__":
    raise SystemExit(main())
