"""
analyze_paper.py — Evidence Refinery Stage 2 (REASON): per-paper deep analysis.

Fills the analysis fields the family-facing site already reads but which today
are populated only for repurposing candidates (extract_candidates.py /
pubmed_validation.py). Every other paper sits as a raw abstract — no
"what this means for Aleksandra", no evidence grade. This module closes that gap.

Writes back to the `papers` table (columns from scripts/schema.sql):

  ai_summary                  JSONB      {en, ka} plain-language 3-4 sentence
                                         summary (migration 026 made this
                                         bilingual; we write en, ka backfilled
                                         from the digest cache / migration 025)
  ai_key_findings             TEXT[]     PICO-aware key findings (population /
                                         intervention / outcome / study type)
  ai_aleksandra_implications  JSONB      {en, ka} "what this means for Aleksandra",
                                         non-prescriptive, honest about limits
  evidence_level              INT 1-7    GRADE-like tier (1 = meta-analysis …
                                         7 = single anecdote / unverified)
  confidence_level            enum       high | moderate | low | very_low

One structured LLM call per paper, routed through scripts.cognition.llm.call_llm
with task="analyze_paper" (thinker tier, complexity-gated: short abstracts run on
the cheap thinker_light model, long/complex ones escalate to Opus 4.8 — see
scripts.cognition.models). Every call writes one `runs` row + passes the daily-
budget gate, exactly like scripts.scoring.relevance and got_pipeline.

Anti-fabrication contract (the project's first rule, mirrored from relevance.py
and summarize.py):
  - Grounds every finding in the supplied abstract. If the abstract is missing
    or too thin to support analysis, the model sets insufficient_evidence=true
    and writes an honest "limited evidence" summary rather than inventing detail.
  - Never prescribes a treatment, never predicts an outcome (CGM-04 stance).
  - Never raises on a model/parse failure: the paper is left unanalyzed (fields
    stay NULL) so a later backfill retries — perception/ingest is never blocked.

Selection (backfill): only papers that are (a) already relevance-scored at or
above --min-relevance AND (b) not yet analysed (ai_summary IS NULL). This is the
cost-optimal funnel from the RFC — relevance.py screens all 608 cheaply first,
then this stage spends the expensive reasoning model only on the relevant subset.
Idempotent: an already-analysed paper is skipped at the Supabase filter level.

Usage
-----
    # One paper
    python -m scripts.analysis.analyze_paper --paper-id <uuid>

    # Backfill the relevant, unanalysed papers (newest-relevant first)
    python -m scripts.analysis.analyze_paper --backfill --min-relevance 0.5
    python -m scripts.analysis.analyze_paper --backfill --limit 50 --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any

import httpx

from scripts.cognition.llm import call_llm
from scripts.ledger import _supabase_creds, _supabase_headers, load_env

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
AGENT_ID = "analyzer_paper"
TASK = "analyze_paper"  # thinker tier, complexity-gated (scripts.cognition.models)
TEMPERATURE = 0.2
MAX_TOKENS = 1100

DEFAULT_MIN_RELEVANCE = 0.5
DEFAULT_BACKFILL_LIMIT = 200
MAX_KEY_FINDINGS = 6
MAX_FINDING_CHARS = 280
MAX_SUMMARY_CHARS = 1500
MAX_IMPLICATION_CHARS = 1500

ALLOWED_CONFIDENCE = {"high", "moderate", "low", "very_low"}
MIN_EVIDENCE_LEVEL = 1
MAX_EVIDENCE_LEVEL = 7

SYSTEM_PROMPT = """\
You analyse a single research paper for one patient: Aleksandra Jincharadze, a
9-month-old child with severe hypoxic-ischemic encephalopathy (HIE), diffuse
cystic encephalomalacia (multifocal cavitary lesions, primarily fronto-parietal),
and a preserved brainstem. Her family is investigating treatment options inside
the neuroplasticity window (0-2 years).

