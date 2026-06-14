"""tests/test_got_provenance.py — COG-5 (honest model) + COG-3 (insert gate).

Offline: monkeypatch _supabase_creds + httpx.post so no DB. Drives
_insert_hypotheses directly to assert (a) generated_by records the model we pass
(the router's real choice), never the legacy 'claude-sonnet-4-5' constant, and
(b) the validator promotes a strong row to 'under_review' but holds a weak one
as 'new'.
"""

from __future__ import annotations

import scripts.hypothesis.got_pipeline as gp


class _Resp:
    def __init__(self, status: int):
        self.status_code = status
        self.text = ""

    def json(self):
        return [{"id": "row-1"}]


def _capture_post(monkeypatch):
    posted: list[dict] = []

    def fake_post(url, json=None, headers=None, timeout=None):
        posted.append(json)
        return _Resp(201)

    monkeypatch.setattr(gp, "_supabase_creds", lambda: ("http://x", "k"))
    monkeypatch.setattr(gp.httpx, "post", fake_post)
    return posted


def test_records_passed_model_not_legacy_constant(monkeypatch):
    posted = _capture_post(monkeypatch)
    strong = {
        "title": "Repurpose metformin for HIE white-matter repair",
        "confidence_level": "moderate",
        "recommended_action": "Contact Dr Kurtzberg to design an infant pilot study.",
    }
    ids = gp._insert_hypotheses([strong], generated_by="anthropic/claude-opus-4-8")

    assert len(ids) == 1  # one row inserted (id is the row's generated UUID)
    assert posted[0]["generated_by"] == "anthropic/claude-opus-4-8"
    assert posted[0]["generated_by"] != gp.MODEL  # never the legacy sonnet constant
    assert posted[0]["status"] == "under_review"  # passed >=3/5 → surfaces


def test_weak_hypothesis_is_held_as_new(monkeypatch):
    posted = _capture_post(monkeypatch)
    weak = {
        "title": "idea",  # < 8 chars
        "confidence_level": "high",
        "novelty_score": 0.95,  # overconfident
        "recommended_action": "consider it",  # vague + 'consider'
    }
    gp._insert_hypotheses([weak], generated_by="anthropic/claude-opus-4-8")
    assert posted[0]["status"] == "new"  # held, will not surface
