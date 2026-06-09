"""
bilingual.py — Phase 6 I18N-06 bilingual composer (Anthropic strict tool_use).

Wraps Claude Sonnet 4.5 with `tools=[{strict: True, input_schema: {en, ka}}]`
+ `tool_choice={type: "tool", name: "compose_bilingual"}` so a single API call
emits `{"en": str, "ka": str}` simultaneously. Schema-validated via Anthropic
strict tool_use (grammar-constrained sampling — provably impossible to emit
a non-conforming shape).

Per CONTEXT.md D-02 (per-tier policy):
  - weekly_brief.py uses Option A (deterministic mirror — no LLM)
  - agents/communicator.py + scripts/manager/briefing.py use Option B (this helper)
  - scripts/communicator/outreach_drafter.py STAYS single-language per recipient
  - Internal CrewAI agents (Spider/Analyzer/Hypothesis/Repurposing) STAY English-only

Cost note (RESEARCH.md Pattern 6):
  ~313 tokens of system-prompt overhead per call when `tool_choice` forces a
  specific tool (vs 346 for auto). At Sonnet 4.5's $3 in / $15 out per 1M
  tokens, that's ~$0.001 overhead + per-content tokens. Estimated $0.01–$0.02
  per call. Phase 6 $5 cap has plenty of headroom (cumulative $4.22 / $60 cap).

Budget gate:
  Wired through `scripts.cognition.budget.check_daily_budget(raise_on_over=True)`
  BEFORE the Anthropic call. This is the existing Phase 0 FND-04 ceiling
  (defence-in-depth alongside the n8n cron gate). Caller-side `runs` ledger
  wrapping is left to weekly_brief.py / briefing.py / communicator.py per
  Phase 2.5 A.2 spend-instrumentation gate — compose_bilingual is a pure helper.

Public surface
--------------
    BILINGUAL_TOOL: dict           — the strict tool_use schema
    compose_bilingual(prompt, *, client, model='claude-sonnet-4-5') -> dict

Test mode
---------
    BILINGUAL_TEST_MODE=1 (env var) — bypass Anthropic call entirely; return a
    deterministic placeholder pair. Used by CI / verifier so the code path
    works without an API key and without burning credits.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from scripts.cognition import models
from scripts.cognition.budget import check_daily_budget
from scripts.cognition.llm import (
    LLMRefusal,
    _openrouter_complete,
    _openrouter_key,
    _record_call,
)

if TYPE_CHECKING:  # pragma: no cover — import only for type hints
    from anthropic import Anthropic


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_MAX_TOKENS = 1024

# The strict tool_use schema. `strict: True` activates grammar-constrained
# sampling — the model literally cannot emit anything but a JSON object with
# exactly the keys 'en' and 'ka' (both strings). `additionalProperties: False`
# locks the shape; `required` forces both keys to be present.
BILINGUAL_TOOL: dict[str, Any] = {
    "name": "compose_bilingual",
    "description": (
        "Emit a family-facing draft in English and Georgian (Mkhedruli script) "
        "simultaneously. Both languages must convey the same medical content "
        "with the same evidence framing. Tone clinical but family-friendly. "
        "Do not include PHI (names, MRN, DOB) — the caller redacts before this "
        "call, but reinforce: use 'A.J., 8-month-old infant with severe HIE' "
        "as the patient referent. Avoid imperatives like 'უნდა', 'აუცილებლად', "
        "'განიხილეთ', 'მოითხოვეთ' in the Georgian half (Phase 6 D-05 lexicon)."
    ),
    "strict": True,  # grammar-constrained sampling — non-conforming output impossible
    "input_schema": {
        "type": "object",
        "properties": {
            "en": {
                "type": "string",
                "description": "Body in English (US clinician register).",
            },
            "ka": {
                "type": "string",
                "description": "Body in Georgian (family register, Mkhedruli script).",
            },
        },
        "required": ["en", "ka"],
        "additionalProperties": False,
    },
}


# ---------------------------------------------------------------------------
# Test-mode fallback
# ---------------------------------------------------------------------------
def _is_test_mode() -> bool:
    """Return True when the helper should bypass Anthropic and emit a stub.

    Triggered by:
      - BILINGUAL_TEST_MODE=1 in env (explicit opt-in for CI / verifier)
      - ANTHROPIC_API_KEY unset (defensive — never crash a smoke run)
    """
    if os.environ.get("BILINGUAL_TEST_MODE", "").strip() == "1":
        return True
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return True
    return False


def _stub_pair(prompt: str) -> dict[str, str]:
    """Deterministic placeholder used by CI / verifier when no API key is present.

    The Georgian half is a marked placeholder (NOT a real translation) so any
    downstream consumer (e.g., Telegram .ka audience) can detect that this row
    was produced under test mode rather than real bilingual emission.
    """
    return {
        "en": prompt,
        "ka": f"[KA-PLACEHOLDER] {prompt}",
    }


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------
def compose_bilingual(
    prompt: str,
    *,
    client: "Anthropic | None" = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> dict[str, str]:
    """Single Anthropic call emits both en + ka via strict tool_use.

    Args:
        prompt: The user-message content (English request describing what to draft).
            The model emits both halves of the bilingual pair in one shot — no
            follow-up translation call. Caller MUST have already PHI-redacted
            the prompt; defensive redaction on the OUTPUT is the caller's job
            (see agents/communicator.py for the canonical pattern).
        client: Anthropic SDK client. Keyword-only. May be None in test mode.
        model: Claude model name. Defaults to claude-sonnet-4-5 per CLAUDE.md.
        max_tokens: Output cap per RESEARCH.md Pattern 6 (1024 sufficient for
            section-sized drafts; raise if the caller is composing long-form).

    Returns:
        Dict with exactly two keys: {'en': str, 'ka': str}.

    Raises:
        RuntimeError: If the model produced no tool_use block (should be
            impossible under strict mode, but we surface it explicitly rather
            than indexing into an empty list).
        BudgetExceeded: If the FND-04 daily-spend gate trips.
    """
    # Explicit test-mode short-circuit (CI / verifier).
    if os.environ.get("BILINGUAL_TEST_MODE", "").strip() == "1":
        return _stub_pair(prompt)

    # Provider routing. An injected Anthropic client or MODEL_PROVIDER=anthropic
    # uses the legacy strict tool_use path (rollback / tests); otherwise the
    # writer tier (Gemini via OpenRouter, JSON mode) emits the {en, ka} pair.
    use_anthropic = client is not None or models.provider() == "anthropic"

    if use_anthropic:
        if client is None:
            if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
                return _stub_pair(prompt)  # defensive — never crash a smoke run
            import anthropic  # noqa: PLC0415

            client = anthropic.Anthropic()
        check_daily_budget(raise_on_over=True)
        return _compose_anthropic(prompt, client=client, model=model, max_tokens=max_tokens)

    # Writer tier — Gemini via OpenRouter.
    if not os.environ.get("OPENROUTER_API_KEY", "").strip():
        return _stub_pair(prompt)  # defensive — never crash a smoke run
    check_daily_budget(raise_on_over=True)
    return _compose_openrouter(prompt, max_tokens=max_tokens)


def _compose_anthropic(
    prompt: str,
    *,
    client: "Anthropic",
    model: str,
    max_tokens: int,
) -> dict[str, str]:
    """Legacy strict tool_use path (Anthropic). Rollback / injected-client."""
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        tools=[BILINGUAL_TOOL],
        tool_choice={"type": "tool", "name": "compose_bilingual"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in resp.content:
        block_type = getattr(block, "type", None)
        block_name = getattr(block, "name", None)
        if block_type == "tool_use" and block_name == "compose_bilingual":
            data = block.input  # strict mode guarantees this dict has en+ka
            return {
                "en": str(data.get("en", "")),
                "ka": str(data.get("ka", "")),
            }

    raise RuntimeError(
        "compose_bilingual: model produced no tool_use block for "
        "'compose_bilingual' (response.content blocks: "
        f"{[getattr(b, 'type', '?') for b in resp.content]})"
    )


# OpenRouter/Gemini JSON-mode system prompt. Gemini lacks Anthropic strict
# grammar-constrained sampling, so we ask for a bare JSON object and parse it
# defensively (mirrors the Phase 6.1 lesson: never index a possibly-empty body).
_OPENROUTER_SYSTEM = (
    "You are a family-facing bilingual medical-log composer. Reply with ONLY a "
    'JSON object of the exact shape {"en": "...", "ka": "..."} and nothing else '
    "(no markdown fences, no commentary). Both languages must convey the same "
    "medical content with the same evidence framing; tone clinical but "
    "family-friendly. 'ka' must be Georgian in Mkhedruli script. Do not include "
    "PHI (names, MRN, DOB) — use 'A.J., 8-month-old infant with severe HIE' as "
    "the patient referent. Avoid Georgian imperatives like 'უნდა', "
    "'აუცილებლად', 'განიხილეთ', 'მოითხოვეთ' (Phase 6 D-05 lexicon)."
)


def _parse_en_ka(raw: str) -> dict[str, str] | None:
    """Parse a {en, ka} object from a model reply. Tolerant of stray fences."""
    candidate = raw.strip()
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
    if not isinstance(data, dict) or "en" not in data or "ka" not in data:
        return None
    return {"en": str(data.get("en", "")), "ka": str(data.get("ka", ""))}


def _compose_openrouter(
    prompt: str, *, max_tokens: int, max_attempts: int = 2
) -> dict[str, str]:
    """Writer-tier path — Gemini via OpenRouter, JSON mode. Records one runs row."""
    api_key = _openrouter_key()
    model = models.TIER_MODEL["writer"]
    messages = [
        {"role": "system", "content": _OPENROUTER_SYSTEM},
        {"role": "user", "content": prompt},
    ]

    last_err: str | None = None
    for attempt in range(max_attempts):
        start = datetime.now(timezone.utc)
        try:
            raw, in_tok, out_tok = _openrouter_complete(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.2,
                api_key=api_key,
                response_format={"type": "json_object"},
            )
        except LLMRefusal as e:
            end = datetime.now(timezone.utc)
            _record_call(
                agent_id="compose_bilingual",
                model=model,
                start=start,
                end=end,
                input_tokens=0,
                output_tokens=0,
                exit_status="empty_or_refusal",
                exit_reason=str(e)[:300],
            )
            last_err = str(e)
            continue

        end = datetime.now(timezone.utc)
        parsed = _parse_en_ka(raw)
        _record_call(
            agent_id="compose_bilingual",
            model=model,
            start=start,
            end=end,
            input_tokens=in_tok,
            output_tokens=out_tok,
            exit_status="completed" if parsed else "parse_error",
            exit_reason=None if parsed else "could not parse {en,ka} JSON",
        )
        if parsed:
            return parsed
        last_err = "unparseable JSON reply"

    raise RuntimeError(
        f"compose_bilingual: writer tier produced no valid {{en,ka}} after "
        f"{max_attempts} attempts ({last_err})"
    )


__all__ = [
    "BILINGUAL_TOOL",
    "DEFAULT_MODEL",
    "DEFAULT_MAX_TOKENS",
    "compose_bilingual",
]
