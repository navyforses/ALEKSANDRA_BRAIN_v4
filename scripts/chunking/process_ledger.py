"""
process_ledger.py — Phase 2 sub-phase 2A orchestrator.

For every evidence_ledger row:
  1. Skip if paper_chunks already exists for this ledger_id (idempotent).
  2. Download raw_artifact from R2 via the ledger.py boto3 client.
  3. Format-aware extract_text -> plain string.
  4. chunk_text -> list[Chunk]. Skip ledger row if zero chunks.
  5. INSERT one paper_chunks row per chunk (embedding_id NULL initially).
  6. upsert_chunks to Qdrant -> list of Qdrant point ids.
  7. UPDATE paper_chunks SET embedding_id, embedded_at WHERE id IN (...).

Plus populate_papers_from_ledger():
  For each unique (source_id, source_type) in ledger, INSERT a papers row
  if not already present. Maps payload_metadata into title / abstract /
  authors / journal / publication_year / pmid / doi / ct_id / source_url
  / pdf_storage_path.

Usage:
    .venv/Scripts/python.exe -m scripts.chunking.process_ledger
    .venv/Scripts/python.exe -m scripts.chunking.process_ledger --only-papers
    .venv/Scripts/python.exe -m scripts.chunking.process_ledger --limit 5
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone

import httpx

from scripts.chunking.chunker import chunk_text
from scripts.chunking.embedder import ChunkRow, upsert_chunks
from scripts.chunking.extractor import extract_text
from scripts.extraction.translate import build_bilingual
from scripts.ledger import (
    _get_r2_client,
    _supabase_creds,
    _supabase_headers,
    load_env,
)


# ---------------------------------------------------------------------------
# Supabase REST helpers
# ---------------------------------------------------------------------------
def _supabase_get(path: str, params: dict[str, str]) -> list[dict]:
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/{path}",
        params=params,
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=20,
    )
    if r.status_code != 200:
        raise RuntimeError(f"GET {path} HTTP {r.status_code}: {r.text[:200]}")
    return r.json()


def _supabase_post(
    path: str, body: list[dict] | dict, *, prefer: str = "return=representation"
) -> list[dict]:
    url, key = _supabase_creds()
    r = httpx.post(
        f"{url}/rest/v1/{path}",
        json=body,
        headers={**_supabase_headers(key), "Prefer": prefer},
        timeout=30,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"POST {path} HTTP {r.status_code}: {r.text[:300]}")
    return r.json() if r.text else []


def _supabase_patch(path: str, body: dict, params: dict[str, str]) -> None:
    url, key = _supabase_creds()
    r = httpx.patch(
        f"{url}/rest/v1/{path}",
        params=params,
        json=body,
        headers=_supabase_headers(key, prefer="return=minimal"),
        timeout=20,
    )
    if r.status_code not in (200, 204):
        raise RuntimeError(f"PATCH {path} HTTP {r.status_code}: {r.text[:200]}")


# ---------------------------------------------------------------------------
# R2 fetcher
# ---------------------------------------------------------------------------
def _download_artifact(raw_artifact_url: str) -> bytes:
    if not raw_artifact_url.startswith("s3://"):
        raise RuntimeError(f"unexpected raw_artifact_url scheme: {raw_artifact_url!r}")
    bucket, _, key = raw_artifact_url[len("s3://") :].partition("/")
    client = _get_r2_client()
    return client.get_object(Bucket=bucket, Key=key)["Body"].read()


# ---------------------------------------------------------------------------
# Per-ledger-row processing
# ---------------------------------------------------------------------------
def process_one(ledger_row: dict, *, batch_size: int = 50) -> dict:
    """Returns counters for one ledger row."""
    ledger_id = ledger_row["id"]
    source_type = ledger_row["source_type"]
    source_id = ledger_row["source_id"]

    counters = {
        "chunks_inserted": 0,
        "chunks_embedded": 0,
        "skipped_existing": 0,
        "skipped_no_text": 0,
        "embed_error": 0,
    }

    # 1. Idempotency check
    existing = _supabase_get(
        "paper_chunks",
        {"select": "id", "ledger_id": f"eq.{ledger_id}", "limit": "1"},
    )
    if existing:
        counters["skipped_existing"] = 1
        return counters

    # 2. Download R2 artifact
    payload = _download_artifact(ledger_row["raw_artifact_url"])

    # 3. Extract text
    text = extract_text(source_type, payload)
    if not text:
        counters["skipped_no_text"] = 1
        return counters

    # 4. Chunk
    chunks = chunk_text(text)
    if not chunks:
        counters["skipped_no_text"] = 1
        return counters

    # 5. INSERT paper_chunks (embedding_id NULL)
    insert_rows = [
        {
            "ledger_id": ledger_id,
            "source_type": source_type,
            "source_id": source_id,
            "chunk_index": c.chunk_index,
            "raw_text": c.raw_text,
            "char_count": c.char_count,
            "chunk_type": c.chunk_type,
        }
        for c in chunks
    ]
    inserted = _supabase_post("paper_chunks", insert_rows)
    counters["chunks_inserted"] = len(inserted)

    # 6. Embed + Qdrant upsert in batches of `batch_size`.
    # If embed fails (e.g. Qdrant unreachable), the inserts above ALREADY
    # made it into Postgres with embedding_id=NULL. We swallow the embed
    # error so the caller still credits the inserts AND so subsequent
    # ledger rows keep getting processed; the unembedded rows can be
    # rescued later by scripts/chunking/backfill_embeddings.py.
    chunk_rows: list[ChunkRow] = [
        ChunkRow(
            chunk_id=row["id"],
            ledger_id=ledger_id,
            source_type=source_type,
            source_id=source_id,
            raw_text=row["raw_text"],
        )
        for row in inserted
    ]
    embedded_at = datetime.now(timezone.utc).isoformat()
    try:
        for start in range(0, len(chunk_rows), batch_size):
            batch = chunk_rows[start : start + batch_size]
            point_ids = upsert_chunks(batch)
            # 7. PATCH each row's embedding_id (Supabase REST doesn't support bulk
            # updates of differing values in one call without a CTE; one PATCH per row)
            for cr, pid in zip(batch, point_ids):
                _supabase_patch(
                    "paper_chunks",
                    {"embedding_id": pid, "embedded_at": embedded_at},
                    {"id": f"eq.{cr.chunk_id}"},
                )
                counters["chunks_embedded"] += 1
    except Exception as exc:
        counters["embed_error"] = 1
        print(
            f"    [embed-fail] ledger {ledger_id[:8]} ({source_type}/{source_id[:24]}): "
            f"{type(exc).__name__}: {exc} — kept {counters['chunks_inserted']} rows "
            f"with embedding_id=NULL; recover via backfill_embeddings.py"
        )

    return counters


# ---------------------------------------------------------------------------
# Papers populator (ledger -> papers)
# ---------------------------------------------------------------------------
# Phase 0 papers.source CHECK constraint allows:
#   pubmed | biorxiv | medrxiv | scholar | clinical_trials | consensus
#   | manual_upload | scite | web_search | citation_chain
# We translate ledger source_type into one of those values; gap-fill
# rows (crawl4ai/firecrawl) are NOT distinct papers, they're full-text
# supplements to existing pubmed/biorxiv/medrxiv entries, so we skip
# them in the papers populate pass.
_LEDGER_TO_PAPERS_SOURCE = {
    "pubmed": "pubmed",
    "biorxiv": "biorxiv",
    "medrxiv": "medrxiv",
    "ctgov": "clinical_trials",
}


def _ledger_row_identity(
    ledger_row: dict,
) -> tuple[str, str, dict, dict] | None:
    """
    Cheap pre-translation key derivation.

    Returns (papers_source, identifier, meta, ids) when the ledger row is a
    distinct paper, else None. `ids` carries pmid/ct_id/doi/pmc_id so the
    caller can pass it straight into `_build_papers_row` without re-deriving.

    Split out so `populate_papers_from_ledger` can dedup BEFORE invoking
    `build_bilingual()` (which is a paid Anthropic call). Earlier shape
    issued 2× Sonnet 4-6 translate per ledger row regardless of whether
    the paper already existed — see the dedup-after-translate bug fixed
    in 2026-06-02.
    """
    meta = ledger_row.get("payload_metadata") or {}
    title = meta.get("title") or meta.get("official_title")
    if not title:
        return None

    source_type = ledger_row["source_type"]
    papers_source = _LEDGER_TO_PAPERS_SOURCE.get(source_type)
    if papers_source is None:
        return None

    source_id = ledger_row["source_id"]
    pmid = source_id if source_type == "pubmed" else None
    ct_id = source_id if source_type == "ctgov" else None
    doi = (
        meta.get("doi")
        if source_type == "pubmed"
        else source_id
        if source_type in ("biorxiv", "medrxiv")
        else None
    )
    pmc_id = meta.get("pmc_id") if source_type == "pubmed" else None

    identifier = pmid or doi or ct_id
    if not identifier:
        return None

    ids = {"pmid": pmid, "ct_id": ct_id, "doi": doi, "pmc_id": pmc_id}
    return papers_source, identifier, meta, ids


def _build_papers_row(ledger_row: dict) -> dict | None:
    """
    Map a ledger row to a papers INSERT body. Returns None if no title
    OR if source_type doesn't represent a distinct paper (crawl4ai/firecrawl).

    PostgREST batch insert requires every row in the array to have the
    SAME key set, so we always emit the full key list with None for
    columns that don't apply to a given source_type.

    WARNING: this function calls `build_bilingual()` twice (title +
    abstract), each of which issues a paid Anthropic translate call.
    Callers MUST dedup against `_existing_papers_keys()` BEFORE invoking
    this — see `populate_papers_from_ledger` for the canonical pattern.
    """
    identity = _ledger_row_identity(ledger_row)
    if identity is None:
        return None
    papers_source, _identifier, meta, ids = identity
    title = meta.get("title") or meta.get("official_title")

    pmid = ids["pmid"]
    ct_id = ids["ct_id"]
    doi = ids["doi"]
    pmc_id = ids["pmc_id"]

    publication_year: int | None = None
    if meta.get("publication_year"):
        try:
            publication_year = int(str(meta["publication_year"])[:4])
        except (ValueError, TypeError):
            publication_year = None

    return {
        "title": build_bilingual(title),
        "pmid": pmid,
        "ct_id": ct_id,
        "doi": doi,
        "pmc_id": pmc_id,
        "abstract": build_bilingual(
            meta.get("abstract_full") or meta.get("abstract_excerpt")
        ),
        "authors": meta.get("authors"),
        "journal": meta.get("journal"),
        "publication_year": publication_year,
        "source": papers_source,
        "source_url": ledger_row["raw_artifact_url"],
        "pdf_storage_path": ledger_row["raw_artifact_url"],
        "ingested_at": ledger_row.get("ingested_at"),
    }


def _existing_papers_keys() -> set[tuple[str, str]]:
    """Return set of (source, identifier) pairs already in papers."""
    rows = _supabase_get(
        "papers",
        {"select": "source,pmid,doi,ct_id", "limit": "10000"},
    )
    keys: set[tuple[str, str]] = set()
    for r in rows:
        src = r.get("source")
        ident = r.get("pmid") or r.get("doi") or r.get("ct_id")
        if src and ident:
            keys.add((src, ident))
    return keys


def populate_papers_from_ledger() -> dict:
    """INSERT one papers row per unique (source, identifier) in ledger.

    Dedup MUST precede `_build_papers_row()` because the latter invokes
    `build_bilingual()` twice per row — each a paid Anthropic Sonnet 4-6
    call. Earlier ordering issued ~2N wasted translates per tick when N
    ledger rows were already in `papers`; on a 30-min cron that produced
    ~30K wasted calls/day. Fixed 2026-06-02.
    """
    counters = {"inserted": 0, "skipped_existing": 0, "skipped_no_title": 0}

    ledger = _supabase_get(
        "evidence_ledger",
        {"select": "*", "mode": "eq.positive", "limit": "10000"},
    )

    existing = _existing_papers_keys()  # set of (papers.source, identifier)
    seen: set[tuple[str, str]] = set()
    to_insert: list[dict] = []

    for row in ledger:
        identity = _ledger_row_identity(row)
        if identity is None:
            counters["skipped_no_title"] += 1
            continue
        papers_source, identifier, _meta, _ids = identity
        key = (papers_source, identifier)
        if key in existing or key in seen:
            counters["skipped_existing"] += 1
            continue
        # Only NOW invoke build_bilingual (2× Sonnet 4-6 calls per row).
        body = _build_papers_row(row)
        if body is None:  # defensive — identity-pass implies build-pass
            counters["skipped_no_title"] += 1
            continue
        to_insert.append(body)
        seen.add(key)

    if to_insert:
        _supabase_post("papers", to_insert, prefer="return=minimal")
        counters["inserted"] = len(to_insert)

    return counters


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def run(*, limit: int = 0, only_papers: bool = False, score: bool = True) -> dict:
    load_env()

    totals = {
        "ledger_rows_seen": 0,
        "chunks_inserted": 0,
        "chunks_embedded": 0,
        "skipped_existing": 0,
        "skipped_no_text": 0,
        "embed_errors": 0,
        "papers_inserted": 0,
        "papers_skipped_existing": 0,
        "papers_skipped_no_title": 0,
        "relevance_scored": 0,
        "relevance_failed": 0,
        "relevance_skipped_no_text": 0,
        "errors": 0,
    }

    # 1. Papers populate (cheap, independent)
    print("=== populate_papers_from_ledger ===")
    p = populate_papers_from_ledger()
    totals["papers_inserted"] = p["inserted"]
    totals["papers_skipped_existing"] = p["skipped_existing"]
    totals["papers_skipped_no_title"] = p["skipped_no_title"]
    print(
        f"  inserted={p['inserted']}  skipped_existing={p['skipped_existing']}  no_title={p['skipped_no_title']}"
    )

    # 2. Score any papers that still lack a relevance_score (idempotent
    #    backfill). Cheap (~$0.0002/paper Haiku 4.5). OR-2 fallback contract
    #    leaves score=NULL on failure; perception ingest is never blocked.
    if score:
        print("\n=== score relevance (Haiku 4.5) ===")
        # Lazy import keeps `--no-score` runs free of the cognition.llm
        # import chain (which loads anthropic SDK + budget gate).
        from scripts.scoring.relevance import backfill as _score_backfill

        sb = _score_backfill(limit=200)
        totals["relevance_scored"] = sb.get("scored", 0)
        totals["relevance_failed"] = sb.get("failed", 0)
        totals["relevance_skipped_no_text"] = sb.get("skipped_no_text", 0)
        print(
            f"  scored={sb.get('scored', 0)}  failed={sb.get('failed', 0)}  skipped_no_text={sb.get('skipped_no_text', 0)}"
        )

    if only_papers:
        return totals

    # 2. Chunk + embed per ledger row
    print("\n=== chunk + embed evidence_ledger rows ===")
    ledger_rows = _supabase_get(
        "evidence_ledger",
        {
            "select": "id,source_type,source_id,raw_artifact_url,payload_metadata,ingested_at",
            "order": "ingested_at.desc",
            "limit": "10000" if limit == 0 else str(limit),
        },
    )
    totals["ledger_rows_seen"] = len(ledger_rows)

    for i, row in enumerate(ledger_rows, 1):
        try:
            t0 = time.perf_counter()
            c = process_one(row)
            dt = time.perf_counter() - t0
            totals["chunks_inserted"] += c["chunks_inserted"]
            totals["chunks_embedded"] += c["chunks_embedded"]
            totals["skipped_existing"] += c["skipped_existing"]
            totals["skipped_no_text"] += c["skipped_no_text"]
            totals["embed_errors"] += c.get("embed_error", 0)
            tag = (
                "skip-existing"
                if c["skipped_existing"]
                else "skip-empty"
                if c["skipped_no_text"]
                else f"chunks={c['chunks_inserted']} embedded={c['chunks_embedded']}"
                + (" embed-FAIL" if c.get("embed_error") else "")
            )
            print(
                f"  [{i:3d}/{len(ledger_rows)}] {row['source_type']:<10}/{row['source_id'][:24]:<24} {tag:<28} {dt:5.2f}s"
            )
        except Exception as e:
            totals["errors"] += 1
            print(
                f"  [{i:3d}/{len(ledger_rows)}] ERROR {row['source_type']}/{row['source_id'][:24]} :: {type(e).__name__}: {e}"
            )

    return totals


def _print_totals(t: dict) -> None:
    print()
    print("=" * 60)
    print("Chunking pipeline summary")
    for k, v in t.items():
        print(f"  {k:28} {v}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only first N ledger rows (0 = all)",
    )
    ap.add_argument(
        "--only-papers",
        action="store_true",
        help="Populate papers table only; skip chunking pass",
    )
    ap.add_argument(
        "--no-score",
        action="store_true",
        help="Skip the post-populate Haiku 4.5 relevance scoring pass.",
    )
    args = ap.parse_args()
    totals = run(
        limit=args.limit, only_papers=args.only_papers, score=not args.no_score
    )
    _print_totals(totals)
    return 0 if totals["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
