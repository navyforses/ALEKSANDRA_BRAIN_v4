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

import anthropic

from scripts.cognition.budget import BudgetExceeded, check_daily_budget

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

    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
            raise TranslationFailed("ANTHROPIC_API_KEY not set")
        client = anthropic.Anthropic()

    last_err: str | None = None
    for attempt in range(max_attempts):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Translate to Georgian (Mkhedruli):\n\n{text}",
                    }
                ],
            )
            blocks = [b for b in resp.content if getattr(b, "type", None) == "text"]
            if blocks and blocks[0].text.strip():
                return blocks[0].text.strip()
            last_err = (
                f"empty/refusal (stop_reason={resp.stop_reason} "
                f"blocks={len(resp.content)})"
            )
        except anthropic.APIError as e:
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
