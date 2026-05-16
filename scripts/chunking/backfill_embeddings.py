"""
backfill_embeddings.py — Phase 2.5B repair pass.

Cycle 1 of Phase 2.5B inserted 3767 new paper_chunks rows into Supabase but
silently failed at the Qdrant upsert step because `embedder._get_qdrant()`
did not force IPv4 — Windows resolved `localhost` to IPv6 ::1 first and the
busy Qdrant container dropped the handshake. `process_one` caught the
exception and continued, leaving DB rows with `embedding_id IS NULL`. The
idempotency check at the top of `process_one` then locks these rows out of
any re-run of `process_ledger`.

This script rescues those rows without re-extracting / re-chunking:
  1. Pull every paper_chunks row WHERE embedding_id IS NULL, in batches.
  2. Embed via the same fastembed pipeline (`upsert_chunks`) the Phase 2
     pipeline uses, so vector dim + collection layout are byte-identical.
  3. PATCH each row's embedding_id + embedded_at.

Usage:
    .venv/Scripts/python.exe -X utf8 -m scripts.chunking.backfill_embeddings
    .venv/Scripts/python.exe -X utf8 -m scripts.chunking.backfill_embeddings --limit 500
    .venv/Scripts/python.exe -X utf8 -m scripts.chunking.backfill_embeddings --batch-size 100

Cost: $0 (local fastembed, no LLM call). Network: only Qdrant upsert + Supabase PATCH.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

from scripts.chunking.embedder import ChunkRow, upsert_chunks
from scripts.ledger import load_env

from scripts.chunking.process_ledger import _supabase_patch  # reuse


def _fetch_unembedded(cursor, batch_size: int) -> list[dict]:
    cursor.execute(
        """
        SELECT id, ledger_id, source_type, source_id, raw_text
        FROM paper_chunks
        WHERE embedding_id IS NULL
        ORDER BY id
        LIMIT %s
        """,
        (batch_size,),
    )
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def run(batch_size: int = 50, limit: int = 0) -> dict:
    load_env()
    dsn = os.environ["SUPABASE_DB_URL"]

    totals = {"embedded": 0, "batches": 0, "errors": 0, "elapsed_s": 0.0}
    t0 = time.perf_counter()

    with psycopg2.connect(dsn, sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM paper_chunks WHERE embedding_id IS NULL")
            remaining_at_start = cur.fetchone()[0]
            print(f"unembedded chunks at start: {remaining_at_start}")

            processed = 0
            while True:
                if limit and processed >= limit:
                    print(f"hit --limit {limit}, stopping")
                    break

                with conn.cursor() as bcur:
                    rows = _fetch_unembedded(bcur, batch_size)
                if not rows:
                    print("no more NULL rows — done")
                    break

                chunk_rows = [
                    ChunkRow(
                        chunk_id=str(r["id"]),
                        ledger_id=str(r["ledger_id"]),
                        source_type=r["source_type"],
                        source_id=r["source_id"],
                        raw_text=r["raw_text"],
                    )
                    for r in rows
                ]

                try:
                    point_ids = upsert_chunks(chunk_rows)
                except Exception as e:
                    totals["errors"] += 1
                    print(
                        f"  [batch {totals['batches'] + 1}] UPSERT ERROR :: {type(e).__name__}: {e}"
                    )
                    # break — if Qdrant is unreachable, retrying won't help
                    break

                embedded_at = datetime.now(timezone.utc).isoformat()
                for cr, pid in zip(chunk_rows, point_ids):
                    try:
                        _supabase_patch(
                            "paper_chunks",
                            {"embedding_id": pid, "embedded_at": embedded_at},
                            {"id": f"eq.{cr.chunk_id}"},
                        )
                        totals["embedded"] += 1
                    except Exception as e:
                        totals["errors"] += 1
                        print(
                            f"  PATCH ERROR chunk_id={cr.chunk_id[:8]} :: {type(e).__name__}: {e}"
                        )

                totals["batches"] += 1
                processed += len(rows)
                pct = (
                    100.0 * totals["embedded"] / remaining_at_start
                    if remaining_at_start
                    else 100.0
                )
                print(
                    f"  [batch {totals['batches']:3d}] embedded={len(rows)} "
                    f"cum={totals['embedded']}/{remaining_at_start} ({pct:5.1f}%)"
                )

    totals["elapsed_s"] = round(time.perf_counter() - t0, 2)
    return totals


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, default=50)
    ap.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Stop after N chunks embedded (0 = all)",
    )
    args = ap.parse_args()
    t = run(batch_size=args.batch_size, limit=args.limit)
    print()
    print("=" * 60)
    print("backfill_embeddings summary")
    for k, v in t.items():
        print(f"  {k:14} {v}")
    return 0 if t["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
