"""
test_writer_tier.py — Phase C (writer tier → Gemini via OpenRouter).

Covers the new OpenRouter/Gemini paths in translate.py and bilingual.py plus
the defensive {en,ka} JSON parser. No network: _openrouter_complete, the runs
writer, and the budget gate are patched.
"""

from __future__ import annotations

from unittest import mock

import pytest


# --------------------------------------------------------------------------- #
# translate.py — writer-tier OpenRouter path
# --------------------------------------------------------------------------- #
@pytest.fixture
def tr(monkeypatch):
    import scripts.extraction.translate as _tr

    monkeypatch.delenv("MODEL_PROVIDER", raising=False)  # default = openrouter
    monkeypatch.setattr(_tr, "check_daily_budget", lambda **k: (0.0, False))
    monkeypatch.setattr(_tr, "_record_call", mock.Mock(return_value="row"))
    monkeypatch.setattr(_tr, "_openrouter_key", lambda: "sk-or-test")
    return _tr


def test_translate_openrouter_returns_text(tr, monkeypatch):
    monkeypatch.setattr(
        tr, "_openrouter_complete", mock.Mock(return_value=("გამარჯობა", 6, 4))
    )
    out = tr.translate_to_georgian("hello", check_budget=False)
    assert out == "გამარჯობა"
    rec = tr._record_call.call_args.kwargs
    assert rec["exit_status"] == "ok"
    assert rec["model"] == "google/gemini-2.5-flash"


def test_translate_empty_input_skips_call(tr):
    assert tr.translate_to_georgian("   ", check_budget=False) == ""


def test_translate_openrouter_retries_then_fails(tr, monkeypatch):
    monkeypatch.setattr(
        tr, "_openrouter_complete", mock.Mock(side_effect=tr.LLMRefusal("refused"))
    )
    monkeypatch.setattr(tr.time, "sleep", lambda *_a: None)
    with pytest.raises(tr.TranslationFailed):
        tr.translate_to_georgian("hello", max_attempts=2, check_budget=False)


# --------------------------------------------------------------------------- #
# bilingual.py — writer-tier OpenRouter JSON path + parser
# --------------------------------------------------------------------------- #
@pytest.fixture
def bi(monkeypatch):
    import scripts.communicator.bilingual as _bi

    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("BILINGUAL_TEST_MODE", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setattr(_bi, "check_daily_budget", lambda **k: (0.0, False))
    monkeypatch.setattr(_bi, "_record_call", mock.Mock(return_value="row"))
    monkeypatch.setattr(_bi, "_openrouter_key", lambda: "sk-or-test")
    return _bi


def test_parse_en_ka_variants(bi):
    assert bi._parse_en_ka('{"en":"Hi","ka":"გა"}') == {"en": "Hi", "ka": "გა"}
    # tolerant of code fences / surrounding prose
    fenced = "```json\n{\"en\": \"Hi\", \"ka\": \"გა\"}\n```"
    assert bi._parse_en_ka(fenced) == {"en": "Hi", "ka": "გა"}
    assert bi._parse_en_ka("not json at all") is None
    assert bi._parse_en_ka('{"en":"only-en"}') is None


def test_compose_bilingual_openrouter_path(bi, monkeypatch):
    monkeypatch.setattr(
        bi,
        "_openrouter_complete",
        mock.Mock(return_value=('{"en":"Hello","ka":"გამარჯობა"}', 30, 12)),
    )
    out = bi.compose_bilingual("draft a greeting")  # client=None -> Gemini path
    assert out == {"en": "Hello", "ka": "გამარჯობა"}
    rec = bi._record_call.call_args.kwargs
    assert rec["exit_status"] == "completed"
    assert rec["model"] == "google/gemini-2.5-flash"
    assert rec["input_tokens"] == 30 and rec["output_tokens"] == 12


def test_compose_bilingual_test_mode_stub(bi, monkeypatch):
    monkeypatch.setenv("BILINGUAL_TEST_MODE", "1")
    out = bi.compose_bilingual("anything")
    assert out["en"] == "anything"
    assert out["ka"].startswith("[KA-PLACEHOLDER]")