You are NOT a clinician. You produce discussion material a clinician and family
can read and verify — never instructions, never predictions, never prescriptions.

Given the paper's title and abstract, return JSON only (no markdown, no prose
outside the object) with this exact shape:

  {
    "summary":            str,        # 3-4 sentences, plain language: what the paper studied and found
    "key_findings":       [str],      # 2-6 short bullet strings; prefer PICO framing
                                       #   (population, intervention, comparator, outcome, study type, sample size)
    "evidence_level":     int,        # 1..7 GRADE-like tier (see rubric below)
    "confidence_level":   str,        # how informative this paper is FOR ALEKSANDRA'S CASE:
                                       #   one of: high | moderate | low | very_low
    "aleksandra_implications": str,   # 1-3 sentences: what a clinician might DISCUSS for her case,
                                       #   framed as "evidence suggests" / "studies report"; state applicability
                                       #   limits plainly (e.g. adult/animal data, different condition)
    "insufficient_evidence":   bool   # true if the abstract is missing or too thin to analyse honestly
  }

evidence_level rubric (clamp to 1..7):
  1 = systematic review / meta-analysis
  2 = randomized controlled trial
  3 = prospective cohort
  4 = case-control / retrospective comparison
  5 = case series / small uncontrolled / observational
  6 = mechanism / animal / in-vitro / preprint hypothesis
  7 = expert opinion / single anecdote / unverified

Hard rules you cannot violate:
  - GROUND every finding in the supplied abstract. Do not introduce facts the
    abstract does not state.
  - If the abstract is empty or too thin, set insufficient_evidence=true, give a
    one-line honest summary ("Abstract too limited to analyse"), set
    evidence_level=7 and confidence_level="very_low". Do NOT invent content.
  - NEVER recommend starting/stopping/changing a treatment. NEVER predict
    Aleksandra's outcome. The clinician decides; you surface and explain.
  - Be honest about transfer: a strong adult-stroke or animal study is still
    only indirectly relevant to an infant with HIE — say so in
    aleksandra_implications and reflect it in confidence_level.
  - Avoid "limited outcomes" framing; the 0-2 year neuroplasticity window is the
    operating premise.
