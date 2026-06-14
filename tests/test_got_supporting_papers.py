"""tests/test_got_supporting_papers.py — COG-2 supporting_papers populated at insert.

_insert_hypotheses now resolves cited PMID/NCT/DOI to papers.id via the paper index
and writes them into supporting_papers (was always []). No network/DB: _load_paper_index,
_supabase_creds/_headers, validate, and httpx.post are mocked; the POST body is captured.
"""

from __future__ import annotations

import types

import scripts.hypothesis.got_pipeline as gp
from scripts.hypothesis.backfill_supporting_papers import PaperIndex


def _wire(monkeypatch, captured, *, index):
    monkeypatch.setattr(gp, "_supabase_creds", lambda: ("http://x", "k"))
    monkeypatch.setattr(gp, "_supabase_headers", lambda key, **kw: {})
    monkeypatch.setattr(gp, "validate", lambda h, **kw: {"passing": True})

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.append(json)
        return types.SimpleNamespace(status_code=201, text="", json=lambda: [{}])

    monkeypatch.setattr(gp.httpx, "post", fake_post)
    if isinstance(index, Exception):
        monkeypatch.setattr(
            gp, "_load_paper_index", lambda: (_ for _ in ()).throw(index)
        )
    else:
        monkeypatch.setattr(gp, "_load_paper_index", lambda: index)


def test_pmid_resolves_to_papers_id(monkeypatch):
    captured: list = []
    idx = PaperIndex(by_pmid={"12345678": "paper-uuid-1"}, by_nct={}, by_doi={})
    _wire(monkeypatch, captured, index=idx)
    ids = gp._insert_hypotheses(
        [
            {
                "title": "T",
                "description": "D",
                "hypothesis_type": "drug_repurposing",
                "confidence_level": "moderate",
                "supporting_source_ids": ["PMID:12345678"],
            }
        ],
        generated_by="m",
    )
    assert len(ids) == 1
    assert captured[0]["supporting_papers"] == ["paper-uuid-1"]


def test_index_load_failure_is_fail_open(monkeypatch):
    captured: list = []
    _wire(monkeypatch, captured, index=RuntimeError("network down"))
    ids = gp._insert_hypotheses(
        [
            {
                "title": "T",
                "description": "D",
                "hypothesis_type": "other",
                "confidence_level": "low",
                "supporting_source_ids": ["PMID:12345678"],
            }
        ],
        generated_by="m",
    )
    # the lead is still inserted; supporting_papers just stays empty
    assert len(ids) == 1
    assert captured[0]["supporting_papers"] == []
