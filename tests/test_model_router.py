"""
test_model_router.py — Phase A (multi-provider tiered routing).

Covers the new registry (scripts.cognition.models) and the provider dispatch
in scripts.cognition.llm.call_llm. No network: the OpenRouter HTTP call,
budget gate, and runs writer are all patched.
"""

from __future__ import annotations

from unittest import mock

import pytest

from scripts.cognition import models


# --------------------------------------------------------------------------- #
# models registry
# --------------------------------------------------------------------------- #
def test_task_to_tier_mapping():
    assert models.tier_for("extraction") == "worker"
    assert models.tier_for("got") == "thinker"
    assert models.tier_for("translate") == "writer"
    # unknown task falls back to the cheap worker tier, never an expensive one
    assert models.tier_for("does_not_exist") == "worker"


def test_model_for_default_openrouter():
    assert models.model_for("extraction") == "deepseek/deepseek-chat"
    assert models.model_for("got") == "anthropic/claude-opus-4-8"
    assert models.model_for("translate") == "google/gemini-2.5-flash"


def test_model_for_anthropic_rollback(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "anthropic")
    assert models.model_for("extraction") == "claude-haiku-4-5-20251001"
    assert models.model_for("got") == "claude-opus-4-8"
    assert models.model_for("translate") == "claude-sonnet-4-5"


def test_price_for_exact_prefix_and_fallback():
    assert models.price_for("deepseek/deepseek-chat") == (0.27, 1.10)
    # prefix match: date-suffixed native id resolves to the family key
    assert models.price_for("claude-opus-4-8") == (15.00, 75.00)
    # unknown slug → conservative fallback (never under-report)
    assert models.price_for("some/unknown-model") == models.FALLBACK_PRICE


def test_is_openrouter_model():
    assert models.is_openrouter_model("deepseek/deepseek-chat") is True
    assert models.is_openrouter_model("anthropic/claude-opus-4-8") is True
    assert models.is_openrouter_model("claude-sonnet-4-5") is False


def test_thinker_gating_by_complexity():
    lo = models.THINKER_COMPLEXITY_MIN - 1
    hi = models.THINKER_COMPLEXITY_MIN + 1
    # short/simple reasoning runs on the cheap worker model
    assert models.model_for("got", complexity=lo) == "deepseek/deepseek-chat"
    # long/complex reasoning escalates to Opus
    assert models.model_for("got", complexity=hi) == "anthropic/claude-opus-4-8"
    # no complexity hint → full tier model (quality-safe default)
    assert models.model_for("got") == "anthropic/claude-opus-4-8"
    # gating never downgrades a worker task upward
    assert models.model_for("extraction", complexity=hi) == "deepseek/deepseek-chat"


def test_crew_llm_prefix_and_rollback(monkeypatch):
    assert models.crew_llm("worker") == "openrouter/deepseek/deepseek-chat"
    assert models.crew_llm("thinker") == "openrouter/anthropic/claude-opus-4-8"
    assert models.crew_llm("writer") == "openrouter/google/gemini-2.5-flash"
    monkeypatch.setenv("MODEL_PROVIDER", "anthropic")
    assert models.crew_llm("worker") == "claude-haiku-4-5-20251001"
    assert models.crew_llm("thinker") == "claude-opus-4-8"


# --------------------------------------------------------------------------- #
# call_llm provider dispatch
# --------------------------------------------------------------------------- #
@pytest.fixture
def llm(monkeypatch):
    """Import llm with budget gate + runs writer neutralised."""
    from scripts.cognition import llm as _llm

    monkeypatch.setattr(_llm, "check_daily_budget", lambda **k: (0.0, False))
    monkeypatch.setattr(_llm, "_record_call", mock.Mock(return_value="row-id"))
    monkeypatch.setattr(_llm, "load_env", lambda: None)
    return _llm


