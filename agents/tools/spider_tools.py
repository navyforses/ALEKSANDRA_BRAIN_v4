"""
spider_tools.py — Phase 2 Spider agent tools.

Two thin CrewAI @tool wrappers over Phase 1 + Phase 2A scripts:

  check_ledger_new(hours_back)  → counts new evidence_ledger rows in the
      last N hours, grouped by source_type, so the agent can decide whether
      a chunking pass is warranted.

  trigger_chunking(ledger_id)   → invokes scripts.chunking.process_ledger
      for one row (extract → chunk → embed → Qdrant upsert → embedding_id
      patch). Returns counters.

Both return JSON-serialisable dicts so CrewAI's LLM can read them.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone

import httpx
from crewai.tools import tool

from scripts.ledger import _supabase_creds, _supabase_headers, load_env


@tool("check_ledger_new")
def check_ledger_new(hours_back: int = 6) -> str:
    """Return a JSON summary of evidence_ledger rows ingested in the last
    `hours_back` hours, grouped by source_type. Use this to decide whether
    to trigger downstream chunking + Graphiti ingestion."""
    load_env()
    url, key = _supabase_creds()
    since = (datetime.now(timezone.utc) - timedelta(hours=hours_back)).isoformat()
    r = httpx.get(
        f"{url}/rest/v1/evidence_ledger",
        params={
            "select": "id,source_type,source_id,ingested_at",
            "ingested_at": f"gte.{since}",
        },
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=20,
    )
    r.raise_for_status()
    rows = r.json()
    by_source: Counter = Counter(row["source_type"] for row in rows)
    return json.dumps(
        {
            "since": since,
            "hours_back": hours_back,
            "total_new": len(rows),
            "by_source": dict(by_source),
            "ledger_ids": [row["id"] for row in rows][:50],
        }
    )


@tool("trigger_chunking")
def trigger_chunking(ledger_id: str) -> str:
    """Run the chunk → embed → Qdrant pipeline for one ledger_id. Idempotent:
    if paper_chunks rows already exist for this ledger, no-op. Returns a
    JSON counter dict."""
    from scripts.chunking.process_ledger import process_one

    load_env()
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/evidence_ledger",
        params={
            "select": "id,source_type,source_id,retrieval_timestamp,raw_artifact_url,payload_metadata",
            "id": f"eq.{ledger_id}",
            "limit": "1",
        },
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=15,
    )
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return json.dumps({"error": f"ledger_id {ledger_id} not found"})
    counters = process_one(rows[0])
    return json.dumps(counters)


__all__ = ["check_ledger_new", "trigger_chunking"]
