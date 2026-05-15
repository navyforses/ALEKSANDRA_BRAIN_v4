"""
ingest_paper.py — Phase 2 sub-phase 2B.

Given one evidence_ledger row, build the full paper text from its
already-chunked paper_chunks rows, then hand it to Graphiti as one
or more Episodes. Graphiti's LLM (Claude Haiku 4.5) extracts
Drug / Gene / Pathway / BrainRegion / Disease / etc. entities and
RELATES_TO edges, writing them into Neo4j under
group_id='hie_research'.

Long papers are split into multiple Episodes (8000-char threshold)
because each Graphiti episode is one LLM call and very long bodies
hurt extraction precision.

kv_state.graphiti_processed:<ledger_id> tracks per-paper status so a
crashed batch run can resume without re-paying for already-processed
papers.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
from graphiti_core.nodes import EpisodeType

from scripts.extraction.graphiti_client import GROUP_ID, get_graphiti
from scripts.extraction.ontology import build_entity_types
from scripts.ledger import _supabase_creds, _supabase_headers, get_state, set_state

EPISODE_CHAR_THRESHOLD = 8000

# MEM-06: ontology constraint loaded once per process. The LLM may classify an
# extracted entity into one of these 8 types or skip it entirely; passing
# excluded_entity_types=['Entity'] suppresses Graphiti's default catch-all
# label so authors / affiliations / funders no longer flood the graph as
# generic entities.
_ENTITY_TYPES, _ONTOLOGY_VERSION = build_entity_types()
_EXCLUDED_ENTITY_TYPES = ["Entity"]


def _fetch_chunks(ledger_id: str) -> list[dict]:
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/paper_chunks",
        params={
            "select": "chunk_index,raw_text",
            "ledger_id": f"eq.{ledger_id}",
            "order": "chunk_index.asc",
        },
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def _fetch_ledger(ledger_id: str) -> dict | None:
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/evidence_ledger",
        params={
            "select": "id,source_type,source_id,retrieval_timestamp,payload_metadata",
            "id": f"eq.{ledger_id}",
            "limit": "1",
        },
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=10,
    )
    r.raise_for_status()
    rows = r.json()
    return rows[0] if rows else None


def _split_for_episodes(
    text: str, threshold: int = EPISODE_CHAR_THRESHOLD
) -> list[str]:
    """
    Split a long paper into segments at paragraph boundaries.
    Each segment <= threshold characters.
    """
    if len(text) <= threshold:
        return [text]

    paragraphs = text.split("\n\n")
    segments: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = (current + "\n\n" + para) if current else para
        if len(candidate) > threshold and current:
            segments.append(current)
            current = para
        else:
            current = candidate
    if current:
        segments.append(current)
    return segments


def _state_key(ledger_id: str) -> str:
    return f"graphiti_processed:{ledger_id}"


def already_processed(ledger_id: str) -> bool:
    state = get_state(_state_key(ledger_id))
    return bool(state and state.get("processed"))


async def ingest_paper_as_episode(ledger_id: str, *, force: bool = False) -> dict:
    """
    Ingest one paper into Graphiti. Returns counter dict.
    """
    counters = {
        "episodes_created": 0,
        "skipped_already_processed": 0,
        "skipped_no_chunks": 0,
        "errors": 0,
    }

    if not force and already_processed(ledger_id):
        counters["skipped_already_processed"] = 1
        return counters

    ledger_row = _fetch_ledger(ledger_id)
    if ledger_row is None:
        counters["errors"] = 1
        return counters

    chunks = _fetch_chunks(ledger_id)
    if not chunks:
        counters["skipped_no_chunks"] = 1
        return counters

    body = "\n\n".join(c["raw_text"] for c in chunks)
    segments = _split_for_episodes(body)

    source_type = ledger_row["source_type"]
    source_id = ledger_row["source_id"]
    meta = ledger_row.get("payload_metadata") or {}
    title = (
        meta.get("title") or meta.get("official_title") or f"{source_type}/{source_id}"
    )

    # reference_time: paper's publication year > ledger.retrieval_timestamp
    ref_time: datetime
    pub_year = meta.get("publication_year")
    if pub_year:
        try:
            ref_time = datetime(int(str(pub_year)[:4]), 1, 1, tzinfo=timezone.utc)
        except (ValueError, TypeError):
            ref_time = datetime.fromisoformat(ledger_row["retrieval_timestamp"])
    else:
        ref_time = datetime.fromisoformat(ledger_row["retrieval_timestamp"])

    g = get_graphiti()
    episode_uuids: list[str] = []
    for i, segment in enumerate(segments):
        name = f"{source_type}/{source_id}" + (
            f" (part {i + 1}/{len(segments)})" if len(segments) > 1 else ""
        )
        try:
            result = await g.add_episode(
                name=name,
                episode_body=segment,
                source_description=(
                    f"{source_type} paper: {title[:120]} "
                    f"[ontology v{_ONTOLOGY_VERSION}]"
                ),
                reference_time=ref_time,
                source=EpisodeType.text,
                group_id=GROUP_ID,
                entity_types=_ENTITY_TYPES,
                excluded_entity_types=_EXCLUDED_ENTITY_TYPES,
            )
            counters["episodes_created"] += 1
            ep_uuid = getattr(
                getattr(result, "episode", None), "uuid", None
            ) or getattr(result, "uuid", None)
            if ep_uuid:
                episode_uuids.append(str(ep_uuid))
        except Exception as e:
            counters["errors"] += 1
            print(f"    [err] add_episode {name}: {type(e).__name__}: {e}")

    # Only mark `processed=True` when ALL segments succeeded. A partial run
    # (some episodes_created, some errors) leaves the state unset so the next
    # batch pass retries the paper. Otherwise crash-resume would silently skip
    # papers whose first segment landed but later segments hit a transient
    # error (rate-limit, LLM timeout, etc.).
    fully_processed = (
        counters["episodes_created"] == len(segments) and counters["errors"] == 0
    )
    if fully_processed:
        set_state(
            _state_key(ledger_id),
            {
                "processed": True,
                "ledger_id": ledger_id,
                "source_type": source_type,
                "source_id": source_id,
                "episode_uuids": episode_uuids,
                "segments": len(segments),
                "processed_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    return counters
