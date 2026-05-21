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

import os
from typing import TYPE_CHECKING, Any

from scripts.cognition.budget import check_daily_budget

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
    # Test-mode short-circuit: bypass budget + Anthropic entirely, return stub.
    if _is_test_mode():
        return _stub_pair(prompt)

    if client is None:
        raise RuntimeError(
            "compose_bilingual: client is required outside test mode "
            "(set BILINGUAL_TEST_MODE=1 to use the deterministic stub)"
        )

    # Defence-in-depth budget gate — RAISES BudgetExceeded BEFORE the SDK call
    # when today's runs.token_cost sum is over the cap (Phase 0 FND-04 ceiling).
    check_daily_budget(raise_on_over=True)

    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        tools=[BILINGUAL_TOOL],
        tool_choice={"type": "tool", "name": "compose_bilingual"},
        messages=[{"role": "user", "content": prompt}],
    )

    # Iterate response blocks; pick the forced tool_use block.
    for block in resp.content:
        block_type = getattr(block, "type", None)
        block_name = getattr(block, "name", None)
        if block_type == "tool_use" and block_name == "compose_bilingual":
            data = block.input  # strict mode guarantees this dict has en+ka
            # Defensive read for type stability — strict mode makes this redundant
            # but the cost is one dict lookup.
            return {
                "en": str(data.get("en", "")),
                "ka": str(data.get("ka", "")),
            }

    raise RuntimeError(
        "compose_bilingual: model produced no tool_use block for "
        "'compose_bilingual' (response.content blocks: "
        f"{[getattr(b, 'type', '?') for b in resp.content]})"
    )


__all__ = [
    "BILINGUAL_TOOL",
    "DEFAULT_MODEL",
    "DEFAULT_MAX_TOKENS",
    "compose_bilingual",
]
