"""
Finalize Phase 2.5D validation workflow.

This is intentionally deterministic and no-LLM:
  1. hydrate hypotheses.supporting_papers from real paper UUIDs,
  2. mark five evidence-linked hypotheses as `confirmed` for research follow-up,
  3. export ten JSONL examples for future DSPy prompt optimization.

`confirmed` here means "curated evidence links confirmed for research review";
it is not a clinical treatment recommendation.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from scripts.hypothesis.backfill_supporting_papers import (
    PaperIndex,
    _load_paper_index,
    _resolve_papers,
)
from scripts.ledger import _supabase_creds, _supabase_headers, load_env


ROOT = Path(__file__).resolve().parents[2]
TRAINING_DIR = ROOT / "scripts" / "hypothesis" / "dspy_training"

CONFIRMED_IDS = {
    "97a108f4-d977-4e20-b15d-aa31c0e45624",
    "1e279b31-aac1-4015-bf15-ba3517a161a4",
    "2f60318e-7faa-47a2-8d11-3d8bca81209c",
    "f3b73b2e-e622-4e5d-9596-11078b480e9b",
    "3b28ab79-3797-4ac7-a277-cc41f1efd2a4",
}


@dataclass(frozen=True)
class CuratedFallback:
    title_keywords: tuple[str, ...]
    reason: str


FALLBACKS: dict[str, CuratedFallback] = {
    "fda0a72f-05ca-4a32-9129-4e15f1642ce3": CuratedFallback(
        title_keywords=("GABA Aminotransferase", "Vigabatrin"),
        reason="curated mechanistic GABA-T/vigabatrin evidence for research review",
    ),
    "dbb0e9f4-8bba-48c9-a658-f701317155d9": CuratedFallback(
        title_keywords=("GABA Aminotransferase", "Vigabatrin"),
        reason="curated seizure-control and GABA-T evidence for research review",
    ),
}


def _get(path: str, params: dict[str, str]) -> list[dict[str, Any]]:
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/{path}",
        params=params,
        headers=_supabase_headers(key),
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []


def _patch_hypothesis(hypothesis_id: str, payload: dict[str, Any]) -> None:
    url, key = _supabase_creds()
    r = httpx.patch(
        f"{url}/rest/v1/hypotheses",
        params={"id": f"eq.{hypothesis_id}"},
        json=payload,
        headers={**_supabase_headers(key), "Prefer": "return=minimal"},
        timeout=30,
    )
    r.raise_for_status()


def _append_run(reason: str) -> None:
    url, key = _supabase_creds()
    r = httpx.post(
        f"{url}/rest/v1/runs",
        json={
            "kind": "validation_workflow",
            "agent_id": "phase2_5_validation",
            "exit_status": "completed",
            "exit_reason": reason[:900],
            "tokens_input": 0,
            "tokens_output": 0,
            "token_cost": 0,
        },
        headers={**_supabase_headers(key), "Prefer": "return=minimal"},
        timeout=30,
    )
    r.raise_for_status()


def _load_hypotheses() -> list[dict[str, Any]]:
    return _get(
        "hypotheses",
        {
            "select": (
                "id,title,description,hypothesis_type,confidence_level,"
                "novelty_score,feasibility_score,status,ai_reasoning,"
                "supporting_papers,recommended_action"
            ),
            "order": "created_at.asc",
        },
    )


def _load_papers() -> list[dict[str, Any]]:
    return _get(
        "papers",
        {"select": "id,title,pmid,doi,ct_id,relevance_score", "limit": "1000"},
    )


def _fallback_papers(hypothesis_id: str, papers: list[dict[str, Any]]) -> list[str]:
    fallback = FALLBACKS.get(hypothesis_id)
    if not fallback:
        return []

    matched: list[str] = []
    for paper in papers:
        title = str(paper.get("title") or "")
        if any(keyword.lower() in title.lower() for keyword in fallback.title_keywords):
            pid = paper.get("id")
            if pid:
                matched.append(str(pid))
    return list(dict.fromkeys(matched))[:2]


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:56] or "hypothesis"


def _example_for(
    hypothesis: dict[str, Any],
    supporting_papers: list[str],
    status: str,
    reviewed_at: str,
) -> dict[str, Any]:
    return {
        "hypothesis_id": hypothesis["id"],
        "title": hypothesis.get("title"),
        "input": {
            "description": hypothesis.get("description"),
            "hypothesis_type": hypothesis.get("hypothesis_type"),
            "ai_reasoning": hypothesis.get("ai_reasoning"),
        },
        "expected": {
            "status": status,
            "confidence_level": hypothesis.get("confidence_level"),
            "novelty_score": hypothesis.get("novelty_score"),
            "feasibility_score": hypothesis.get("feasibility_score"),
            "supporting_paper_ids": supporting_papers,
        },
        "curation": {
            "reviewed_at": reviewed_at,
            "curator": "phase2_5_finalize_validation.py",
            "meaning": (
                "research evidence-link validation only; not a medical recommendation"
            ),
        },
    }


def _write_training_files(examples: list[dict[str, Any]], *, apply: bool) -> None:
    if not apply:
        return
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    for i, example in enumerate(examples, start=1):
        title = str(example.get("title") or example["hypothesis_id"])
        path = TRAINING_DIR / f"{i:02d}_{_slug(title)}.jsonl"
        path.write_text(json.dumps(example, ensure_ascii=True) + "\n", encoding="utf-8")


def finalize(*, apply: bool = False) -> int:
    load_env()
    index: PaperIndex = _load_paper_index()
    hypotheses = _load_hypotheses()
    papers = _load_papers()
    reviewed_at = datetime.now(timezone.utc).isoformat()

    examples: list[dict[str, Any]] = []
    hydrated = 0
    confirmed = 0

    for hypothesis in hypotheses:
        hypothesis_id = str(hypothesis["id"])
        resolved = _resolve_papers(index, hypothesis.get("ai_reasoning"))
        fallback = _fallback_papers(hypothesis_id, papers)
        supporting_papers = list(dict.fromkeys([*resolved, *fallback]))

        if supporting_papers:
            hydrated += 1

        status = (
            "confirmed"
            if hypothesis_id in CONFIRMED_IDS
            else (hypothesis.get("status") or "under_review")
        )
        if status == "new":
            status = "under_review"
        if status == "confirmed":
            confirmed += 1

        note_bits = [
            "Phase 2.5D research validation: supporting paper UUIDs hydrated",
            "evidence links curated for follow-up",
            "not a clinical treatment recommendation",
        ]
        if hypothesis_id in FALLBACKS and fallback:
            note_bits.append(FALLBACKS[hypothesis_id].reason)
        outcome = "; ".join(note_bits)

        examples.append(
            _example_for(hypothesis, supporting_papers, status, reviewed_at)
        )

        print(
            f"{'UPDATE' if apply else 'DRY-RUN'} {hypothesis_id} "
            f"status={status} papers={len(supporting_papers)}"
        )
        if apply:
            _patch_hypothesis(
                hypothesis_id,
                {
                    "supporting_papers": supporting_papers,
                    "status": status,
                    "reviewed_at": reviewed_at if status == "confirmed" else None,
                    "outcome": outcome,
                },
            )

    _write_training_files(examples, apply=apply)
    reason = (
        f"hydrated={hydrated}/{len(hypotheses)} confirmed={confirmed} "
        f"dspy_examples={len(examples)}"
    )
    if apply:
        _append_run(reason)
    print(f"summary: {reason} apply={apply}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write DB/files.")
    args = parser.parse_args()
    return finalize(apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
