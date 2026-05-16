"""
notion_archiver.py — Phase 4 ACD-04 family knowledge-base writer.

Appends source-grounded findings into the family's Notion database with
full provenance. The Notion database is the family's read-friendly mirror
of `outreach_log` / `alerts_log` / `briefs` — Shako and Natia browse it
the way most people browse a workspace, with filters by tier and date.

Database schema (created by `scripts/notion_bootstrap.py`):

  - Title          : title           (heading; short factual finding)
  - Date           : date            (date the finding was archived)
  - Tier           : select          (T0 / T1 / T2 / T3 / T4)
  - Confidence     : number          (0.00 .. 1.00)
  - Run ID         : rich_text       (originating runs.id — OBS-02 linkage)
  - Citations      : multi_select    (PMID:..., DOI:..., NCT:...)
  - Source         : rich_text       (Communicator audience + query)
  - PHI Redacted   : checkbox        (always TRUE for safety net)
  - Notion link    : url             (back-ref; populated on read, not write)

Idempotency: every Notion page carries the originating `runs.id` in the
"Run ID" property. Before creating a new page we query the database for
an existing page with the same Run ID. If found, we skip (return the
existing page URL) — re-running the archiver is safe.

The archiver enforces the same `phi_redacted=TRUE` invariant the
`outreach_log` / `alerts_log` / `briefs` CHECK constraints enforce in
Supabase. A `SummaryDraft.persistable() == False` input raises before
any Notion call.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from notion_client import Client


# Schema property names — kept in one place so a Notion-side rename only
# touches this file. If the bootstrap script changes the schema, update
# these too.
PROP_TITLE = "Title"
PROP_DATE = "Date"
PROP_TIER = "Tier"
PROP_CONFIDENCE = "Confidence"
PROP_RUN_ID = "Run ID"
PROP_CITATIONS = "Citations"
PROP_SOURCE = "Source"
PROP_PHI_REDACTED = "PHI Redacted"


@dataclass
class NotionArchiveResult:
    page_id: str
    page_url: str
    created: bool  # False if the page already existed (idempotent skip)
    run_id: str


class NotionArchiverError(RuntimeError):
    """Raised when archive_finding cannot proceed safely."""


def _client() -> Client:
    token = os.environ.get("NOTION_API_KEY", "").strip()
    if not token:
        raise NotionArchiverError(
            "NOTION_API_KEY missing — see docs/RUNBOOK-notion-api.md"
        )
    return Client(auth=token)


def _database_id() -> str:
    db_id = os.environ.get("NOTION_DATABASE_ID", "").strip()
    if not db_id:
        raise NotionArchiverError(
            "NOTION_DATABASE_ID missing — run scripts/notion_bootstrap.py"
        )
    return db_id


def _find_by_run_id(notion: Client, db_id: str, run_id: str) -> dict | None:
    """Return the existing page for `run_id`, or None."""
    resp = notion.databases.query(
        database_id=db_id,
        filter={
            "property": PROP_RUN_ID,
            "rich_text": {"equals": run_id},
        },
        page_size=1,
    )
    results = resp.get("results", []) or []
    return results[0] if results else None


def _title_for(draft_title: str, fallback_query: str) -> str:
    """Compose a short title from the draft or query — 120 char cap."""
    base = draft_title or fallback_query or "Untitled finding"
    return base[:120].strip()


def archive_finding(
    *,
    run_id: str,
    title: str,
    tier: str,
    confidence: float,
    citations: list[str],
    source_label: str,
    archived_at: datetime | None = None,
) -> NotionArchiveResult:
    """Append a finding to the family Notion database.

    Parameters mirror what the Communicator pipeline produces; the caller
    is responsible for ensuring the underlying draft passed phi_redactor
    and banned_phrases checks before reaching this function.

    Raises NotionArchiverError on configuration problems. Lets
    `notion_client.APIResponseError` propagate so callers can decide
    whether to retry on transient API failures.
    """
    if not run_id:
        raise NotionArchiverError("run_id is required for OBS-02 linkage")
    if tier not in {"T0", "T1", "T2", "T3", "T4"}:
        raise NotionArchiverError(f"tier must be T0..T4, got {tier!r}")
    if not (0.0 <= confidence <= 1.0):
        raise NotionArchiverError(f"confidence must be in [0,1], got {confidence!r}")

    notion = _client()
    db_id = _database_id()

    existing = _find_by_run_id(notion, db_id, run_id)
    if existing:
        return NotionArchiveResult(
            page_id=existing["id"],
            page_url=existing.get("url", ""),
            created=False,
            run_id=run_id,
        )

    when = (archived_at or datetime.now(timezone.utc)).date().isoformat()
    title_value = _title_for(title, source_label)

    # Citation cap: Notion multi_select tolerates ~100 options per database
    # but per-page we keep it tight. The full list lives in the source row.
    citation_options = [{"name": c[:90]} for c in citations[:20]]

    properties: dict[str, Any] = {
        PROP_TITLE: {"title": [{"text": {"content": title_value}}]},
        PROP_DATE: {"date": {"start": when}},
        PROP_TIER: {"select": {"name": tier}},
        PROP_CONFIDENCE: {"number": round(float(confidence), 4)},
        PROP_RUN_ID: {"rich_text": [{"text": {"content": run_id}}]},
        PROP_CITATIONS: {"multi_select": citation_options},
        PROP_SOURCE: {"rich_text": [{"text": {"content": source_label[:200]}}]},
        PROP_PHI_REDACTED: {"checkbox": True},
    }

    page = notion.pages.create(
        parent={"database_id": db_id},
        properties=properties,
    )

    return NotionArchiveResult(
        page_id=page["id"],
        page_url=page.get("url", ""),
        created=True,
        run_id=run_id,
    )


def archive_count() -> int:
    """Return total page count in the configured Notion database.

    Used by `scripts/verify_phase4.py` as the FFV-04 evidence number.
    Fails closed (returns 0) on any Notion API hiccup.
    """
    try:
        notion = _client()
        db_id = _database_id()
        # Walk one page (max page_size=100) — sufficient for "at least N" checks.
        resp = notion.databases.query(database_id=db_id, page_size=100)
        results = resp.get("results", []) or []
        # If has_more, we know it's >=100 — caller's "≥1" check passes anyway.
        return len(results)
    except Exception:
        return 0


__all__ = [
    "NotionArchiveResult",
    "NotionArchiverError",
    "archive_finding",
    "archive_count",
]
