"""
relevance.py — Phase 2.5B paper-relevance classifier.

Scores newly-ingested papers against Aleksandra's specific clinical context
(severe HIE, diffuse cystic encephalomalacia, preserved brainstem, 9-month
neonatal stage) and writes:

  - papers.relevance_score          (double precision, 0..1)
  - papers.direct_relevance         (bool)   — HIE / hypoxic ischemic injury
  - papers.cross_disease_relevance  (bool)   — TBI, stroke, perinatal asphyxia
  - papers.cross_disease_source     (text)   — e.g., "TBI", "perinatal stroke"

One Haiku 4.5 call per paper. Cost @ ~$0.0002/paper × 70 expected new papers
in 2.5B = ~$0.014 — comfortably under the $1.50 sub-phase budget.

OR-2 fallback contract: every call goes through `scripts.cognition.llm.call_claude`,
so a transient failure is logged as a failed-status `runs` row automatically.
This module then catches the exception, leaves `relevance_score = NULL`, and
returns control to the caller — perception ingest continues regardless.

Usage:
    # Score one paper (called from perception_tick after a fetch_* loop)
    from scripts.scoring.relevance import score_and_write
    score_and_write(paper_id="<uuid>")

    # Batch-backfill all unscored papers (one-off or n8n cron)
    python -m scripts.scoring.relevance --backfill
    python -m scripts.scoring.relevance --backfill --limit 50
    python -m scripts.scoring.relevance --backfill --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from typing import Any

import httpx

from scripts.cognition.llm import call_llm
from scripts.ledger import _supabase_creds, _supabase_headers, load_env

# MODEL is legacy/reference only — the model is now picked by the worker tier
# in scripts.cognition.models (task="relevance"). Kept for documentation.
MODEL = "claude-haiku-4-5-20251001"
TEMPERATURE = 0.1
MAX_TOKENS = 400
AGENT_ID = "analyzer_relevance"

SYSTEM_PROMPT = """\
You score research papers for relevance to a single patient: Aleksandra Jincharadze,
a 9-month-old child with severe hypoxic-ischemic encephalopathy (HIE), diffuse cystic
encephalomalacia (multifocal cavitary lesions, primarily fronto-parietal), and a
preserved brainstem. The family is investigating treatment options inside the
neuroplasticity window (0–2 years).

For each paper (title + abstract), return JSON only, no markdown:

  {
    "relevance_score":         float,   # 0.0..1.0
    "direct_relevance":        bool,    # true if paper is about HIE / hypoxic-ischemic injury / neonatal encephalopathy
    "cross_disease_relevance": bool,    # true if paper is about a related condition that may transfer mechanistically (TBI, stroke, perinatal asphyxia, infantile spasms, cerebral palsy, white-matter injury)
    "cross_disease_source":    str,     # one short label if cross_disease_relevance=true (e.g. "TBI", "perinatal stroke", "infantile spasms"), else ""
    "rationale":               str      # ≤ 200 chars
  }

Scoring rubric:
  - 0.90–1.00: directly addresses HIE treatment or mechanism with infant data
  - 0.70–0.89: HIE-relevant but adult/animal, or treatment for a related neonatal condition
  - 0.50–0.69: cross-disease (TBI/stroke/etc.) with plausible HIE transfer
  - 0.30–0.49: tangentially relevant (general neuroprotection, broad pediatric)
  - 0.00–0.29: off-topic for this case
