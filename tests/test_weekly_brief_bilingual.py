"""tests/test_weekly_brief_bilingual.py — W3 bilingual title/name handling (offline).

papers.title / hypotheses.title / therapies.name are JSONB at rest, so a live SELECT
hands the dataclasses a {en, ka} dict. The old _bilingual_mirror double-wrapped that
({en:{...},ka:{...}}); the fix reads it verbatim (ka preserved) and only mirrors a
legacy plain string. No DB/network: the dataclasses are constructed directly.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from scripts.communicator.weekly_brief import (
    BriefSections,
    HypothesisRow,
    PaperRow,
    TherapyRow,
    _bilingual_mirror,
)


def test_mirror_reads_dict_verbatim_without_double_wrap():
    out = _bilingual_mirror({"en": "Cord blood for HIE", "ka": "ჭიპლარის სისხლი"})
    assert out == {"en": "Cord blood for HIE", "ka": "ჭიპლარის სისხლი"}
    # both halves are strings, never nested dicts
    assert isinstance(out["en"], str) and isinstance(out["ka"], str)


def test_mirror_ka_falls_back_to_en_when_missing():
    assert _bilingual_mirror({"en": "Only EN"}) == {"en": "Only EN", "ka": "Only EN"}


def test_mirror_legacy_string_is_mirrored():
    assert _bilingual_mirror("Plain legacy") == {
        "en": "Plain legacy",
        "ka": "Plain legacy",
    }


def test_mirror_none_is_empty_pair():
    assert _bilingual_mirror(None) == {"en": "", "ka": ""}


def _sections() -> BriefSections:
    return BriefSections(
        week_start=date(2026, 6, 1),
        week_end=date(2026, 6, 7),
        generated_at=datetime(2026, 6, 7, 9, 0, tzinfo=timezone.utc),
        papers=[
            PaperRow(
                title={"en": "Erythropoietin in HIE", "ka": "ერითროპოეტინი HIE-ში"},
                citation_id="PMID:12345678",
                ingested_at="2026-06-05T00:00:00+00:00",
                relevance_score=0.91,
            )
        ],
        hypotheses=[
            HypothesisRow(
                title={"en": "EPO + hypothermia synergy", "ka": "EPO + ჰიპოთერმია"},
                status="under_review",
                confidence="moderate",
                reviewed_at=None,
                supporting=["PMID:1"],
            )
        ],
        therapies=[
            TherapyRow(
                name={"en": "Melatonin", "ka": "მელატონინი"},
                therapy_type="neuroprotective",
                aleksandra_status="evaluating",
                evidence_in_hie="preclinical",
            )
        ],
    )


def test_to_dict_preserves_real_ka_for_all_row_types():
    d = _sections().to_dict()
    assert d["papers"][0]["title"] == {
        "en": "Erythropoietin in HIE",
        "ka": "ერითროპოეტინი HIE-ში",
    }
    assert d["hypotheses"][0]["title"]["ka"] == "EPO + ჰიპოთერმია"
    assert d["therapies"][0]["name"]["ka"] == "მელატონინი"
    # no double-wrap anywhere: every emitted half is a string
    for section, key in (
        ("papers", "title"),
        ("hypotheses", "title"),
        ("therapies", "name"),
    ):
        field = d[section][0][key]
        assert isinstance(field["en"], str) and isinstance(field["ka"], str)


def test_to_dict_tolerates_legacy_string_rows():
    sec = _sections()
    sec.papers[0].title = "Legacy plain title"
    d = sec.to_dict()
    assert d["papers"][0]["title"] == {
        "en": "Legacy plain title",
        "ka": "Legacy plain title",
    }
