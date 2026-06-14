"""tests/test_llm_response_format.py — P-6 response_format wiring (offline).

Asserts call_llm forwards response_format to the OpenRouter completion (and defaults
to None, keeping existing callers byte-identical), and that relevance.score() only
requests JSON mode when ALEKSANDRA_RELEVANCE_JSON_MODE is enabled. No network/DB:
the completion fn, key, budget gate, and runs-writer are all mocked.
"""

from __future__ import annotations

import scripts.cognition.llm as llm
import scripts.scoring.relevance as rel


def _capture_openrouter(monkeypatch):
    captured: dict = {}

    def fake_complete(
        *, model, messages, max_tokens, temperature, api_key, response_format=None
    ):
        captured["response_format"] = response_format
        return ("{}", 1, 1)

    monkeypatch.setattr(llm, "_openrouter_complete", fake_complete)
    monkeypatch.setattr(llm, "_openrouter_key", lambda: "k")
    monkeypatch.setattr(llm, "_record_call", lambda **k: "run-1")
    monkeypatch.setattr(llm, "check_daily_budget", lambda **k: None)
    monkeypatch.setattr(llm, "load_env", lambda: None)
    return captured


def test_call_llm_forwards_response_format(monkeypatch):
    captured = _capture_openrouter(monkeypatch)
    llm.call_llm(
        prompt="hi",
        agent_id="t",
        model="deepseek/deepseek-v4-flash",
        response_format={"type": "json_object"},
    )
    assert captured["response_format"] == {"type": "json_object"}


def test_call_llm_defaults_response_format_none(monkeypatch):
    captured = _capture_openrouter(monkeypatch)
    llm.call_llm(prompt="hi", agent_id="t", model="deepseek/deepseek-v4-flash")
    assert captured["response_format"] is None


def test_relevance_json_mode_off_by_default(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(rel, "call_llm", lambda **kw: captured.update(kw) or "{}")
    monkeypatch.delenv("ALEKSANDRA_RELEVANCE_JSON_MODE", raising=False)
    rel.score("A title", "An abstract")
    assert captured["response_format"] is None


def test_relevance_json_mode_opt_in(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(rel, "call_llm", lambda **kw: captured.update(kw) or "{}")
    monkeypatch.setenv("ALEKSANDRA_RELEVANCE_JSON_MODE", "1")
    rel.score("A title", "An abstract")
    assert captured["response_format"] == {"type": "json_object"}