"""


@dataclass(frozen=True)
class RelevanceResult:
    score: float | None
    direct: bool
    cross: bool
    cross_source: str
    rationale: str
    raw: str


def _strip_code_fence(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```"):
        first_nl = s.find("\n")
        s = s[first_nl + 1 :].rsplit("```", 1)[0].strip()
    return s


def _coerce_float_0_1(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return max(0.0, min(1.0, f))


def score(title: str, abstract: str) -> RelevanceResult:
    """
    Send one classification request. Never raises — failures return a
    RelevanceResult with score=None so the caller can persist NULL and
    move on (OR-2 fallback contract).
    """
    title = (title or "").strip()
    abstract = (abstract or "").strip()
    if not title and not abstract:
        return RelevanceResult(
            score=None,
            direct=False,
            cross=False,
            cross_source="",
            rationale="empty paper (no title or abstract)",
            raw="",
        )

    prompt = f"## Title\n{title}\n\n## Abstract\n{abstract or '(no abstract available)'}\n\nReturn the JSON."

    try:
        raw = call_llm(
            prompt=prompt,
            agent_id=AGENT_ID,
            task="relevance",  # 🔧 worker tier (DeepSeek via OpenRouter)
            system=SYSTEM_PROMPT,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
    except Exception as e:
        # call_llm already wrote a failed-status `runs` row before re-raising.
        # Caller persists relevance_score = NULL and ingest continues.
        return RelevanceResult(
            score=None,
            direct=False,
            cross=False,
            cross_source="",
            rationale=f"call_claude failed: {type(e).__name__}: {str(e)[:160]}",
            raw="",
        )

    payload_text = _strip_code_fence(raw)
    try:
        data = json.loads(payload_text)
    except json.JSONDecodeError:
        # Try to salvage a JSON object embedded anywhere in the text.
        match = re.search(r"\{.*\}", payload_text, flags=re.DOTALL)
        if not match:
            return RelevanceResult(
                score=None,
                direct=False,
                cross=False,
                cross_source="",
                rationale=f"non-JSON response (len={len(raw)})",
                raw=raw[:600],
            )
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return RelevanceResult(
                score=None,
                direct=False,
                cross=False,
                cross_source="",
                rationale=f"non-JSON response (len={len(raw)})",
                raw=raw[:600],
            )

    if not isinstance(data, dict):
        return RelevanceResult(
            score=None,
            direct=False,
            cross=False,
            cross_source="",
            rationale=f"JSON not an object: {type(data).__name__}",
            raw=raw[:600],
        )

    return RelevanceResult(
        score=_coerce_float_0_1(data.get("relevance_score")),
        direct=bool(data.get("direct_relevance", False)),
        cross=bool(data.get("cross_disease_relevance", False)),
        cross_source=str(data.get("cross_disease_source") or "")[:120],
        rationale=str(data.get("rationale") or "")[:400],
        raw=raw[:1200],
    )


def _fetch_paper(paper_id: str) -> dict[str, Any] | None:
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/papers",
        params={"id": f"eq.{paper_id}", "select": "id,title,abstract,relevance_score"},
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=15,
    )
    r.raise_for_status()
    rows = r.json()
    return rows[0] if rows else None


def _patch_paper(paper_id: str, body: dict[str, Any]) -> bool:
    url, key = _supabase_creds()
    r = httpx.patch(
        f"{url}/rest/v1/papers",
        params={"id": f"eq.{paper_id}"},
        json=body,
        headers={**_supabase_headers(key), "Prefer": "return=minimal"},
        timeout=15,
    )
    return 200 <= r.status_code < 300


def score_and_write(paper_id: str) -> RelevanceResult:
    """
    Score one paper and persist results. Always returns a RelevanceResult;
    if the score is None (Haiku failed), nothing is written and the paper
    keeps relevance_score=NULL for later backfill (OR-2).
    """
    load_env()
    row = _fetch_paper(paper_id)
    if row is None:
        return RelevanceResult(
            score=None,
            direct=False,
            cross=False,
            cross_source="",
            rationale="paper not found",
            raw="",
        )

    result = score(
        title=row.get("title") or "",
        abstract=row.get("abstract") or "",
    )

    if result.score is None:
        # Leave relevance_score = NULL on the row; backfill picks it up later.
        return result

    body: dict[str, Any] = {
        "relevance_score": result.score,
        "direct_relevance": result.direct,
        "cross_disease_relevance": result.cross,
    }
    if result.cross_source:
        body["cross_disease_source"] = result.cross_source

    _patch_paper(paper_id, body)
    return result


def _fetch_unscored(limit: int) -> list[dict[str, Any]]:
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/papers",
        params={
            "select": "id,title,abstract",
            "relevance_score": "is.null",
            "order": "ingested_at.desc",
            "limit": str(limit),
        },
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def backfill(limit: int = 200, *, dry_run: bool = False) -> dict[str, int]:
    """
    Batch-score papers where relevance_score IS NULL. Idempotent: any paper
    that already has a score is skipped at the Supabase filter level.
    """
    load_env()
    rows = _fetch_unscored(limit=limit)
    summary = {
        "seen": len(rows),
        "scored": 0,
        "wrote": 0,
        "skipped_no_text": 0,
        "failed": 0,
    }

    for row in rows:
        pid = str(row["id"])
        title = row.get("title") or ""
        abstract = row.get("abstract") or ""
        if not title and not abstract:
            summary["skipped_no_text"] += 1
            print(f"SKIP   {pid}  (empty title+abstract)")
            continue

        result = score(title=title, abstract=abstract)
        if result.score is None:
            summary["failed"] += 1
            print(f"FAIL   {pid}  {result.rationale[:120]}")
            continue

        summary["scored"] += 1
        marker = "DRY-RUN" if dry_run else "WRITE "
        print(
            f"{marker} {pid}  score={result.score:.2f}  "
            f"direct={result.direct}  cross={result.cross}  "
            f"{(title[:60])!r}"
        )

        if not dry_run:
            body: dict[str, Any] = {
                "relevance_score": result.score,
                "direct_relevance": result.direct,
                "cross_disease_relevance": result.cross,
            }
            if result.cross_source:
                body["cross_disease_source"] = result.cross_source
            if _patch_paper(pid, body):
                summary["wrote"] += 1

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Score papers against Aleksandra's HIE context."
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Batch-score all papers with NULL relevance_score.",
    )
    parser.add_argument(
        "--limit", type=int, default=200, help="Max rows to score in backfill mode."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Backfill mode: compute scores, print them, do NOT write to Supabase.",
    )
    parser.add_argument(
        "--paper-id",
        type=str,
        default=None,
        help="Single-paper mode: score one paper by UUID.",
    )
    args = parser.parse_args()

    if args.paper_id:
        result = score_and_write(args.paper_id)
        print(
            f"paper {args.paper_id}: "
            f"score={result.score}  direct={result.direct}  cross={result.cross}  "
            f"src={result.cross_source!r}  "
            f"rationale={result.rationale[:200]!r}"
        )
        return 0 if result.score is not None else 2

    if args.backfill:
        summary = backfill(limit=args.limit, dry_run=args.dry_run)
        print("\n=== backfill summary ===")
        for k, v in summary.items():
            print(f"  {k:>16}  {v}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
