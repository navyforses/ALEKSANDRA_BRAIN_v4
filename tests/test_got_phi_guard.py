"""tests/test_got_phi_guard.py — COG-4 PHI is log-and-flag, never drop.

A doctor name in a family-visible field flags the row (recorded in ai_reasoning.phi_review)
but the hypothesis is STILL inserted — dropping a credible lead would violate the Core
Value. A clean row carries an empty phi_review. No network/DB: all transports mocked.
"""

from __future__ import annotations

import json
import types

import scripts.hypothesis.got_pipeline as gp
from scripts.hypothesis.backfill_supporting_papers import PaperIndex


def _wire(monkeypatch, captured):
    monkeypatch.setattr(gp, "_supabase_creds", lambda: ("http://x", "k"))
    monkeypatch.setattr(gp, "_supabase_headers", lambda key, **kw: {})
    monkeypatch.setattr(gp, "validate", lambda h, **kw: {"passing": True})
    monkeypatch.setattr(
        gp, "_load_paper_index", lambda: PaperIndex(by_pmid={}, by_nct={}, by_doi={})
    )

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.append(json)
        return types.SimpleNamespace(status_code=201, text="", json=lambda: [{}])

    monkeypatch.setattr(gp.httpx, "post", fake_post)


def test_phi_flags_but_never_drops_and_batch_continues(monkeypatch):
    captured: list = []
    _wire(monkeypatch, captured)
    ids = gp._insert_hypotheses(
        [
            {
                "title": "Reach out to Dr. Kurtzberg about EAP cord blood",
                "description": "Clean description.",
                "hypothesis_type": "other",
                "confidence_level": "low",
                "supporting_source_ids": [],
            },
            {
                "title": "Clean cross-disease inference",
                "description": "No PHI here.",
                "hypothesis_type": "other",
                "confidence_level": "low",
                "supporting_source_ids": [],
            },
        ],
        generated_by="m",
    )
    # both rows inserted — the PHI row is NOT dropped
    assert len(ids) == 2

    flagged = json.loads(captured[0]["ai_reasoning"])
    assert "doctor_name" in flagged["phi_review"]

    clean = json.loads(captured[1]["ai_reasoning"])
    assert clean["phi_review"] == []
