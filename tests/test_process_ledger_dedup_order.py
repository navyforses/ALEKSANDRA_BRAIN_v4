"""Regression test for the 2026-06-02 dedup-before-translate cost bug.

Before the fix, `populate_papers_from_ledger` invoked `_build_papers_row`
(which calls `build_bilingual` 2x per row → 2 Anthropic Sonnet 4-6 calls)
on EVERY ledger row, then discarded the result if the paper already
existed in `papers`. On a 30-minute cron over 326 ledger rows, that
produced ~31K wasted Sonnet calls per day (~$117/day Anthropic spend).

The fix: derive (source, identifier) cheaply first via
`_ledger_row_identity`, dedup, and only invoke `_build_papers_row` for
genuinely new papers.

This test pins that ordering: when every ledger row is already in
`papers`, `build_bilingual` MUST be called zero times.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import scripts.chunking.process_ledger as pl


_LEDGER_ROW = {
    "id": "ledger-1",
    "source_type": "pubmed",
    "source_id": "12345",
    "raw_artifact_url": "r2://artifacts/pubmed/12345.xml",
    "ingested_at": "2026-06-02T00:00:00Z",
    "payload_metadata": {
        "title": "A sample HIE paper",
        "abstract_excerpt": "Sample abstract about hypoxic-ischemic encephalopathy.",
        "doi": "10.0/sample.12345",
        "authors": "Doe J",
        "journal": "Test J",
        "publication_year": "2025",
    },
}


def _fake_supabase_get(table: str, params: dict[str, Any]) -> list[dict]:
    if table == "evidence_ledger":
        return [_LEDGER_ROW]
    if table == "papers":
        return [
            {
                "source": "pubmed",
                "pmid": "12345",
                "doi": "10.0/sample.12345",
                "ct_id": None,
            }
        ]
    return []


def test_dedup_runs_before_translate() -> None:
    """No translate calls when every ledger row is already in `papers`."""
    with (
        patch.object(pl, "_supabase_get", side_effect=_fake_supabase_get),
        patch.object(pl, "build_bilingual") as bil,
        patch.object(pl, "_supabase_post", return_value=None),
    ):
        bil.side_effect = lambda txt: {"en": txt or "", "ka": ""}
        result = pl.populate_papers_from_ledger()

    assert bil.call_count == 0, (
        f"dedup-before-translate broken: build_bilingual called "
        f"{bil.call_count}x for a paper already in `papers`"
    )
    assert result["skipped_existing"] == 1
    assert result["inserted"] == 0


def test_translate_runs_for_new_paper() -> None:
    """Genuinely new papers still trigger translation (2x: title + abstract)."""

    def _fake_papers_empty(table: str, params: dict[str, Any]) -> list[dict]:
        if table == "evidence_ledger":
            return [_LEDGER_ROW]
        return []

    with (
        patch.object(pl, "_supabase_get", side_effect=_fake_papers_empty),
        patch.object(pl, "build_bilingual") as bil,
        patch.object(pl, "_supabase_post", return_value=None),
    ):
        bil.side_effect = lambda txt: {"en": txt or "", "ka": ""}
        result = pl.populate_papers_from_ledger()

    assert bil.call_count == 2, (
        f"expected 2 translate calls (title + abstract); got {bil.call_count}"
    )
    assert result["skipped_existing"] == 0
    assert result["inserted"] == 1
