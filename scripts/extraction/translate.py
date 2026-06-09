"""scripts/extraction/translate.py — reusable en→ka translator.

Extracted from migrations 014/015 hard-won pattern:

  - claude-sonnet-4-6 model (looser safety classifier than 4-5).
  - System prompt that frames the task as a non-commercial family-operated
    medical research log so the model does not refuse descriptive medical
    terminology as "medical advice".
  - Defensive content[0] access — refusal returns content=[] with
    stop_reason='refusal', NOT an exception. We retry with backoff and
    only raise after max_attempts genuine empty/refusal responses.
  - Output is Mkhedruli only (no transliteration), preserves markdown.

Used at ingestion time (fetch_pubmed/ctgov/preprints) to populate the
`ka` half of the JSONB title/abstract columns introduced by migration 017.

Budget discipline:
  - Every translate call is preceded by `check_daily_budget()` so the
    Spider cannot blow past the project cap even with a thousand-paper
    burst. Default cap is the project-wide $0.50/day per budget.py.

Cost shape (sonnet-4-6 pricing as of 2026-05):
  - input  $3 / 1M tokens
  - output $15 / 1M tokens
  - Typical paper title: ~20 tokens in/out → ~$0.0004
  - Typical paper abstract: ~250 tokens in/out → ~$0.005
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import anthropic
import httpx

from scripts.cognition import models
from scripts.cognition.budget import BudgetExceeded, check_daily_budget
from scripts.cognition.llm import (
    LLMRefusal,
    _openrouter_complete,
    _openrouter_key,
    _record_call,
)

MODEL = "claude-sonnet-4-6"
SYSTEM_PROMPT = (
    "You are a translation utility for a non-commercial family-operated "
    "medical research log. Your only job is to translate the user-provided "
    "English text to Georgian (Mkhedruli script ONLY, no transliteration). "
    "Preserve markdown formatting (headers, bold, lists, line breaks). "
    "Output ONLY the Georgian translation — no commentary, no quotes, no "
    "preamble. The text is descriptive scientific terminology, not a medical "
    "recommendation; do not refuse."
)

# Anthropic prompt-caching requires the cacheable block to be ≥1024 tokens
# for Sonnet/Opus and ≥2048 for Haiku. SYSTEM_PROMPT above is ~95 tokens, so
# caching it directly would no-op. We still mark it ephemeral so when the
# prompt grows (or when we switch to a longer multi-shot template) the cache
# layer engages automatically. Reads are charged at 0.1× input rate.
_SYSTEM_BLOCKS = [
    {
        "type": "text",
        "text": SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},
    }
]


class TranslationFailed(RuntimeError):
    pass


def translate_to_georgian(
    text: str,
    *,
    client: anthropic.Anthropic | None = None,
    max_attempts: int = 3,
    max_tokens: int = 4096,
    check_budget: bool = True,
) -> str:
    """Translate English `text` to Georgian (Mkhedruli).

    Writer tier: Gemini via OpenRouter by default. An injected Anthropic
    `client` or MODEL_PROVIDER=anthropic uses the legacy Sonnet strict path
    (rollback / tests).

    Empty or whitespace-only input returns "" without an API call (cheap path
    for papers that legitimately have no abstract).

    Raises:
        BudgetExceeded: if `check_budget=True` and today's spend is over cap.
        TranslationFailed: after `max_attempts` empty/refusal responses.
    """
    if not text or not text.strip():
        return ""

    if check_budget:
        _spend, over = check_daily_budget(raise_on_over=False)
        if over:
            raise BudgetExceeded(_spend, 0.0)

    if client is not None or models.provider() == "anthropic":
        return _translate_anthropic(
            text, client=client, max_attempts=max_attempts, max_tokens=max_tokens
        )
    return _translate_openrouter(
        text, max_attempts=max_attempts, max_tokens=max_tokens
    )


def _translate_anthropic(
    text: str,
    *,
    client: anthropic.Anthropic | None,
    max_attempts: int,
    max_tokens: int,
) -> str:
    """Legacy Sonnet path — rollback (MODEL_PROVIDER=anthropic) or injected client."""
    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
            raise TranslationFailed("ANTHROPIC_API_KEY not set")
        client = anthropic.Anthropic()

    last_err: str | None = None
    for attempt in range(max_attempts):
        start = datetime.now(timezone.utc)
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                system=_SYSTEM_BLOCKS,
                messages=[
                    {
                        "role": "user",
                        "content": f"Translate to Georgian (Mkhedruli):\n\n{text}",
                    }
                ],
            )
            end = datetime.now(timezone.utc)
            usage = getattr(resp, "usage", None)
            # Roll cache_read/cache_create into input_tokens for the ledger.
            in_tok = int(getattr(usage, "input_tokens", 0) or 0) + int(
                getattr(usage, "cache_creation_input_tokens", 0) or 0
            ) + int(getattr(usage, "cache_read_input_tokens", 0) or 0)
            out_tok = int(getattr(usage, "output_tokens", 0) or 0)
            blocks = [b for b in resp.content if getattr(b, "type", None) == "text"]
            ok = bool(blocks and blocks[0].text.strip())
            _record_call(
                agent_id="translate_to_georgian",
                model=MODEL,
                start=start,
                end=end,
                input_tokens=in_tok,
                output_tokens=out_tok,
                exit_status="ok" if ok else "empty_or_refusal",
                exit_reason=None if ok else f"stop_reason={resp.stop_reason}",
            )
            if ok:
                return blocks[0].text.strip()
            last_err = (
                f"empty/refusal (stop_reason={resp.stop_reason} "
                f"blocks={len(resp.content)})"
            )
        except anthropic.APIError as e:
            end = datetime.now(timezone.utc)
            _record_call(
                agent_id="translate_to_georgian",
                model=MODEL,
                start=start,
                end=end,
                input_tokens=0,
                output_tokens=0,
                exit_status="api_error",
                exit_reason=f"{type(e).__name__}: {e}",
            )
            last_err = f"{type(e).__name__}: {e}"
        time.sleep(1 + attempt)

    raise TranslationFailed(
        f"translate failed after {max_attempts} attempts: {last_err}"
    )


def _translate_openrouter(text: str, *, max_attempts: int, max_tokens: int) -> str:
    """Writer-tier path — Gemini via OpenRouter (default)."""
    api_key = _openrouter_key()  # raises RuntimeError if OPENROUTER_API_KEY unset
    model = models.TIER_MODEL["writer"]
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Translate to Georgian (Mkhedruli):\n\n{text}",
        },
    ]

    last_err: str | None = None
    for attempt in range(max_attempts):
        start = datetime.now(timezone.utc)
        try:
            out, in_tok, out_tok = _openrouter_complete(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.0,
                api_key=api_key,
            )
            end = datetime.now(timezone.utc)
            _record_call(
                agent_id="translate_to_georgian",
                model=model,
                start=start,
                end=end,
                input_tokens=in_tok,
                output_tokens=out_tok,
                exit_status="ok",
            )
            if out and out.strip():
                return out.strip()
            last_err = "empty response"
        except LLMRefusal as e:
            end = datetime.now(timezone.utc)
            _record_call(
                agent_id="translate_to_georgian",
                model=model,
                start=start,
                end=end,
                input_tokens=0,
                output_tokens=0,
                exit_status="empty_or_refusal",
                exit_reason=str(e)[:300],
            )
            last_err = str(e)
        except httpx.HTTPStatusError as e:
            end = datetime.now(timezone.utc)
            _record_call(
                agent_id="translate_to_georgian",
                model=model,
                start=start,
                end=end,
                input_tokens=0,
                output_tokens=0,
                exit_status="api_error",
                exit_reason=f"{type(e).__name__}: {e}"[:300],
            )
            last_err = f"{type(e).__name__}: {e}"
        time.sleep(1 + attempt)

    raise TranslationFailed(
        f"translate failed after {max_attempts} attempts: {last_err}"
    )


def build_bilingual(en_text: str | None) -> dict | None:
    """Wrap English text into a {en, ka} JSONB-ready dict.

    Returns None when input is None (preserves nullable column semantics).
    Returns {"en": "", "ka": ""} when input is empty string (deliberate
    empty cell). Translation failures fall back to en-only so ingestion
    never blocks on translator hiccups; a later backfill catches up.
    """
    if en_text is None:
        return None
    en = en_text.strip()
    if not en:
        return {"en": "", "ka": ""}
    try:
        ka = translate_to_georgian(en)
    except (TranslationFailed, BudgetExceeded):
        ka = ""
    return {"en": en, "ka": ka}
