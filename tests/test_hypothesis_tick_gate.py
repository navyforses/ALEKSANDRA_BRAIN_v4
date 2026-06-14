"""tests/test_hypothesis_tick_gate.py — COG-1 entity-count gate (offline).

The gate must spend NO LLM budget on a quiet week. Mocks _supabase_creds /
httpx / kv_state so there is no DB; asserts run_first is never called below
threshold and the watermark advances only on a real run.
"""

from __future__ import annotations

import scripts.hypothesis.got_pipeline as gp


class _Resp:
    def __init__(self, headers):
        self.headers = headers


def test_ledger_count_parses_content_range(monkeypatch):
    monkeypatch.setattr(gp, "_supabase_creds", lambda: ("http://x", "k"))
    monkeypatch.setattr(
        gp.httpx, "get", lambda *a, **k: _Resp({"content-range": "0-0/42"})
    )
    assert gp._ledger_count() == 42


def test_should_tick_threshold(monkeypatch):
    monkeypatch.setattr(gp, "_ledger_count", lambda: 42)
    monkeypatch.setattr(gp, "get_state", lambda key: {"count": 40})
    assert gp.should_tick(min_new_entities=5)[0] is False  # delta 2 < 5

    monkeypatch.setattr(gp, "get_state", lambda key: {"count": 37})
    assert gp.should_tick(min_new_entities=5)[0] is True  # delta 5 >= 5


def test_should_tick_missing_or_malformed_watermark(monkeypatch):
    monkeypatch.setattr(gp, "_ledger_count", lambda: 10)
    monkeypatch.setattr(gp, "get_state", lambda key: None)
    go, current, last = gp.should_tick(min_new_entities=5)
    assert last == 0 and go is True


def test_run_first_gated_skips_without_llm(monkeypatch):
    monkeypatch.setattr(gp, "load_env", lambda: None)
    monkeypatch.setattr(gp, "should_tick", lambda min_new_entities=5: (False, 42, 40))

    def boom(*a, **k):
        raise AssertionError("run_first must NOT be called below threshold")

    monkeypatch.setattr(gp, "run_first", boom)
    result = gp.run_first_gated()
    assert result["skipped"] is True
    assert result["delta"] == 2


def test_run_first_gated_runs_and_advances_watermark(monkeypatch):
    monkeypatch.setattr(gp, "load_env", lambda: None)
    monkeypatch.setattr(gp, "should_tick", lambda min_new_entities=5: (True, 50, 40))
    monkeypatch.setattr(
        gp, "run_first", lambda max_hypotheses=5: {"hypotheses_inserted": 3}
    )
    sets: list = []
    monkeypatch.setattr(gp, "set_state", lambda key, value: sets.append((key, value)))

    result = gp.run_first_gated()
    assert result["skipped"] is False
    assert result["ledger_count"] == 50
    assert sets and sets[0][0] == gp._HYP_WATERMARK_KEY
    assert sets[0][1]["count"] == 50
