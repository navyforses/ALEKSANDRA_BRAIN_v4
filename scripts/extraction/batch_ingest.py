"""
batch_ingest.py — Phase 2 sub-phase 2B.3.

Iterate every evidence_ledger row, skip those already marked
`kv_state.graphiti_processed:<id>.processed=True`, and hand each
remaining row to `ingest_paper_as_episode` so Graphiti extracts entities
and relationships into Neo4j under group_id='hie_research'.

Safety rails:
  - hard-stop after `MAX_ERRORS` cumulative errors (prevents runaway
    Anthropic spend if Haiku is rate-limited or auth-failed)
  - per-paper try/except — one bad paper never aborts the batch
  - resume-safe: kv_state.graphiti_processed is the source of truth;
    a re-run skips fully-processed papers, retries the rest

Run:  python -m scripts.extraction.batch_ingest [--force] [--limit N]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time

import httpx

from scripts.extraction.graphiti_client import (
    close_graphiti,
    ensure_indices,
    get_graphiti,
)
from scripts.extraction.ingest_paper import (
    already_processed,
    ingest_paper_as_episode,
)
from scripts.ledger import _supabase_creds, _supabase_headers

MAX_ERRORS = 3
GROUP_ID = "hie_research"


async def _count_entities() -> int | None:
    """Count Graphiti-extracted entities under group_id='hie_research'.

    Returns None on driver error so the formatter falls back to 0 without
    poisoning the Telegram summary with NaN.
    """
    try:
        g = get_graphiti()
        async with g.driver.session() as session:
            result = await session.run(
                "MATCH (n:Entity {group_id: $gid}) RETURN count(n) AS c",
                gid=GROUP_ID,
            )
            record = await result.single()
            return int(record["c"]) if record else 0
    except Exception:
        return None


def _fetch_all_ledger_ids() -> list[tuple[str, str, str]]:
    """Return [(ledger_id, source_type, source_id), ...] in created_at order."""
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/evidence_ledger",
        params={
            "select": "id,source_type,source_id,ingested_at",
            "order": "ingested_at.asc",
        },
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=15,
    )
    r.raise_for_status()
    return [(row["id"], row["source_type"], row["source_id"]) for row in r.json()]


async def run_batch(*, force: bool, limit: int | None) -> dict:
    grand = {
        "papers_seen": 0,
        "papers_processed": 0,
        "papers_skipped": 0,
        "episodes_created": 0,
        "errors": 0,
    }

    ledger_rows = _fetch_all_ledger_ids()
    print(f"[batch] {len(ledger_rows)} ledger rows total")

    await ensure_indices()

    entities_before = await _count_entities()
    grand["entities_before"] = entities_before if entities_before is not None else 0

    t_start = time.time()
    for idx, (lid, stype, sid) in enumerate(ledger_rows, start=1):
        if limit is not None and grand["papers_processed"] >= limit:
            print(f"[batch] reached --limit {limit}; stopping early")
            break
        grand["papers_seen"] += 1

        if not force and already_processed(lid):
            grand["papers_skipped"] += 1
            continue

        label = f"{stype}/{sid}"
        print(f"[{idx}/{len(ledger_rows)}] {label} ({lid[:8]}...)")
        t0 = time.time()
        try:
            counters = await ingest_paper_as_episode(lid, force=force)
        except Exception as e:
            grand["errors"] += 1
            print(f"    [fatal] {type(e).__name__}: {e}")
            if grand["errors"] >= MAX_ERRORS:
                print(
                    f"[batch] HARD STOP — {grand['errors']} errors >= MAX_ERRORS={MAX_ERRORS}"
                )
                break
            continue

        dt = time.time() - t0
        grand["episodes_created"] += counters["episodes_created"]
        grand["errors"] += counters["errors"]
        grand["papers_processed"] += 1
        print(
            f"    episodes={counters['episodes_created']} "
            f"errors={counters['errors']} elapsed={dt:.1f}s"
        )

        if grand["errors"] >= MAX_ERRORS:
            print(
                f"[batch] HARD STOP — {grand['errors']} errors >= MAX_ERRORS={MAX_ERRORS}"
            )
            break

    entities_after = await _count_entities()
    grand["entities_after"] = entities_after if entities_after is not None else 0
    grand["entities_added"] = max(
        0, grand["entities_after"] - grand["entities_before"]
    )

    await close_graphiti()
    grand["elapsed_total_s"] = round(time.time() - t_start, 1)
    return grand


def main() -> int:
    p = argparse.ArgumentParser(
        description="Batch Graphiti ingest of evidence_ledger rows"
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Re-process every paper even if already in kv_state",
    )
    p.add_argument(
        "--limit", type=int, default=None, help="Stop after N papers processed"
    )
    args = p.parse_args()

    print(f"[batch] force={args.force} limit={args.limit}")
    summary = asyncio.run(run_batch(force=args.force, limit=args.limit))

    print("\n=== batch_ingest summary ===")
    for k, v in summary.items():
        print(f"  {k:>22}  {v}")

    return 0 if summary["errors"] < MAX_ERRORS else 1


if __name__ == "__main__":
    sys.exit(main())
