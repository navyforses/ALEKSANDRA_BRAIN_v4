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

from scripts.cognition import models
from scripts.cognition.budget import check_daily_budget
from scripts.ledger import _supabase_creds, _supabase_headers, load_env

OPENROUTER_BASE_URL = os.environ.get(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
)


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
    """Resolve $/1M rates via the shared model registry and return cost in USD.

    Pricing lives in ``scripts.cognition.models`` so the worker/thinker/writer
    slugs and the legacy Anthropic ids share one table. The local
    ``_PRICING_USD_PER_M_TOKENS`` constant above is retained only for backward
    import compatibility and is no longer the source of truth.
    """
    in_rate, out_rate = models.price_for(model)
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
# OpenRouter (OpenAI-compatible) path — the default gateway for all tiers.
# ---------------------------------------------------------------------------
class LLMRefusal(RuntimeError):
    """Provider returned an empty/refused completion (no usable text)."""


def _openrouter_key() -> str:
    load_env()
    k = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not k:
        raise RuntimeError("OPENROUTER_API_KEY missing from environment")
    return k


def _openrouter_complete(
    *,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
    api_key: str,
    response_format: dict[str, Any] | None = None,
) -> tuple[str, int, int]:
    """POST one chat-completion to OpenRouter. Returns (text, in_tok, out_tok).

    Args:
        response_format: optional OpenAI-style hint, e.g. {"type": "json_object"},
            forwarded to the gateway for providers that support JSON mode (Gemini).

    Raises:
        LLMRefusal: empty `choices` or empty `content` (refusal / safety stop).
        httpx.HTTPStatusError: non-2xx from the gateway.
    """
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    # Opus 4.8 and other newer models reject `temperature` (HTTP 400). Omit it for
    # those — the gateway/model uses its default. See models.supports_temperature.
    if models.supports_temperature(model):
        body["temperature"] = temperature
    if response_format is not None:
        body["response_format"] = response_format
    r = httpx.post(
        f"{OPENROUTER_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/navyforses/ALEKSANDRA_BRAIN_v4",
            "X-Title": "ALEKSANDRA_BRAIN",
        },
        json=body,
        timeout=180,
    )
    r.raise_for_status()
    data = r.json()
    choices = data.get("choices") or []
    if not choices:
        raise LLMRefusal(f"empty choices (model={model})")
    message = choices[0].get("message") or {}
    text = message.get("content")
    if not text:
        # Defensive: OpenAI-shape refusals return empty/None content with a
        # finish_reason rather than an exception (mirrors the Phase 6.1 Anthropic
        # content==[] lesson). Surface it as a typed error the caller can retry.
        raise LLMRefusal(
            f"empty content (model={model}, "
            f"finish_reason={choices[0].get('finish_reason')})"
        )
    usage = data.get("usage") or {}
    return (
        text,
        int(usage.get("prompt_tokens") or 0),
        int(usage.get("completion_tokens") or 0),
    )


def _run_openrouter(
    *,
    prompt: str,
    agent_id: str,
    model: str,
    system: str | None,
    max_tokens: int,
    temperature: float,
    response_format: dict[str, Any] | None = None,
) -> str:
    api_key = _openrouter_key()
    messages: list[dict[str, str]] = []
    if system is not None:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    start = datetime.now(timezone.utc)
    try:
        text, in_t, out_t = _openrouter_complete(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            api_key=api_key,
            response_format=response_format,
        )
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
    _record_call(
        agent_id=agent_id,
        model=model,
        start=start,
        end=end,
        input_tokens=in_t,
        output_tokens=out_t,
        exit_status="completed",
    )
    return text


