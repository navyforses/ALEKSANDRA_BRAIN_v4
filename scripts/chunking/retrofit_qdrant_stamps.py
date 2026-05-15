"""
retrofit_qdrant_stamps.py — MEM-04 retrofit for Phase 2A.

Phase 2A's first pass shipped Qdrant points without the four MEM-04
required payload fields: `embedding_model`, `chunker_version`,
`content_hash`, `graphiti_uuid`. This script walks the existing
`papers` collection, joins each point back to its `paper_chunks` row
via the `chunk_id` payload field, computes the content hash, looks up
the Graphiti episode_uuid via kv_state.graphiti_processed:*, and writes
the four fields with Qdrant's `set_payload` (vectors stay intact).

Run:
  python -m scripts.chunking.retrofit_qdrant_stamps             # all points
  python -m scripts.chunking.retrofit_qdrant_stamps --dry-run   # report-only
"""

from __future__ import annotations

import argparse
import sys
from typing import Iterable

import httpx
from qdrant_client import QdrantClient

from scripts.chunking.chunker import CHUNKER_VERSION
from scripts.chunking.embedder import EMBED_MODEL, QDRANT_COLLECTION, _content_hash
from scripts.ledger import _supabase_creds, _supabase_headers, load_env


def _scroll_all_points(client: QdrantClient, batch: int = 256) -> Iterable[dict]:
    offset = None
    while True:
        points, next_offset = client.scroll(
            collection_name=QDRANT_COLLECTION,
            with_payload=True,
            with_vectors=False,
            limit=batch,
            offset=offset,
        )
        for p in points:
            yield {"id": p.id, "payload": p.payload or {}}
        if next_offset is None:
            return
        offset = next_offset


def _fetch_chunks_by_ids(chunk_ids: list[str]) -> dict[str, str]:
    """chunk_id (UUID) -> raw_text. Batched IN() query."""
    if not chunk_ids:
        return {}
    url, key = _supabase_creds()
    out: dict[str, str] = {}
    BATCH = 100
    for i in range(0, len(chunk_ids), BATCH):
        batch = chunk_ids[i : i + BATCH]
        id_list = ",".join(f'"{cid}"' for cid in batch)
        r = httpx.get(
            f"{url}/rest/v1/paper_chunks",
            params={"select": "id,raw_text", "id": f"in.({id_list})"},
            headers=_supabase_headers(key, prefer="count=none"),
            timeout=30,
        )
        r.raise_for_status()
        for row in r.json():
            out[row["id"]] = row["raw_text"]
    return out


def _fetch_graphiti_state() -> dict[str, list[str]]:
    """ledger_id -> [episode_uuid, ...]. From kv_state.graphiti_processed:*."""
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/kv_state",
        params={"select": "key,value", "key": "like.graphiti_processed:*"},
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=20,
    )
    r.raise_for_status()
    out: dict[str, list[str]] = {}
    for row in r.json():
        ledger_id = row["key"].split(":", 1)[1]
        episode_uuids = (row.get("value") or {}).get("episode_uuids") or []
        if episode_uuids:
            out[ledger_id] = episode_uuids
    return out


def run(dry_run: bool = False) -> dict:
    load_env()
    import os

    qclient = QdrantClient(url=os.environ.get("QDRANT_URL", "http://localhost:6333"))

    stamped = 0
    skipped_already = 0
    missing_chunk = 0
    no_episode_yet = 0

    # Phase 1: gather all chunk_ids that need work
    points = list(_scroll_all_points(qclient))
    needs_stamping = [
        p
        for p in points
        if not all(
            k in p["payload"]
            for k in (
                "embedding_model",
                "chunker_version",
                "content_hash",
                "graphiti_uuid",
            )
        )
    ]
    print(f"[retrofit] total={len(points)} need_stamp={len(needs_stamping)}")
    if not needs_stamping:
        return {"total": len(points), "stamped": 0, "skipped_already": len(points)}

    chunk_ids = [
        p["payload"].get("chunk_id")
        for p in needs_stamping
        if p["payload"].get("chunk_id")
    ]
    chunks = _fetch_chunks_by_ids([c for c in chunk_ids if c])
    print(f"[retrofit] fetched {len(chunks)} chunks from Supabase")

    state = _fetch_graphiti_state()
    print(f"[retrofit] {len(state)} ledger_id->episode_uuid mappings")

    # Phase 2: stamp each point
    for p in points:
        payload = p["payload"]
        if all(
            k in payload
            for k in (
                "embedding_model",
                "chunker_version",
                "content_hash",
                "graphiti_uuid",
            )
        ):
            skipped_already += 1
            continue

        chunk_id = payload.get("chunk_id")
        raw_text = chunks.get(chunk_id) if chunk_id else None
        if not raw_text:
            missing_chunk += 1
            continue

        ledger_id = payload.get("ledger_id")
        episode_uuids = state.get(ledger_id) if ledger_id else None
        graphiti_uuid = episode_uuids[0] if episode_uuids else None
        if graphiti_uuid is None:
            no_episode_yet += 1

        new_payload = {
            "embedding_model": EMBED_MODEL,
            "chunker_version": CHUNKER_VERSION,
            "content_hash": _content_hash(raw_text),
            "graphiti_uuid": graphiti_uuid,
        }

        if dry_run:
            stamped += 1
            continue

        qclient.set_payload(
            collection_name=QDRANT_COLLECTION,
            payload=new_payload,
            points=[p["id"]],
        )
        stamped += 1

    return {
        "total": len(points),
        "stamped": stamped,
        "skipped_already": skipped_already,
        "missing_chunk": missing_chunk,
        "no_episode_yet": no_episode_yet,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dry-run", action="store_true", help="Report counts without writing payloads"
    )
    args = ap.parse_args()
    summary = run(dry_run=args.dry_run)
    print("\n=== retrofit summary ===")
    for k, v in summary.items():
        print(f"  {k:>20}  {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
