"""
llm.py — Phase 3 spend instrumentation (closes the Phase 2 audit gap).

Every Anthropic call in ALEKSANDRA_BRAIN funnels through this module so that
exactly one `runs` row (`kind='llm_call'`) is appended per request, carrying
`agent_id`, `tokens_input`, `tokens_output`, `token_cost` (USD), and
`exit_status`. That ledger is the contract the daily-budget-gate n8n workflow
and the Phase 3 verifier both read.

Two surfaces are exported:

  call_claude(prompt, *, agent_id, model=…, system=…, max_tokens=…, temperature=…)
      Synchronous wrapper used directly by got_pipeline, extract_candidates,
      and pubmed_validation. Submits one user message, records the row, and
      returns the concatenated text content. Raises on API errors but always
      writes the row first (status='failed' + exit_reason).

  make_instrumented_async_anthropic(*, agent_id, api_key=None, max_retries=1)
      Returns a duck-typed AsyncAnthropic substitute (composition wrapper) that
      forwards every attribute to the real client while intercepting
      `messages.create()` to record into runs. Used by graphiti_client.py so
      Graphiti's internal LLM calls are also captured.

Design notes
------------
- Append-only contract: one `runs` row per call. We never UPDATE, never
  pre-INSERT a placeholder. The trigger from migration 001 rejects either.
- Pricing is hard-coded from Anthropic's published per-million-token rates
  (verified 2026-05 per .planning research). Unknown model IDs fall back to
  Sonnet 4.5 rates ($3 / $15) — conservative, so spend is never under-reported.
- Instrumentation failure (e.g., Supabase unreachable) prints a stderr warning
  but does NOT raise. The LLM call's own success/failure is the source of truth
  for the caller; missing one runs row is recoverable, a failed clinical
  pipeline is not.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any

import httpx

from scripts.cognition.budget import check_daily_budget
from scripts.ledger import _supabase_creds, _supabase_headers, load_env


# ---------------------------------------------------------------------------
# Pricing — Anthropic published $/1M-token rates (verified 2026-05).
#
# Tuple is (input_usd_per_million, output_usd_per_million). Match is by
# str.startswith so date-suffixed and -latest model IDs both resolve. Order
# matters here: more-specific prefixes go first.
# ---------------------------------------------------------------------------
_PRICING_USD_PER_M_TOKENS: list[tuple[str, tuple[float, float]]] = [
    # Claude Opus 4.x — $15 / $75 per 1M
    ("claude-opus-4", (15.00, 75.00)),
    # Claude Sonnet 4.5 and 4.6 — $3 / $15 per 1M
    ("claude-sonnet-4-5", (3.00, 15.00)),
    ("claude-sonnet-4-6", (3.00, 15.00)),
    ("claude-sonnet-4", (3.00, 15.00)),
    # Claude Haiku 4.5 — $0.80 / $4 per 1M
    ("claude-haiku-4-5", (0.80, 4.00)),
    ("claude-haiku-4", (0.80, 4.00)),
]
_FALLBACK_RATE_USD_PER_M = (3.00, 15.00)  # Sonnet — conservative for unknown IDs


def _compute_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Resolve $/1M rates by model-prefix and return cost in USD."""
    for prefix, (in_rate, out_rate) in _PRICING_USD_PER_M_TOKENS:
        if model.startswith(prefix):
            return (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000
    in_rate, out_rate = _FALLBACK_RATE_USD_PER_M
    return (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000


# ---------------------------------------------------------------------------
# runs writer — one INSERT per LLM call. Append-only enforced by trigger.
# ---------------------------------------------------------------------------
def _record_call(
    *,
    agent_id: str,
    model: str,
    start: datetime,
    end: datetime,
    input_tokens: int,
    output_tokens: int,
    exit_status: str,
    exit_reason: str | None = None,
) -> str | None:
    """Append one runs row. Returns row id, or None on instrumentation failure."""
    try:
        url, key = _supabase_creds()
    except RuntimeError as e:
        print(f"[runs.write] supabase creds missing: {e}", file=sys.stderr)
        return None

    cost = _compute_cost_usd(model, input_tokens, output_tokens)
    payload: dict[str, Any] = {
        "kind": "llm_call",
        "agent_id": agent_id,
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "token_cost": round(cost, 6),
        "tokens_input": int(input_tokens),
        "tokens_output": int(output_tokens),
        "exit_status": exit_status,
    }
    if exit_reason:
        payload["exit_reason"] = exit_reason[:1000]

    try:
        r = httpx.post(
            f"{url}/rest/v1/runs",
            json=payload,
            headers={**_supabase_headers(key), "Prefer": "return=representation"},
            timeout=10,
        )
        if r.status_code in (200, 201):
            try:
                return r.json()[0]["id"]
            except Exception:
                return None
        print(f"[runs.write] HTTP {r.status_code}: {r.text[:300]}", file=sys.stderr)
    except Exception as e:
        print(
            f"[runs.write] failed to record llm_call: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
    return None


# ---------------------------------------------------------------------------
# Synchronous wrapper — used by got_pipeline + extract_candidates + pubmed_validation
# ---------------------------------------------------------------------------
def call_claude(
    *,
    prompt: str,
    agent_id: str,
    model: str = "claude-sonnet-4-5",
    system: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> str:
    """
    Send one user message to Claude, append a runs row, return the text reply.

    Args:
        prompt: User message content.
        agent_id: Which agent is calling (spider | analyzer | hypothesis |
                  repurposing | communicator | <subtask qualifier>). Goes into
                  runs.agent_id.
        model: Anthropic model ID. Pricing resolved by prefix match.
        system: Optional system prompt.
        max_tokens: Max output tokens.
        temperature: Sampling temperature.

    Returns:
        Concatenated text content from the response (all `text` blocks joined).

    Raises:
        RuntimeError: ANTHROPIC_API_KEY missing.
        anthropic.APIError (and subclasses): on API errors — a failed runs row
            is still written first with exit_reason set.
    """
    import anthropic  # deferred — keeps import cheap when llm.py is only re-exporting

    load_env()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY missing from environment")

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system is not None:
        kwargs["system"] = system

    # Daily-budget gate — defence-in-depth alongside the n8n cron gate.
    # Raises BudgetExceeded if today's runs.token_cost sum is over the cap;
    # the SDK call never fires when over budget.
    check_daily_budget(raise_on_over=True)

    client = anthropic.Anthropic(api_key=api_key)
    start = datetime.now(timezone.utc)
    try:
        resp = client.messages.create(**kwargs)
    except Exception as e:
        end = datetime.now(timezone.utc)
        _record_call(
            agent_id=agent_id,
            model=model,
            start=start,
            end=end,
            input_tokens=0,
            output_tokens=0,
            exit_status="failed",
            exit_reason=f"{type(e).__name__}: {str(e)[:600]}",
        )
        raise

    end = datetime.now(timezone.utc)
    usage = getattr(resp, "usage", None)
    in_t = int(getattr(usage, "input_tokens", 0) or 0)
    out_t = int(getattr(usage, "output_tokens", 0) or 0)
    _record_call(
        agent_id=agent_id,
        model=model,
        start=start,
        end=end,
        input_tokens=in_t,
        output_tokens=out_t,
        exit_status="completed",
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


# ---------------------------------------------------------------------------
# Async instrumentation surface — used by Graphiti's AnthropicClient
# ---------------------------------------------------------------------------
class _InstrumentedAsyncMessages:
    """Wraps anthropic.AsyncAnthropic().messages and records each create()."""

    def __init__(self, inner: Any, agent_id: str) -> None:
        self._inner = inner
        self._agent_id = agent_id

    async def create(self, *args: Any, **kwargs: Any) -> Any:
        # Daily-budget gate — same contract as the sync wrapper. Raises
        # BudgetExceeded before the SDK call when today's spend is over.
        check_daily_budget(raise_on_over=True)

        model = kwargs.get("model", "unknown")
        start = datetime.now(timezone.utc)
        try:
            result = await self._inner.create(*args, **kwargs)
        except Exception as e:
            end = datetime.now(timezone.utc)
            _record_call(
                agent_id=self._agent_id,
                model=model,
                start=start,
                end=end,
                input_tokens=0,
                output_tokens=0,
                exit_status="failed",
                exit_reason=f"{type(e).__name__}: {str(e)[:600]}",
            )
            raise

        end = datetime.now(timezone.utc)
        usage = getattr(result, "usage", None)
        in_t = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
        out_t = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0
        _record_call(
            agent_id=self._agent_id,
            model=model,
            start=start,
            end=end,
            input_tokens=in_t,
            output_tokens=out_t,
            exit_status="completed",
        )
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _InstrumentedAsyncAnthropic:
    """
    Composition wrapper around anthropic.AsyncAnthropic that records every
    `messages.create()` call to the runs ledger.

    Duck-types as AsyncAnthropic — all other attributes (completions, batches,
    files, etc.) forward to the inner client unchanged. Type hints in the
    Graphiti AnthropicClient constructor are nominal, not enforced.
    """

    def __init__(self, *, api_key: str, agent_id: str, max_retries: int = 1) -> None:
        from anthropic import AsyncAnthropic

        self._inner = AsyncAnthropic(api_key=api_key, max_retries=max_retries)
        self._agent_id = agent_id
        self.messages = _InstrumentedAsyncMessages(self._inner.messages, agent_id)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def make_instrumented_async_anthropic(
    *,
    agent_id: str,
    api_key: str | None = None,
    max_retries: int = 1,
) -> _InstrumentedAsyncAnthropic:
    """Build an instrumented AsyncAnthropic-compatible client for Graphiti."""
    load_env()
    resolved = api_key or os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not resolved:
        raise RuntimeError("ANTHROPIC_API_KEY missing from environment")
    return _InstrumentedAsyncAnthropic(
        api_key=resolved, agent_id=agent_id, max_retries=max_retries
    )


__all__ = [
    "call_claude",
    "make_instrumented_async_anthropic",
]