# ---------------------------------------------------------------------------
# Anthropic SDK path — native 'claude-*' ids (legacy / MODEL_PROVIDER=anthropic).
# ---------------------------------------------------------------------------
def _run_anthropic(
    *,
    prompt: str,
    agent_id: str,
    model: str,
    system: str | None,
    max_tokens: int,
    temperature: float,
) -> str:
    import anthropic  # deferred — keeps import cheap when llm.py only re-exports

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY missing from environment")

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    # Opus 4.8 and other newer models reject `temperature` (HTTP 400). Omit it
    # for those — the model uses its own default. See models.supports_temperature.
    if models.supports_temperature(model):
        kwargs["temperature"] = temperature
    if system is not None:
        kwargs["system"] = system

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
# Provider-routed synchronous entry point.
# ---------------------------------------------------------------------------
def call_llm(
    *,
    prompt: str,
    agent_id: str,
    task: str | None = None,
    model: str | None = None,
    complexity: int | None = None,
    system: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.2,
    response_format: dict[str, Any] | None = None,
) -> str:
    """
    Send one user message and return the text reply, appending a runs row.

    ``response_format`` is an optional OpenAI-style hint (e.g.
    ``{"type": "json_object"}``) forwarded only on the OpenRouter path for
    providers that support JSON mode; the Anthropic path ignores it (JSON is
    prompt-enforced there). Default ``None`` keeps every existing caller
    byte-identical.

    Model resolution (first wins):
      1. explicit ``model`` argument,
      2. ``models.model_for(task, complexity=...)`` when ``task`` is given —
         a thinker task with ``complexity`` below the gate runs on the worker
         model instead (gated Opus policy),
      3. legacy Sonnet default.

    OpenRouter slugs ('provider/model') route through the OpenRouter gateway;
    native 'claude-*' ids go straight to the Anthropic SDK. Both paths share the
    same daily-budget gate and runs instrumentation.

    Raises:
        RuntimeError: required API key missing.
        BudgetExceeded: today's runs.token_cost sum is over the cap.
        LLMRefusal / anthropic.APIError: provider errors — a failed runs row is
            written first with exit_reason set.
    """
    load_env()
    resolved = model or (
        models.model_for(task, complexity=complexity) if task else "claude-sonnet-4-5"
    )

    # Daily-budget gate — defence-in-depth alongside the n8n cron gate. Raises
    # BudgetExceeded before any provider call when today's spend is over the cap.
    check_daily_budget(raise_on_over=True)

    if models.is_openrouter_model(resolved):
        return _run_openrouter(
            prompt=prompt,
            agent_id=agent_id,
            model=resolved,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
        )
    return _run_anthropic(
        prompt=prompt,
        agent_id=agent_id,
        model=resolved,
        system=system,
        max_tokens=max_tokens,
        temperature=temperature,
    )


def call_claude(
    *,
    prompt: str,
    agent_id: str,
    model: str = "claude-sonnet-4-5",
    system: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.2,
) -> str:
    """Back-compat shim. Prefer ``call_llm(task=...)``.

    Existing call sites that pass a concrete ``model=`` keep working: a native
    'claude-*' id routes to Anthropic, an OpenRouter slug routes to OpenRouter.
    New code should pass ``task=`` and let the registry pick the model.
    """
    return call_llm(
        prompt=prompt,
        agent_id=agent_id,
        model=model,
        system=system,
        max_tokens=max_tokens,
        temperature=temperature,
    )


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


# ---------------------------------------------------------------------------
# Async instrumentation surface — used by Graphiti's OpenAIClient (OpenRouter).
# Mirrors the Anthropic wrapper above but for the OpenAI chat-completions shape
# (`client.chat.completions.create`). Graphiti's internal extraction / dedup /
# summarisation calls each write one `runs` row with agent_id + token+cost.
# ---------------------------------------------------------------------------
class _InstrumentedAsyncChatCompletions:
    """Wraps AsyncOpenAI().chat.completions and records each create()."""

    def __init__(self, inner: Any, agent_id: str) -> None:
        self._inner = inner
        self._agent_id = agent_id

    async def create(self, *args: Any, **kwargs: Any) -> Any:
        # Daily-budget gate — same contract as the sync path. Raises
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
        in_t = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
        out_t = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
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


class _InstrumentedAsyncChat:
    def __init__(self, inner: Any, agent_id: str) -> None:
        self._inner = inner
        self.completions = _InstrumentedAsyncChatCompletions(
            inner.completions, agent_id
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _InstrumentedAsyncOpenAI:
    """
    Composition wrapper around openai.AsyncOpenAI that records every
    `chat.completions.create()` to the runs ledger. Duck-types as AsyncOpenAI —
    all other attributes forward to the inner client unchanged.
    """

    def __init__(
        self, *, api_key: str, base_url: str, agent_id: str, max_retries: int = 1
    ) -> None:
        from openai import AsyncOpenAI

        self._inner = AsyncOpenAI(
            api_key=api_key, base_url=base_url, max_retries=max_retries
        )
        self._agent_id = agent_id
        self.chat = _InstrumentedAsyncChat(self._inner.chat, agent_id)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def make_instrumented_async_openai(
    *,
    agent_id: str,
    api_key: str | None = None,
    base_url: str | None = None,
    max_retries: int = 1,
) -> _InstrumentedAsyncOpenAI:
    """Build an instrumented AsyncOpenAI-compatible client for Graphiti/OpenRouter."""
    load_env()
    resolved = api_key or os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not resolved:
        raise RuntimeError("OPENROUTER_API_KEY missing from environment")
    return _InstrumentedAsyncOpenAI(
        api_key=resolved,
        base_url=base_url or OPENROUTER_BASE_URL,
        agent_id=agent_id,
        max_retries=max_retries,
    )


__all__ = [
    "LLMRefusal",
    "call_claude",
    "call_llm",
    "make_instrumented_async_anthropic",
    "make_instrumented_async_openai",
]