def test_call_llm_task_routes_to_openrouter(llm, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    fake = mock.Mock(return_value=("hello from deepseek", 12, 7))
    monkeypatch.setattr(llm, "_openrouter_complete", fake)

    out = llm.call_llm(prompt="hi", agent_id="analyzer_graphiti", task="extraction")

    assert out == "hello from deepseek"
    # correct model slug was sent
    assert fake.call_args.kwargs["model"] == "deepseek/deepseek-chat"
    # a completed runs row was recorded with the real token counts
    rec = llm._record_call.call_args.kwargs
    assert rec["exit_status"] == "completed"
    assert rec["input_tokens"] == 12 and rec["output_tokens"] == 7
    assert rec["model"] == "deepseek/deepseek-chat"


def test_call_llm_native_id_routes_to_anthropic(llm, monkeypatch):
    sentinel = mock.Mock(return_value="anthropic-reply")
    monkeypatch.setattr(llm, "_run_anthropic", sentinel)
    or_path = mock.Mock()
    monkeypatch.setattr(llm, "_run_openrouter", or_path)

    out = llm.call_llm(prompt="hi", agent_id="hypothesis", model="claude-sonnet-4-5")

    assert out == "anthropic-reply"
    or_path.assert_not_called()
    assert sentinel.call_args.kwargs["model"] == "claude-sonnet-4-5"


def test_call_llm_records_failure_then_raises(llm, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    boom = mock.Mock(side_effect=llm.LLMRefusal("empty content"))
    monkeypatch.setattr(llm, "_openrouter_complete", boom)

    with pytest.raises(llm.LLMRefusal):
        llm.call_llm(prompt="hi", agent_id="writer", task="translate")

    rec = llm._record_call.call_args.kwargs
    assert rec["exit_status"] == "failed"
    assert rec["input_tokens"] == 0 and rec["output_tokens"] == 0
    assert "LLMRefusal" in rec["exit_reason"]


def test_call_claude_backcompat_routes_by_model(llm, monkeypatch):
    """Legacy call_claude(model='claude-...') still lands on the Anthropic path."""
    sentinel = mock.Mock(return_value="ok")
    monkeypatch.setattr(llm, "_run_anthropic", sentinel)

    out = llm.call_claude(prompt="hi", agent_id="spider")  # default sonnet id

    assert out == "ok"
    assert sentinel.call_args.kwargs["model"] == "claude-sonnet-4-5"


def test_budget_gate_blocks_before_provider_call(llm, monkeypatch):
    """A BudgetExceeded from the gate must fire before any provider call."""
    from scripts.cognition.budget import BudgetExceeded

    def over(**_k):
        raise BudgetExceeded(99.0, 5.0)

    monkeypatch.setattr(llm, "check_daily_budget", over)
    or_path = mock.Mock()
    monkeypatch.setattr(llm, "_run_openrouter", or_path)

    with pytest.raises(BudgetExceeded):
        llm.call_llm(prompt="hi", agent_id="analyzer", task="extraction")
    or_path.assert_not_called()


# --------------------------------------------------------------------------- #
# Graphiti instrumentation — AsyncOpenAI chat.completions recording
# --------------------------------------------------------------------------- #
def test_instrumented_openai_records_completion_usage(llm):
    import asyncio

    class _Usage:
        prompt_tokens = 20
        completion_tokens = 9

    class _Result:
        usage = _Usage()

    class _Inner:
        async def create(self, **kwargs):
            return _Result()

    comp = llm._InstrumentedAsyncChatCompletions(_Inner(), "analyzer_graphiti")
    out = asyncio.run(comp.create(model="deepseek/deepseek-chat", messages=[]))

    assert out is not None
    rec = llm._record_call.call_args.kwargs
    assert rec["exit_status"] == "completed"
    assert rec["input_tokens"] == 20 and rec["output_tokens"] == 9
    assert rec["model"] == "deepseek/deepseek-chat"
    assert rec["agent_id"] == "analyzer_graphiti"


def test_instrumented_openai_records_failure(llm):
    import asyncio

    class _Inner:
        async def create(self, **kwargs):
            raise RuntimeError("deepseek 502")

    comp = llm._InstrumentedAsyncChatCompletions(_Inner(), "analyzer_graphiti")
    with pytest.raises(RuntimeError):
        asyncio.run(comp.create(model="deepseek/deepseek-chat", messages=[]))

    rec = llm._record_call.call_args.kwargs
    assert rec["exit_status"] == "failed"
    assert rec["input_tokens"] == 0 and rec["output_tokens"] == 0
    assert "RuntimeError" in rec["exit_reason"]
