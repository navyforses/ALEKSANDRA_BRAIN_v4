"""tests/test_hypothesis_eval.py — COG-6 offline hypothesis-quality harness.

Pure: no neo4j, no DB, no LLM (eval.py imports only phi_guard + the lightweight
resolver). Confirms the gates flag bad rows, pass clean ones, detect unresolved
citations against a supplied PaperIndex, and that --dry-run self-tests to exit 1.
"""

from __future__ import annotations

import scripts.hypothesis.eval as ev
from scripts.hypothesis.backfill_supporting_papers import PaperIndex

_GOOD = {
    "title": "Erythropoietin adjunct to hypothermia in HIE",
    "description": "EPO may extend the neuroprotective window.",
    "hypothesis_type": "drug_repurposing",
    "confidence_level": "moderate",
    "novelty_score": 0.6,
    "feasibility_score": 0.7,
    "supporting_source_ids": [],
}


def test_clean_hypothesis_passes():
    card = ev.evaluate([_GOOD])
    assert card["total"] == 1
    assert card["ok"] == 1
    assert card["flagged"] == 0
    assert card["results"][0]["ok"] is True


def test_bad_row_trips_every_gate():
    bad = {
        "title": "Contact Dr. Kurtzberg",  # PHI in a family-visible field
        "description": "x",
        "hypothesis_type": "made_up",
        "confidence_level": "certain",
        "novelty_score": 2.5,
        "feasibility_score": "n/a",
    }
    flags = ev.evaluate([bad])["results"][0]["flags"]
    assert any(f.startswith("bad_type") for f in flags)
    assert any(f.startswith("bad_confidence") for f in flags)
    assert any("out_of_range_novelty_score" in f for f in flags)
    assert "nonnumeric_feasibility_score" in flags
    assert "phi_in_visible_fields" in flags


def test_unresolved_supporting_papers_flagged():
    idx = PaperIndex(by_pmid={}, by_nct={}, by_doi={})
    h = {**_GOOD, "supporting_source_ids": ["PMID:99999999"]}
    card = ev.evaluate([h], paper_index=idx)
    assert "unresolved_supporting_papers" in card["results"][0]["flags"]


def test_resolved_supporting_papers_clean():
    idx = PaperIndex(by_pmid={"12345678": "paper-1"}, by_nct={}, by_doi={})
    h = {**_GOOD, "supporting_source_ids": ["PMID:12345678"]}
    card = ev.evaluate([h], paper_index=idx)
    assert card["results"][0]["ok"] is True


def test_main_dry_run_exits_one():
    # the built-in fixture deliberately includes a failing row (self-test)
    assert ev.main(["--dry-run"]) == 1


def test_main_no_args_prints_help_and_exits_one():
    assert ev.main([]) == 1
