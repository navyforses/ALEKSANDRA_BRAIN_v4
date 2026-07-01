from __future__ import annotations

from scripts.family_visibility import fire_workflows as fw


def test_daily_digest_accepts_bilingual_paper_titles(monkeypatch):
    def fake_get(path: str, params: dict[str, str]) -> list[dict]:
        if path == "papers":
            return [
                {
                    "title": {"en": "English title", "ka": "ქართული სათაური"},
                    "relevance_score": 0.91,
                }
            ]
        if path == "runs":
            return [{"token_cost": "0.25"}]
        return []

    monkeypatch.setattr(fw, "_get", fake_get)

    digest = fw.compose_daily_digest()

    assert "top_papers=1" in digest
    assert "spend=$0.250000" in digest
    assert "ქართული სათაური" in digest
    assert "English title" not in digest


def test_urgent_alert_accepts_bilingual_paper_titles(monkeypatch):
    def fake_get(path: str, params: dict[str, str]) -> list[dict]:
        if path == "papers":
            return [
                {
                    "title": {"en": "Fallback title", "ka": ""},
                    "relevance_score": 0.95,
                }
            ]
        return []

    monkeypatch.setattr(fw, "_get", fake_get)

    alert = fw.compose_urgent_alert()

    assert "high_relevance_papers=1" in alert
    assert "Fallback title" in alert
