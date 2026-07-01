"""tests/test_perception_tick_no_gap.py — OPS-4 worker-independent fallback flag.

run() lazy-imports each fetcher, so we patch them at their SOURCE modules. With
--no-gap the heavy Crawl4AI/Playwright gap-fill is skipped (so the fallback can
run on GitHub Actions) while PubMed/CTgov/preprints/negative still flow. No
network/DB: every fetcher + ledger writer + Telegram is mocked.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import scripts.fetch_ctgov
import scripts.fetch_negative
import scripts.fetch_preprints
import scripts.fetch_pubmed
import scripts.gap_filler
import scripts.perception_tick as pt


def _mock_pipeline(monkeypatch):
    monkeypatch.setattr(pt, "_budget_locked", lambda: False)
    monkeypatch.setattr(pt, "_write_run", lambda **k: "run-1")
    monkeypatch.setattr(pt, "_telegram", lambda msg: None)
    monkeypatch.setattr(
        scripts.fetch_pubmed, "run", MagicMock(return_value={"ledger_inserted": 1})
    )
    monkeypatch.setattr(
        scripts.fetch_ctgov, "run", MagicMock(return_value={"ledger_inserted": 0})
    )
    monkeypatch.setattr(
        scripts.fetch_preprints, "run", MagicMock(return_value={"ledger_inserted": 0})
    )
    monkeypatch.setattr(
        scripts.fetch_negative, "run", MagicMock(return_value={"ledger_inserted": 0})
    )
    gap = MagicMock(return_value={"ledger_inserted": 5})
    monkeypatch.setattr(scripts.gap_filler, "run", gap)
    return gap


def test_no_gap_skips_gap_filler(monkeypatch):
    gap = _mock_pipeline(monkeypatch)
    result = pt.run(small=True, no_gap=True)
    assert result["exit_status"] == "completed"
    assert result["counts"]["gap_filler"] == {"skipped": "no_gap"}
    gap.assert_not_called()


def test_gap_runs_by_default(monkeypatch):
    gap = _mock_pipeline(monkeypatch)
    result = pt.run(small=True)  # no_gap defaults False — byte-compatible
    assert result["exit_status"] == "completed"
    gap.assert_called_once()


def test_cli_threads_no_gap(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr(
        pt, "run", lambda **k: captured.update(k) or {"exit_status": "completed"}
    )
    monkeypatch.setattr(sys, "argv", ["perception_tick", "--no-gap", "--no-telegram"])
    assert pt.main() == 0
    assert captured.get("no_gap") is True


def test_trials_match_import_failure_isolated(monkeypatch):
    _mock_pipeline(monkeypatch)

    def _boom(_name: str):
        raise ModuleNotFoundError("No module named 'anthropic'")

    monkeypatch.setattr(pt, "import_module", _boom)
    result = pt.run(small=True, no_gap=True)
    assert result["exit_status"] == "completed"
    assert "ModuleNotFoundError" in result["counts"]["trials_match"]["error"]
