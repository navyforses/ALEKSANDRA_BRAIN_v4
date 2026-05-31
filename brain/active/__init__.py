"""Phase 7.4 — Active Learning.

Expected-Information-Gain (EIG) ranker + bilingual question generator +
rate-limited Telegram dry-run flow + response parser + posterior-update
integration for ALEKSANDRA_BRAIN v7 digital twin.

Two logical layers (no separate sub-packages; flat module layout):

  Layer A (Days 1-4 — math core):
    - entropy.py          Shannon entropy + analytical closed forms
    - eig.py              Expected Information Gain per (dim, observation)
    - catalog.py          13 candidate observation specs (bilingual desc)
    - ranker.py           top-K observations by cost-weighted EIG

  Layer B (Days 5-9 — wife-facing flow):
    - templates_ka.toml   26 hand-authored Mkhedruli templates (13 dims)
    - templates_en.toml   26 hand-authored EN templates (13 dims)
    - question_gen.py     render question from template + EIG payload
    - rate_limiter.py     constitutional rule #11 weekly cap (3/week)
    - telegram_flow.py    dry-run outbound with EMERGENCY_FREEZE switch
    - response_parser.py  voice / text transcript -> parsed value
    - integration.py      ParsedResponse -> BeliefEvidence -> update()

Hard rules:
    * NO PHI in module code or tests (synthetic samples only)
    * NO live Telegram (dry-run gated; production wiring deferred)
    * NO LLM (KA templates are hand-authored Mkhedruli)
    * NO direct DB writes when SUPABASE_DB_URL unset (DRY_RUN sentinel)
"""

from __future__ import annotations

__all__ = [
    "entropy",
    "eig",
    "catalog",
    "ranker",
    "question_gen",
    "rate_limiter",
    "telegram_flow",
    "response_parser",
    "integration",
]
