"""tests/test_hypothesis_validate.py — COG-3 deterministic rules (pure, no I/O)."""

from __future__ import annotations

from scripts.hypothesis.validate import SURFACED_STATUSES, validate


def test_strong_hypothesis_passes():
    v = validate(
        {
            "title": "Repurpose metformin for HIE white-matter repair",
            "confidence_level": "moderate",
            "recommended_action": "Contact Dr Kurtzberg to design an infant pilot.",
        }
    )
    assert v["passing"] is True
    assert v["passing_count"] >= 3


def test_overconfident_high_novelty_fails_rule2():
    v = validate(
        {
            "title": "x" * 10,
            "confidence_level": "high",
            "novelty_score": 0.95,
            "recommended_action": "Run a concrete infant pilot study right now.",
        }
    )
    assert v["checks"]["confidence_not_overconfident"] is False


def test_empty_citations_not_vacuously_true():
    v = validate({"title": "x" * 10, "supporting_papers": []})
    assert v["checks"]["citations_round_trip"] is False


def test_citation_round_trip_uses_ledger_ids():
    h = {"title": "x" * 10, "supporting_papers": ["a", "b"]}
    assert validate(h, ledger_ids={"a", "b"})["checks"]["citations_round_trip"] is True
    assert validate(h, ledger_ids={"a"})["checks"]["citations_round_trip"] is False
    # un-fetched (None) => cannot evaluate => False, never vacuously True
    assert validate(h)["checks"]["citations_round_trip"] is False


def test_consider_action_is_not_concrete():
    v = validate({"title": "x" * 10, "recommended_action": "consider something later"})
    assert v["checks"]["action_concrete"] is False


def test_entity_match_drives_rule4():
    h = {"title": "x" * 10}
    assert validate(h, entity_match=True)["checks"]["title_grounds_in_graph"] is True
    assert validate(h, entity_match=None)["checks"]["title_grounds_in_graph"] is False


def test_surfaced_statuses_excludes_new():
    assert "new" not in SURFACED_STATUSES
    assert "under_review" in SURFACED_STATUSES