"""


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AnalysisResult:
    summary: str | None
    key_findings: list[str] = field(default_factory=list)
    implications: str | None = None
    evidence_level: int | None = None
    confidence_level: str | None = None
    insufficient_evidence: bool = False
    note: str = ""
    raw: str = ""

    def is_writable(self) -> bool:
        """True when there is at least a summary to persist."""
        return bool(self.summary and self.summary.strip())


# ---------------------------------------------------------------------------
# Parsing / coercion helpers
# ---------------------------------------------------------------------------
def _plain(value: Any) -> str:
    """Flatten a possibly-bilingual ({en,ka} JSONB / JSON string) field to text.

    Migration 017 turned papers.title/abstract into {en, ka} JSONB; a raw dict or
    a JSON-looking string must not be fed verbatim to the prompt. Prefer English.
    """
    if value is None:
        return ""
    if isinstance(value, dict):
        return str(value.get("en") or value.get("ka") or "").strip()
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                d = json.loads(s)
                if isinstance(d, dict):
                    return str(d.get("en") or d.get("ka") or "").strip()
            except json.JSONDecodeError:
                pass
        return s
    return str(value).strip()


def _strip_code_fence(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```"):
        first_nl = s.find("\n")
        s = s[first_nl + 1 :].rsplit("```", 1)[0].strip()
    return s


def _coerce_evidence_level(value: Any) -> int | None:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return max(MIN_EVIDENCE_LEVEL, min(MAX_EVIDENCE_LEVEL, n))


def _coerce_confidence(value: Any) -> str | None:
    s = str(value or "").strip().lower()
    return s if s in ALLOWED_CONFIDENCE else None


def _coerce_findings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = _plain(item) if not isinstance(item, str) else item.strip()
        if text:
            out.append(text[:MAX_FINDING_CHARS])
        if len(out) >= MAX_KEY_FINDINGS:
            break
    return out


def _parse_payload(raw: str) -> dict | None:
    """Pull the JSON object out of a model reply, tolerating fences / stray prose."""
    candidate = _strip_code_fence(raw)
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", candidate, flags=re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return data if isinstance(data, dict) else None


# ---------------------------------------------------------------------------
# Core analysis (never raises)
# ---------------------------------------------------------------------------
def analyze(title: str, abstract: str) -> AnalysisResult:
    """Analyse one paper. Never raises — a failure returns summary=None so the
    caller persists nothing and the paper stays unanalysed for a later retry."""
    title = _plain(title)
    abstract = _plain(abstract)

    if not title and not abstract:
        return AnalysisResult(
            summary=None,
            insufficient_evidence=True,
            note="empty paper (no title or abstract)",
        )

    prompt = (
        f"## Title\n{title or '(no title)'}\n\n"
        f"## Abstract\n{abstract or '(no abstract available)'}\n\n"
        "Return the JSON object."
    )

    try:
        raw = call_llm(
            prompt=prompt,
            agent_id=AGENT_ID,
            task=TASK,
            complexity=len(prompt),  # short abstract -> thinker_light; long -> Opus
            system=SYSTEM_PROMPT,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
    except Exception as e:  # noqa: BLE001 — call_llm already logged a failed runs row
        return AnalysisResult(
            summary=None,
            note=f"call_llm failed: {type(e).__name__}: {str(e)[:160]}",
        )

    data = _parse_payload(raw)
    if data is None:
        return AnalysisResult(
            summary=None,
            note=f"non-JSON response (len={len(raw)})",
            raw=raw[:600],
        )

    summary = _plain(data.get("summary"))[:MAX_SUMMARY_CHARS] or None
    implications = _plain(data.get("aleksandra_implications"))[:MAX_IMPLICATION_CHARS]
    return AnalysisResult(
        summary=summary,
        key_findings=_coerce_findings(data.get("key_findings")),
        implications=implications or None,
        evidence_level=_coerce_evidence_level(data.get("evidence_level")),
        confidence_level=_coerce_confidence(data.get("confidence_level")),
        insufficient_evidence=bool(data.get("insufficient_evidence", False)),
        raw=raw[:1200],
    )


# ---------------------------------------------------------------------------
# Supabase I/O
# ---------------------------------------------------------------------------
def _fetch_paper(paper_id: str) -> dict[str, Any] | None:
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/papers",
        params={
            "id": f"eq.{paper_id}",
            "select": "id,title,abstract,relevance_score,ai_summary",
        },
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


def _build_patch_body(result: AnalysisResult) -> dict[str, Any]:
    """Only include fields the analysis actually produced — never NULL a column
    we couldn't fill.

    ai_summary / ai_aleksandra_implications are JSONB {en, ka} since migration
    026 (mirroring title/abstract). We write the English we just produced and
    leave ka NULL — the ka slot is filled by the digest-cache backfill in
    migration 026 and kept current by migration 025's auto pass. flatten() in
    the viewer falls back to en until ka lands, so the family site never blanks.
    """
    body: dict[str, Any] = {"ai_summary": {"en": result.summary, "ka": None}}
    if result.key_findings:
        body["ai_key_findings"] = result.key_findings  # JSON array -> Postgres text[]
    if result.implications:
        body["ai_aleksandra_implications"] = {"en": result.implications, "ka": None}
    if result.evidence_level is not None:
        body["evidence_level"] = result.evidence_level
    if result.confidence_level is not None:
        body["confidence_level"] = result.confidence_level
    return body


def analyze_and_write(paper_id: str) -> AnalysisResult:
    """Analyse one paper by id and persist. If the analysis is not writable
    (model failed / no summary), nothing is written and the row keeps
    ai_summary=NULL for a later backfill retry."""
    load_env()
    row = _fetch_paper(paper_id)
    if row is None:
        return AnalysisResult(summary=None, note="paper not found")

    result = analyze(title=row.get("title") or "", abstract=row.get("abstract") or "")
    if not result.is_writable():
        return result

    _patch_paper(paper_id, _build_patch_body(result))
    return result


def _fetch_unanalyzed(limit: int, min_relevance: float) -> list[dict[str, Any]]:
    """Relevant (relevance_score >= min_relevance) and not-yet-analysed
    (ai_summary IS NULL) papers, most-relevant first."""
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/papers",
        params={
            "select": "id,title,abstract,relevance_score",
            "ai_summary": "is.null",
            "relevance_score": f"gte.{min_relevance}",
            "order": "relevance_score.desc",
            "limit": str(limit),
        },
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def backfill(
    limit: int = DEFAULT_BACKFILL_LIMIT,
    *,
    min_relevance: float = DEFAULT_MIN_RELEVANCE,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Analyse relevant, unanalysed papers. Idempotent (Supabase-level filter)."""
    load_env()
    rows = _fetch_unanalyzed(limit=limit, min_relevance=min_relevance)
    summary: dict[str, Any] = {
        "seen": len(rows),
        "analyzed": 0,
        "wrote": 0,
        "insufficient": 0,
        "failed": 0,
        "min_relevance": min_relevance,
        "dry_run": dry_run,
    }

    for row in rows:
        pid = str(row["id"])
        result = analyze(
            title=row.get("title") or "", abstract=row.get("abstract") or ""
        )
        if not result.is_writable():
            summary["failed"] += 1
            print(f"FAIL   {pid}  {result.note[:120]}")
            continue

        summary["analyzed"] += 1
        if result.insufficient_evidence:
            summary["insufficient"] += 1
        marker = "DRY-RUN" if dry_run else "WRITE  "
        print(
            f"{marker} {pid}  ev={result.evidence_level}  "
            f"conf={result.confidence_level}  "
            f"findings={len(result.key_findings)}  "
            f"{result.summary[:60]!r}"
        )
        if not dry_run and _patch_paper(pid, _build_patch_body(result)):
            summary["wrote"] += 1

    return summary


