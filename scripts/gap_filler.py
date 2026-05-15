"""
gap_filler.py — PRC-04 + PRC-05 full-text recovery.

Walks evidence_ledger for rows in the last 6 hours where
payload_metadata.has_full_text is false / missing, identifies a
candidate full-text URL (PMC link for pubmed-with-pmc_id, biorxiv.org
link for biorxiv DOIs, etc.) and tries to fetch it with Crawl4AI.

On Crawl4AI failure (network, timeout, empty markdown), the URL's
kv_state crawl_fail counter ticks up. The second failure on the same
URL flips eligibility for Firecrawl, but ONLY if the monthly Firecrawl
spend (kv_state firecrawl_spend:<YYYY-MM>) is below FIRECRAWL_MONTHLY_CAP_USD.

Every successful fetch — Crawl4AI or Firecrawl — writes a NEW ledger
row (not an update). The source_id is the content_hash itself
(content-addressed storage), source_type 'crawl4ai' or 'firecrawl'.
This means the same paper may have two ledger rows: one from PubMed
(abstract only) and one from gap-fill (full text). That's by design —
provenance fan-in is more honest than overwriting metadata.

Usage
-----
    .venv/Scripts/python.exe -m scripts.gap_filler                 # all eligible rows in last 6h
    .venv/Scripts/python.exe -m scripts.gap_filler --hours 24      # widen lookback
    .venv/Scripts/python.exe -m scripts.gap_filler --limit 5       # safety cap
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import Any

import httpx

from scripts.ledger import (
    _supabase_creds,
    _supabase_headers,
    compute_hash,
    get_state,
    insert_ledger_row,
    is_known_source,
    load_env,
    set_state,
    upload_artifact,
)

FIRECRAWL_BASE = "https://api.firecrawl.dev/v1/scrape"
FIRECRAWL_COST_PER_PAGE_USD = (
    0.05  # rough budget tick; Firecrawl Hobby ~7 credits/page ~= $0.05
)


# ---------------------------------------------------------------------------
# Identify candidate URLs from ledger rows
# ---------------------------------------------------------------------------
def _candidate_url(
    source_type: str, source_id: str, meta: dict[str, Any]
) -> str | None:
    """Return a best-guess full-text URL for a row, or None."""
    if source_type == "pubmed":
        pmc = meta.get("pmc_id")
        if pmc:
            pmc_clean = pmc.replace("PMC", "").strip()
            return f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_clean}/"
        doi = meta.get("doi")
        if doi:
            return f"https://doi.org/{doi}"
        return None
    if source_type in ("biorxiv", "medrxiv"):
        link = meta.get("link") or ""
        if link:
            return link
        doi = meta.get("doi")
        if doi:
            host = "biorxiv.org" if source_type == "biorxiv" else "medrxiv.org"
            return f"https://www.{host}/content/{doi}v1.full"
        return None
    return None


# ---------------------------------------------------------------------------
# Fetch ledger rows in the gap-fill window
# ---------------------------------------------------------------------------
def _list_candidates(hours: int) -> list[dict[str, Any]]:
    """Pull ledger rows in [now - hours, now] with no recorded full text."""
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/evidence_ledger",
        params={
            "select": "id,source_id,source_type,payload_metadata,retrieval_timestamp",
            "mode": "eq.positive",
            "source_type": "in.(pubmed,biorxiv,medrxiv)",
            "retrieval_timestamp": f"gte.{_isoformat_lookback(hours)}",
            "order": "retrieval_timestamp.desc",
            "limit": "200",
        },
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=15,
    )
    if r.status_code != 200:
        raise RuntimeError(
            f"_list_candidates failed: HTTP {r.status_code}: {r.text[:200]}"
        )
    rows: list[dict[str, Any]] = r.json()
    out = []
    for row in rows:
        meta = row.get("payload_metadata") or {}
        if meta.get("has_full_text") is True:
            continue
        out.append(row)
    return out


def _isoformat_lookback(hours: int) -> str:
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return cutoff.isoformat()


# ---------------------------------------------------------------------------
# Firecrawl fallback (PRC-05 budget-gated)
# ---------------------------------------------------------------------------
def _firecrawl_spend_key() -> str:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"firecrawl_spend:{month}"


def _firecrawl_cap_usd() -> float:
    load_env()
    raw = os.environ.get("FIRECRAWL_MONTHLY_CAP_USD", "10")
    try:
        return float(raw)
    except ValueError:
        return 10.0


def _firecrawl_under_cap() -> tuple[bool, float]:
    """Return (under_cap, current_spend_usd)."""
    state = get_state(_firecrawl_spend_key()) or {"usd": 0.0, "calls": 0}
    spend = float(state.get("usd", 0.0))
    return spend < _firecrawl_cap_usd(), spend


def _firecrawl_record_spend(usd: float) -> None:
    key = _firecrawl_spend_key()
    state = get_state(key) or {"usd": 0.0, "calls": 0}
    state["usd"] = float(state.get("usd", 0.0)) + usd
    state["calls"] = int(state.get("calls", 0)) + 1
    state["last_at"] = datetime.now(timezone.utc).isoformat()
    set_state(key, state)


def _firecrawl_fetch(url: str) -> tuple[bool, bytes | None, str | None]:
    load_env()
    api_key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    if not api_key:
        return False, None, "FIRECRAWL_API_KEY not set"
    try:
        r = httpx.post(
            FIRECRAWL_BASE,
            json={"url": url, "formats": ["markdown"]},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60,
        )
        if r.status_code != 200:
            return False, None, f"HTTP {r.status_code}: {r.text[:200]}"
        data = r.json()
        md = data.get("data", {}).get("markdown") or data.get("markdown") or ""
        if not md.strip():
            return False, None, "empty markdown"
        return True, md.encode("utf-8"), None
    except Exception as e:
        return False, None, f"{type(e).__name__}: {e}"


# ---------------------------------------------------------------------------
# Fail counter
# ---------------------------------------------------------------------------
def _fail_key(url: str) -> str:
    # Hash the URL into the key so we don't blow Supabase TEXT key limits.
    import hashlib as _h

    return f"crawl_fail:{_h.sha256(url.encode()).hexdigest()[:16]}"


def _bump_fail(url: str) -> int:
    key = _fail_key(url)
    state = get_state(key) or {"count": 0, "url": url}
    state["count"] = int(state.get("count", 0)) + 1
    state["last_at"] = datetime.now(timezone.utc).isoformat()
    set_state(key, state)
    return state["count"]


def _fail_count(url: str) -> int:
    state = get_state(_fail_key(url))
    return int(state.get("count", 0)) if state else 0


# ---------------------------------------------------------------------------
# Main fill loop (single asyncio context to avoid Windows event-loop cleanup bugs)
# ---------------------------------------------------------------------------
async def _process_candidates(
    candidates: list[dict[str, Any]],
    counts: dict[str, int],
    *,
    allow_firecrawl: bool,
) -> None:
    try:
        from crawl4ai import AsyncWebCrawler  # type: ignore
    except ImportError:
        AsyncWebCrawler = None  # type: ignore

    crawler = None
    if AsyncWebCrawler is not None:
        crawler = AsyncWebCrawler(verbose=False)
        await crawler.__aenter__()

    try:
        for row in candidates:
            source_type = row["source_type"]
            source_id = row["source_id"]
            meta = row.get("payload_metadata") or {}
            url = _candidate_url(source_type, source_id, meta)
            if not url:
                counts["no_url"] += 1
                continue

            # Crawl4AI first
            success = False
            payload: bytes | None = None
            err: str | None = None
            method = "crawl4ai"
            if crawler is None:
                err = "crawl4ai not importable"
            else:
                try:
                    result = await crawler.arun(url=url, bypass_cache=False)
                    md = getattr(result, "markdown", None) or ""
                    md_text = (
                        md
                        if isinstance(md, str)
                        else (getattr(md, "raw_markdown", "") or str(md))
                    )
                    if md_text.strip():
                        success = True
                        payload = md_text.encode("utf-8")
                    else:
                        err = "empty markdown"
                except Exception as e:
                    err = f"{type(e).__name__}: {e}"

            if not success:
                fail_n = _bump_fail(url)
                counts["crawl4ai_fail"] += 1
                print(
                    f"  [c4ai fail #{fail_n}] {source_type}/{source_id} "
                    f"url={url[:60]} :: {err}"
                )
                if allow_firecrawl and fail_n >= 2:
                    under, spent = _firecrawl_under_cap()
                    if not under:
                        counts["firecrawl_skipped_cap"] += 1
                        print(f"  [fc skip] cap reached: ${spent:.2f}")
                        continue
                    if not os.environ.get("FIRECRAWL_API_KEY", "").strip():
                        counts["firecrawl_skipped_no_key"] += 1
                        print("  [fc skip] no API key")
                        continue
                    f_ok, f_payload, f_err = _firecrawl_fetch(url)
                    if f_ok:
                        success = True
                        payload = f_payload
                        method = "firecrawl"
                        _firecrawl_record_spend(FIRECRAWL_COST_PER_PAGE_USD)
                        counts["firecrawl_success"] += 1
                    else:
                        counts["firecrawl_fail"] += 1
                        print(f"  [fc fail] {url[:60]} :: {f_err}")
                        continue
                else:
                    continue
            else:
                counts["crawl4ai_success"] += 1

            assert payload is not None
            h = compute_hash(payload)
            new_source_id = h[:24]
            if is_known_source(new_source_id, method):
                counts["duplicates"] += 1
                continue
            artifact_url = upload_artifact(method, new_source_id, payload, "md")
            ok = insert_ledger_row(
                source_id=new_source_id,
                source_type=method,
                retrieval_method=method,
                content_hash=h,
                raw_artifact_url=artifact_url,
                query=f"gap-fill of {source_type}/{source_id}",
                payload_metadata={
                    "filled_from_ledger_id": row.get("id"),
                    "filled_from_source_type": source_type,
                    "filled_from_source_id": source_id,
                    "url": url,
                    "bytes": len(payload),
                    "has_full_text": True,
                },
            )
            if ok:
                counts["ledger_inserted"] += 1
                print(f"  [ok {method}] {source_type}/{source_id} -> {artifact_url}")
            else:
                counts["duplicates"] += 1
    finally:
        if crawler is not None:
            try:
                await crawler.__aexit__(None, None, None)
            except Exception:
                pass


def run(
    hours: int = 6,
    limit: int = 50,
    *,
    allow_firecrawl: bool = True,
) -> dict[str, int]:
    load_env()
    candidates = _list_candidates(hours)[:limit]
    counts = {
        "candidates": len(candidates),
        "no_url": 0,
        "crawl4ai_success": 0,
        "crawl4ai_fail": 0,
        "firecrawl_success": 0,
        "firecrawl_skipped_cap": 0,
        "firecrawl_skipped_no_key": 0,
        "firecrawl_fail": 0,
        "ledger_inserted": 0,
        "duplicates": 0,
    }
    # Windows: prefer ProactorEventLoop (default in 3.12); ensure we run a single
    # asyncio context so subprocess pipes for Playwright/Chrome close cleanly.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(
        _process_candidates(candidates, counts, allow_firecrawl=allow_firecrawl)
    )
    return counts


def _print_counts(counts: dict[str, int]) -> None:
    print()
    print("Gap-filler summary:")
    for k, v in counts.items():
        print(f"  {k:24} {v}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=6)
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument(
        "--no-firecrawl",
        action="store_true",
        help="Skip Firecrawl fallback (testing only)",
    )
    args = ap.parse_args()
    counts = run(
        hours=args.hours, limit=args.limit, allow_firecrawl=not args.no_firecrawl
    )
    _print_counts(counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
