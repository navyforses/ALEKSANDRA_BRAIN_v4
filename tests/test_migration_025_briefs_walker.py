"""tests/test_migration_025_briefs_walker.py — W4 briefs.sections nested walker (offline).

Walks a briefs.sections JSONB doc, repairs only its bilingual leaves, and PATCHes the
whole object back. Asserts: clean leaves + non-bilingual metadata (dates, citation_id,
status, citations[]) survive verbatim; mirror/blank ka leaves get translated. _rest and
the translator bot are mocked — no network/DB/LLM.
"""

from __future__ import annotations

import copy
import importlib

mod = importlib.import_module("scripts.migrations.025_repair_bilingual_ka")

SECTIONS = {
    "week_start": "2026-06-01",
    "week_end": "2026-06-07",
    "generated_at": "2026-06-07T09:00:00+00:00",
    "summary_lines": [
        {"en": "Three new papers", "ka": "სამი ახალი ნაშრომი"},  # clean -> no-op
    ],
    "papers": [
        {
            "title": {"en": "Erythropoietin", "ka": "ერითროპოეტინი"},  # clean -> no-op
            "citation_id": "PMID:1",
            "relevance_score": 0.9,
        }
    ],
    "hypotheses": [
        {"title": {"en": "EPO synergy", "ka": "EPO synergy"}, "status": "under_review"},
    ],
    "therapies": [],
    "outreach": [],
    "questions": [
        {
            "question": {"en": "Is EPO safe?", "ka": "EPO safe?"},  # no ka -> translate
            "context": {"en": "ctx", "ka": "ctx"},  # mirror -> translate
        }
    ],
    "citations": ["PMID:1"],
}


def test_walk_sections_yields_every_bilingual_leaf():
    leaves = list(mod._walk_sections(copy.deepcopy(SECTIONS)))
    # summary_lines(1) + papers.title(1) + hypotheses.title(1) + question(1) + context(1)
    assert len(leaves) == 5
    kinds = sorted(kind for *_rest, kind in leaves)
    assert kinds.count("title") == 2  # paper title + hypothesis title
    assert kinds.count("prose") == 3  # summary line + question + context


def _mock_rest_and_bot(monkeypatch):
    captured: dict = {}

    def fake_rest(method, path, base, key, body=None):
        if method == "GET":
            return [{"id": "brief-1", "sections": copy.deepcopy(SECTIONS)}]
        if method == "PATCH":
            captured["path"] = path
            captured["body"] = copy.deepcopy(body)
        return []

    monkeypatch.setattr(mod, "_rest", fake_rest)
    monkeypatch.setattr(mod, "translate_title", lambda en: "ქართ-სათაური")
    monkeypatch.setattr(mod, "translate_prose", lambda en: "ქართ-ტექსტი")
    return captured


def test_apply_patches_whole_sections_preserving_untouched_leaves(monkeypatch):
    captured = _mock_rest_and_bot(monkeypatch)
    res = mod._process_briefs(
        table="briefs", base="b", key="k", apply_changes=True, limit=None
    )

    assert res["patched"] == 1
    assert res["translate"] == 3  # hypothesis title + question + context
    s = captured["body"]["sections"]

    # translated leaves
    assert s["hypotheses"][0]["title"] == {"en": "EPO synergy", "ka": "ქართ-სათაური"}
    assert s["questions"][0]["question"] == {"en": "Is EPO safe?", "ka": "ქართ-ტექსტი"}
    assert s["questions"][0]["context"] == {"en": "ctx", "ka": "ქართ-ტექსტი"}

    # clean leaves preserved verbatim
    assert s["papers"][0]["title"] == {"en": "Erythropoietin", "ka": "ერითროპოეტინი"}
    assert s["summary_lines"][0] == {
        "en": "Three new papers",
        "ka": "სამი ახალი ნაშრომი",
    }

    # non-bilingual metadata untouched
    assert s["papers"][0]["citation_id"] == "PMID:1"
    assert s["papers"][0]["relevance_score"] == 0.9
    assert s["hypotheses"][0]["status"] == "under_review"
    assert s["week_start"] == "2026-06-01"
    assert s["citations"] == ["PMID:1"]


def test_dry_run_makes_no_patch(monkeypatch):
    captured = _mock_rest_and_bot(monkeypatch)
    res = mod._process_briefs(
        table="briefs", base="b", key="k", apply_changes=False, limit=None
    )
    assert res["patched"] == 0
    assert res["translate"] == 3
    assert "body" not in captured  # no PATCH issued
