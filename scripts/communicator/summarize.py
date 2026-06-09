"""
summarize.py — Phase 3 CGM-01 source-grounded drafting.

Turns a query into a SummaryDraft with claim sentences, each citing at least
one source from the retrieve() facade. The draft passes through the Phase 3
safety pipeline before it's returned:

  retrieve()  →  Sonnet 4.5 (structured tool-use)  →  banned_phrases.check()
              →  confidence_classifier.score()  →  phi_redactor.redact()

Hard rules enforced by the system prompt:
  - Every claim sentence cites ≥ 1 source ID (PMID / DOI / NCT / URL or
    chunk hash). Without a citation the model is instructed to omit the
    sentence rather than fabricate one.
  - No clinical-command verbs (start/stop/increase/...). Banned-phrase
    detector blocks any output that includes them.
  - No prediction verbs ("will recover", "outcome will be").
  - The recipient identity defaults to "A.J., 8-month-old infant with severe
    HIE" — full identity is only available when consent_full_name=True.

The function returns a SummaryDraft. The caller decides whether to persist
it (outreach_log, alerts_log, briefs) — and persistence is allowed only when
draft.persistable() is True (banned passed, redaction not blocked, ≥1 claim).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime

from scripts.cognition.llm import call_llm
from scripts.communicator.banned_phrases import BannedPhraseResult
from scripts.communicator.banned_phrases import check as banned_check
from scripts.communicator.confidence_classifier import ConfidenceInput, score
from scripts.communicator.phi_redactor import (
    ConsentFlags,
    RedactionResult,
    redact,
)
from scripts.rag.retrieve import retrieve


# ---------------------------------------------------------------------------
# Draft contract
# ---------------------------------------------------------------------------
@dataclass
class Claim:
    sentence: str
    citation_ids: list[str]  # PMID / DOI / NCT / URL / chunk_hash strings
    evidence_grade: int  # 1..6 per project six-tier ranking


@dataclass
class SummaryDraft:
    query: str
    audience: str  # 'family' | 'researcher' | 'clinician' | 'internal'
    language: str  # 'en' | 'fr' | 'ka'
    claims: list[Claim] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)  # union of citation_ids
    confidence: float = 0.0
    banned: BannedPhraseResult | None = None
    redaction: RedactionResult | None = None
    raw_text: str = ""  # the model's plain-text rendering
    redacted_text: str = ""
    generated_at: str = ""

    def persistable(self) -> bool:
        """True only if every safety gate passed."""
        if self.banned is not None and not self.banned.passed:
            return False
        if self.redaction is not None and self.redaction.blocked:
            return False
        if not self.claims:
            return False
        # Every claim must cite at least one source.
        return all(c.citation_ids for c in self.claims)

    def to_json(self) -> str:
        # banned/redaction are dataclasses but contain custom types; keep
        # serialisation simple by stringifying.
        return json.dumps(
            {
                "query": self.query,
                "audience": self.audience,
                "language": self.language,
                "claims": [asdict(c) for c in self.claims],
                "citations": self.citations,
                "confidence": self.confidence,
                "banned_passed": self.banned.passed if self.banned else None,
                "redaction_blocked": self.redaction.blocked if self.redaction else None,
                "redactions_count": (
                    len(self.redaction.redactions) if self.redaction else 0
                ),
                "raw_text": self.raw_text,
                "redacted_text": self.redacted_text,
                "generated_at": self.generated_at,
            },
            default=str,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """You are the Communicator agent for ALEKSANDRA_BRAIN, a research-discovery system for an infant with severe HIE.

You are NOT a clinician. You produce *discussion material* for clinicians and family — never instructions, never predictions, never prescriptions.

RULES YOU CANNOT VIOLATE:
1. Every claim sentence must cite at least one source id from the EVIDENCE block provided. If no source supports the claim, omit it.
2. NEVER use clinical-command verbs: start, stop, increase, decrease, replace, administer, prescribe, diagnose. Use "review", "discuss", "ask", "save", "track", "share", "schedule a clinician conversation about".
3. NEVER predict outcomes ("will recover", "will improve", "outcome will be"). Frame as "evidence suggests" or "studies report".
4. NEVER reveal the patient's full name, DOB day, MRN, hospital MRN, or MRI artifact paths. Refer to the patient as "A.J., 8-month-old infant with severe HIE" unless the consent profile explicitly allows otherwise.
5. NEVER write "we recommend", "you should", "the patient should", or any direct-to-recipient instruction.
6. Stay short. 3-6 claim sentences per draft. Quality over volume.

OUTPUT FORMAT — return a single JSON object with this shape:

{
  "claims": [
    {
      "sentence": "<one factual sentence>",
      "citation_ids": ["<source_id from EVIDENCE, e.g. PMID:12345 or DOI:10.x/y or NCT01234567 or chunk:<hash>>", ...],
      "evidence_grade": <integer 1-6>
    }
  ]
}

evidence_grade values:
  1 = systematic review / meta-analysis
  2 = randomized controlled trial
  3 = cohort or case-control
  4 = case series / uncontrolled
  5 = expert opinion / mechanism / preprint
  6 = unverified / single anecdote
