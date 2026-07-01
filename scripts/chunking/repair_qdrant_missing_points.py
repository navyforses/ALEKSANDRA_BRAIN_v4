"""
repair_qdrant_missing_points.py — restore Qdrant points that DB says exist.

Use when `paper_chunks.embedding_id` is fully populated but the Qdrant
`papers` collection has fewer points than Supabase has embedded chunks.

The repair is intentionally conservative:
  - Supabase is read-only.
  - Existing Qdrant points are left untouched.
  - Missing points are re-created with the existing `embedding_id` as the
    Qdrant point id, preserving the DB contract.

Usage:
    .venv/Scripts/python.exe -X utf8 -m scripts.chunking.repair_qdrant_missing_points --dry-run
    $env:QDRANT_URL='http://localhost:6333'; $env:QDRANT_API_KEY='';
    .venv/Scripts/python.exe -X utf8 -m scripts.chunking.repair_qdrant_missing_points
"""

from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass

import psycopg2
import psycopg2.extras
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from scripts.chunking.chunker import CHUNKER_VERSION
from scripts.chunking.embedder import (
    EMBED_MODEL,
    QDRANT_COLLECTION,
    QDRANT_PAYLOAD_TEXT_MAX,
    _content_hash,
    embed_texts,
)
from scripts.ledger import load_env


@dataclass(frozen=True)
class EmbeddedChunk:
    chunk_id: str
    embedding_id: str
    ledger_id: str
    source_type: str
    source_id: str
    raw_text: str


def _qdrant_client() -> QdrantClient:
    load_env()
    url = os.environ.get("QDRANT_URL", "http://localhost:6333").replace(
        "localhost", "127.0.0.1"
    )
    api_key = os.environ.get("QDRANT_API_KEY") or None
    return QdrantClient(url=url, api_key=api_key)


def _fetch_existing_points(client: QdrantClient) -> tuple[set[str], set[str]]:
    point_ids: set[str] = set()
    chunk_ids: set[str] = set()
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=QDRANT_COLLECTION,
            limit=512,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        point_ids.update(str(point.id) for point in points)
        for point in points:
            payload = point.payload or {}
            chunk_id = payload.get("chunk_id")
            if chunk_id:
                chunk_ids.add(str(chunk_id))
        if offset is None:
            return point_ids, chunk_ids


def _fetch_embedded_chunks() -> list[EmbeddedChunk]:
    load_env()
    with psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, embedding_id, ledger_id, source_type, source_id, raw_text
                FROM paper_chunks
                WHERE embedding_id IS NOT NULL
                ORDER BY id
                """
            )
            return [
                EmbeddedChunk(
                    chunk_id=str(row["id"]),
                    embedding_id=str(row["embedding_id"]),
                    ledger_id=str(row["ledger_id"]),
                    source_type=row["source_type"],
                    source_id=row["source_id"],
                    raw_text=row["raw_text"],
                )
                for row in cur.fetchall()
            ]


def _upsert_missing(client: QdrantClient, rows: list[EmbeddedChunk]) -> None:
    vectors = embed_texts(row.raw_text for row in rows)
    points = [
        PointStruct(
            id=row.embedding_id,
            vector=vector,
            payload={
                "chunk_id": row.chunk_id,
                "ledger_id": row.ledger_id,
                "source_type": row.source_type,
                "source_id": row.source_id,
                "text_preview": row.raw_text[:QDRANT_PAYLOAD_TEXT_MAX],
                "embedding_model": EMBED_MODEL,
                "chunker_version": CHUNKER_VERSION,
                "content_hash": _content_hash(row.raw_text),
                "graphiti_uuid": None,
            },
        )
        for row, vector in zip(rows, vectors)
    ]
    client.upsert(collection_name=QDRANT_COLLECTION, points=points)


def run(*, batch_size: int, limit: int, dry_run: bool) -> dict[str, int | float]:
    started = time.perf_counter()
    client = _qdrant_client()
    existing_point_ids, existing_chunk_ids = _fetch_existing_points(client)
    chunks = _fetch_embedded_chunks()
    missing = [row for row in chunks if row.chunk_id not in existing_chunk_ids]
    id_mismatches = [
        row
        for row in chunks
        if row.chunk_id in existing_chunk_ids
        and row.embedding_id not in existing_point_ids
    ]
    if limit:
        missing = missing[:limit]

    totals: dict[str, int | float] = {
        "db_embedded": len(chunks),
        "qdrant_existing": len(existing_point_ids),
        "qdrant_chunks": len(existing_chunk_ids),
        "id_mismatches": len(id_mismatches),
        "missing": len(missing),
        "repaired": 0,
        "batches": 0,
        "elapsed_s": 0.0,
    }
    print(
        f"db_embedded={len(chunks)} qdrant_existing={len(existing_point_ids)} "
        f"qdrant_chunks={len(existing_chunk_ids)} missing={len(missing)} "
        f"id_mismatches={len(id_mismatches)} dry_run={dry_run}"
    )
    if dry_run or not missing:
        totals["elapsed_s"] = round(time.perf_counter() - started, 2)
        return totals

    for i in range(0, len(missing), batch_size):
        batch = missing[i : i + batch_size]
        _upsert_missing(client, batch)
        totals["repaired"] += len(batch)
        totals["batches"] += 1
        print(
            f"  [batch {totals['batches']:3d}] repaired={len(batch)} "
            f"cum={totals['repaired']}/{len(missing)}"
        )

    totals["elapsed_s"] = round(time.perf_counter() - started, 2)
    return totals


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    totals = run(batch_size=args.batch_size, limit=args.limit, dry_run=args.dry_run)
    print()
    print("=" * 60)
    print("repair_qdrant_missing_points summary")
    for key, value in totals.items():
        print(f"  {key:16} {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
