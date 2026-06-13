"""tests/test_relevance_jsonb.py — P-1 regression.

papers.title / papers.abstract became JSONB ``{en, ka}`` after migration 012.
Before the P-1 fix, ``score()`` called ``.strip()`` on the raw row value, so a
dict title raised ``AttributeError`` and crashed the whole relevance backfill on
the first new paper — leaving ``relevance_score = NULL`` across the corpus.

These tests pin the fix:
  - ``_en()`` coerces dict / str / None to a plain English string.
  - ``score()`` accepts a JSONB-dict title/abstract without raising, and the
    English half (not the Python dict repr) reaches the LLM prompt.
The LLM call is monkeypatched so the test is offline and deterministic.
"""

from __future__ import annotations

import scripts.scoring.relevance as rel


def test_en_helper_coerces_dict_str_none():
    assert rel._en({"en": "x", "ka": "ჯ"}) == "x"
    assert rel._en({"ka": "ჯ"}) == "ჯ"  # falls back to ka when en missing/empty
    assert rel._en({"en": "", "ka": "ჯ"}) == "ჯ"
    assert rel._en("plain") == "plain"
    assert rel._en(None) == ""
    assert rel._en("  pad  ") == "pad"


def test_score_handles_jsonb_dict_without_crashing(monkeypatch):
    captured: dict[str, str] = {}

    def fake_call_llm(*, prompt, agent_id, task, system, max_tokens, temperature):
        captured["prompt"] = prompt
        return (
            '{"relevance_score": 0.82, "direct_relevance": true, '
            '"cross_disease_relevance": false, "cross_disease_source": "", '
            '"rationale": "directly addresses HIE"}'
        )

    monkeypatch.setattr(rel, "call_llm", fake_call_llm)

    # JSONB dicts, exactly as PostgREST returns papers.title / papers.abstract.
    result = rel.score(
        {"en": "Hypothermia for neonatal HIE", "ka": "ჰიპოთერმია"},
        {"en": "We studied therapeutic hypothermia in infants.", "ka": "..."},
    )

    assert result.score == 0.82
    assert result.direct is True
    # The English half — not the dict repr — must reach the prompt.
    assert "Hypothermia for neonatal HIE" in captured["prompt"]
    assert "{'en'" not in captured["prompt"]


def test_score_empty_dict_is_treated_as_empty(monkeypatch):
    # An empty/blank bilingual value should short-circuit to the empty-paper
    # result without ever calling the LLM.
    def boom(**_kwargs):  # pragma: no cover - must not be called
        raise AssertionError("call_llm should not run for empty input")

    monkeypatch.setattr(rel, "call_llm", boom)

    result = rel.score({"en": "", "ka": ""}, {"en": "", "ka": ""})
    assert result.score is None
    assert "empty paper" in result.rationale