def run(
    *,
    limit: int = 0,
    min_relevance: float = DEFAULT_MIN_RELEVANCE,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Worker entry point (POST /analysis-tick). Thin wrapper over backfill()."""
    return backfill(
        limit=limit or DEFAULT_BACKFILL_LIMIT,
        min_relevance=min_relevance,
        dry_run=dry_run,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Per-paper deep analysis (Evidence Refinery Stage 2)."
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Analyse all relevant, unanalysed papers (ai_summary IS NULL).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_BACKFILL_LIMIT,
        help=f"Max papers to analyse in backfill (default {DEFAULT_BACKFILL_LIMIT}).",
    )
    parser.add_argument(
        "--min-relevance",
        type=float,
        default=DEFAULT_MIN_RELEVANCE,
        help=f"Only analyse papers with relevance_score >= this (default {DEFAULT_MIN_RELEVANCE}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Backfill mode: compute analyses, print them, do NOT write to Supabase.",
    )
    parser.add_argument(
        "--paper-id",
        type=str,
        default=None,
        help="Single-paper mode: analyse one paper by UUID.",
    )
    args = parser.parse_args()

    if args.paper_id:
        result = analyze_and_write(args.paper_id)
        print(
            f"paper {args.paper_id}: "
            f"writable={result.is_writable()}  evidence_level={result.evidence_level}  "
            f"confidence={result.confidence_level!r}  findings={len(result.key_findings)}  "
            f"insufficient={result.insufficient_evidence}  note={result.note[:160]!r}"
        )
        return 0 if result.is_writable() else 2

    if args.backfill:
        summary = backfill(
            limit=args.limit, min_relevance=args.min_relevance, dry_run=args.dry_run
        )
        print("\n=== analyze_paper backfill summary ===")
        for k, v in summary.items():
            print(f"  {k:>16}  {v}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
