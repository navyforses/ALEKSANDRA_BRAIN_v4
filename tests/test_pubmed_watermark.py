"""tests/test_pubmed_watermark.py — P-3 incremental date watermark (offline).

Mocks fetch_pubmed's collaborators (Entrez search via _esearch_pmids, kv_state
read/write, batch dedup) so no network/DB. Pins: a stored watermark flows into
esearch as mindate; no watermark means no mindate (first run = full pull); a
clean query advances the watermark.
"""

from __future__ import annotations

import scripts.fetch_pubmed as fp


def _no_entrez(monkeypatch):
    monkeypatch.setattr(fp, "configure_entrez", lambda: False)
    monkeypatch.setattr(fp, "known_sources", lambda ids, st, **k: set())


def test_stored_watermark_becomes_mindate(monkeypatch):
    _no_entrez(monkeypatch)
    captured: dict = {}

    def fake_esearch(query, retmax, mindate=None):
        captured["mindate"] = mindate
        return []

    monkeypatch.setattr(fp, "_esearch_pmids", fake_esearch)
    monkeypatch.setattr(fp, "get_state", lambda key: {"last_edat": "2026/06/01"})
    sets: list = []
    monkeypatch.setattr(fp, "set_state", lambda key, value: sets.append((key, value)))

    fp.run(queries=["hie treatment"], retmax=3)

    assert captured["mindate"] == "2026/06/01"
    # the watermark advanced after a clean query
    assert sets and sets[0][0].startswith("pubmed_watermark:")
    assert "last_edat" in sets[0][1]


def test_no_watermark_means_no_mindate(monkeypatch):
    _no_entrez(monkeypatch)
    captured: dict = {}

    def fake_esearch(query, retmax, mindate=None):
        captured["mindate"] = mindate
        return []

    monkeypatch.setattr(fp, "_esearch_pmids", fake_esearch)
    monkeypatch.setattr(fp, "get_state", lambda key: None)
    monkeypatch.setattr(fp, "set_state", lambda key, value: None)

    fp.run(queries=["hie treatment"], retmax=3)
    assert captured["mindate"] is None


def test_get_state_error_does_not_break_run(monkeypatch):
    # A kv_state read failure must degrade to a full pull, not crash the tick.
    _no_entrez(monkeypatch)
    captured: dict = {}

    def fake_esearch(query, retmax, mindate=None):
        captured["mindate"] = mindate
        return []

    def boom(key):
        raise RuntimeError("kv_state unreachable")

    monkeypatch.setattr(fp, "_esearch_pmids", fake_esearch)
    monkeypatch.setattr(fp, "get_state", boom)
    monkeypatch.setattr(fp, "set_state", lambda key, value: None)

    counts = fp.run(queries=["hie treatment"], retmax=3)
    assert captured["mindate"] is None
    assert counts["queries_run"] == 1