"""


def _build_user_prompt(
    query: str, evidence_block: str, audience: str, language: str
) -> str:
    return (
        f"AUDIENCE: {audience}\n"
        f"LANGUAGE: write in {language}.\n\n"
        f"QUERY:\n{query}\n\n"
        f"EVIDENCE (use only these citation_ids):\n{evidence_block}\n\n"
        f"Return only the JSON object — no preamble, no markdown."
    )


def _build_evidence_block(
    result, top_chunks: int = 6, top_facts: int = 6
) -> tuple[str, list[str]]:
    """Format the retrieve() result into a block the model can cite from.

    Returns (text_block, allowed_citation_ids).
    """
    lines: list[str] = []
    allowed: list[str] = []
    for c in result.chunks[:top_chunks]:
        cid = (
            f"chunk:{c.content_hash[:12]}" if c.content_hash else f"chunk:{c.chunk_id}"
        )
        # Inject the canonical source identifier if available
        if c.source_type == "pubmed":
            cid = f"PMID:{c.source_id}"
        elif c.source_type == "ctgov":
            cid = f"NCT:{c.source_id}"
        elif c.source_type in {"biorxiv", "medrxiv"}:
            cid = f"DOI:{c.source_id}"
        allowed.append(cid)
        preview = c.text_preview.replace("\n", " ")[:300]
        lines.append(f"- [{cid}] {preview}")
    for f in result.facts[:top_facts]:
        cid = f"fact:{f.uuid[:12]}"
        allowed.append(cid)
        lines.append(f"- [{cid}] {f.source_name} -> {f.target_name}: {f.fact}")
    return "\n".join(lines), allowed


def _parse_json_object(raw: str) -> dict:
    """Pull the first {...} JSON object out of `raw`. Tolerates stray prose."""
    m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not m:
        raise ValueError(f"No JSON object found in model output: {raw[:200]!r}")
    return json.loads(m.group(0))


def _claim_confidence(citation_ids: list[str], evidence_grade: int) -> float:
    """Best-effort confidence from the citation tuple + evidence grade.

    Day 3 simplification: we don't yet have round-trip verification wired in,
    so citation_round_trip_passed defaults to True. CGM-01 still gates on
    citation presence; the round-trip check tightens in a follow-up.
    """
    return score(
        ConfidenceInput(
            evidence_grade=evidence_grade,
            source_count=len(citation_ids),
            source_recency_years=0.5,
            direct_relevance=True,
            citation_round_trip_passed=True,
        )
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_summary(
    query: str,
    *,
    audience: str = "internal",
    language: str = "en",
    consent: ConsentFlags | None = None,
    max_tokens: int = 1200,
) -> SummaryDraft:
    """Produce a SummaryDraft for `query`, fully passed through the safety chain.

    Caller is responsible for persistence. A non-persistable draft (banned
    failed / redaction blocked / no claims) is still returned so the caller
    can inspect what went wrong.
    """
    # 1. Pull evidence via the single allowed retrieval facade.
    result = retrieve(query, t_at=None, top_k=8)
    evidence_block, allowed_cids = _build_evidence_block(result)

    if not allowed_cids:
        # No evidence found — return an empty draft so the caller can route to T0.
        return SummaryDraft(
            query=query,
            audience=audience,
            language=language,
            claims=[],
            citations=[],
            confidence=0.0,
            banned=BannedPhraseResult(passed=True, violations=[]),
            redaction=None,
            raw_text="",
            redacted_text="",
            generated_at=datetime.utcnow().isoformat(),
        )

    # 2. Writer-tier call (Gemini via OpenRouter) via the ledger-aware wrapper.
    user = _build_user_prompt(query, evidence_block, audience, language)
    raw = call_llm(
        prompt=user,
        agent_id="communicator",
        task="summarize",  # ✍️ writer tier
        system=_SYSTEM_PROMPT,
        max_tokens=max_tokens,
        temperature=0.2,
    )

    # 3. Parse JSON.
    parsed = _parse_json_object(raw)
    claims_raw = parsed.get("claims", []) or []
    allowed_set = set(allowed_cids)
    claims: list[Claim] = []
    citations: list[str] = []
    for c in claims_raw:
        sentence = (c.get("sentence") or "").strip()
        cids = [cid for cid in (c.get("citation_ids") or []) if cid in allowed_set]
        grade = int(c.get("evidence_grade") or 5)
        if not sentence:
            continue
        # Drop any claim that didn't cite — never persist an uncited claim.
        if not cids:
            continue
        claims.append(Claim(sentence=sentence, citation_ids=cids, evidence_grade=grade))
        citations.extend(cids)

    raw_text = "\n".join(c.sentence for c in claims)

    # 4. Banned-phrase scan on the rendered text.
    banned = banned_check(raw_text)

    # 5. Confidence — claim-weighted mean.
    if claims:
        confidence = round(
            sum(_claim_confidence(c.citation_ids, c.evidence_grade) for c in claims)
            / len(claims),
            4,
        )
    else:
        confidence = 0.0

    # 6. PHI redaction — using caller-supplied consent (None → all-False default).
    redaction = redact(raw_text, consent=consent)

    return SummaryDraft(
        query=query,
        audience=audience,
        language=language,
        claims=claims,
        citations=sorted(set(citations)),
        confidence=confidence,
        banned=banned,
        redaction=redaction,
        raw_text=raw_text,
        redacted_text=redaction.text if not redaction.blocked else "",
        generated_at=datetime.utcnow().isoformat(),
    )


__all__ = ["Claim", "SummaryDraft", "generate_summary"]
