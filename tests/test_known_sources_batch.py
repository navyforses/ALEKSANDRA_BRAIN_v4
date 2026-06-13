"""tests/test_known_sources_batch.py — P-4 batch dedup (fail-open).

Offline: monkeypatch ledger._supabase_creds + ledger.httpx so no network/DB.
Pins the load-bearing fail-open contract: ANY error (non-200 or raised) returns
an empty set so the fetcher re-fetches rather than silently dropping a lead.
"""

from __future__ import annotations

import scripts.ledger as ledger


class _Resp:
    def __init__(self, status: int, data):
        self.status_code = status
        self._data = data
        self.text = ""

    def json(self):
        return self._data


def _creds(monkeypatch):
    monkeypatch.setattr(ledger, "_supabase_creds", lambda: ("http://x", "k"))


def test_returns_known_subset_single_batch(monkeypatch):
    _creds(monkeypatch)
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(params)
        return _Resp(200, [{"source_id": "111"}, {"source_id": "333"}])

    monkeypatch.setattr(ledger.httpx, "get", fake_get)
    assert ledger.known_sources(["111", "222", "333"], "pubmed") == {"111", "333"}
    assert len(calls) == 1
    assert calls[0]["source_id"].startswith("in.(")


def test_chunks_large_id_lists(monkeypatch):
    _creds(monkeypatch)
    calls = []
    monkeypatch.setattr(
        ledger.httpx, "get", lambda *a, **k: calls.append(1) or _Resp(200, [])
    )
    ledger.known_sources([str(i) for i in range(200)], "pubmed", chunk=80)
    assert len(calls) == 3  # ceil(200 / 80)


def test_fail_open_on_non_200(monkeypatch):
    _creds(monkeypatch)
    monkeypatch.setattr(ledger.httpx, "get", lambda *a, **k: _Resp(500, None))
    assert ledger.known_sources(["1", "2"], "pubmed") == set()


def test_fail_open_on_exception(monkeypatch):
    _creds(monkeypatch)

    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(ledger.httpx, "get", boom)
    assert ledger.known_sources(["1", "2"], "pubmed") == set()


def test_empty_input_makes_no_request(monkeypatch):
    _creds(monkeypatch)

    def boom(*a, **k):
        raise AssertionError("must not query for an empty id list")

    monkeypatch.setattr(ledger.httpx, "get", boom)
    assert ledger.known_sources([], "pubmed") == set()


def test_watermark_key_folds_mode():
    pos = ledger.query_watermark_key("hie treatment", mode="positive")
    neg = ledger.query_watermark_key("hie treatment", mode="negative")
    assert pos.startswith("pubmed_watermark:positive:")
    assert neg.startswith("pubmed_watermark:negative:")
    assert pos != neg  # same query text, different branch → no collision
