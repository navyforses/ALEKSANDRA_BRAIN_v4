"""
fetch_preprints.py — PRC-03 bioRxiv + medRxiv RSS fetcher.

Pulls new preprints via RSS for the Aleksandra facet set. Two feed
families:
  - bioRxiv neuroscience subject feed
  - medRxiv pediatrics subject feed
  (with one HIE-targeted bioRxiv search feed as a third pass)

For each entry, dedup on DOI -> serialize entry as JSON bytes -> hash
-> R2 upload as biorxiv/<doi_safe>.json (or medrxiv/) -> insert one
provenance row.

The RSS endpoints are free, anonymous, and cacheable. Tested against
the connect.biorxiv.org subject feeds (bioRxiv) and the same for
medRxiv. If a feed times out or 404s, that source is skipped — the
other ones still run.

Usage
-----
    .venv/Scripts/python.exe -m scripts.fetch_preprints              # all feeds
    .venv/Scripts/python.exe -m scripts.fetch_preprints --max 5      # at most 5 entries per feed
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from typing import Any

import feedparser

from scripts.ledger import (
    compute_hash,
    insert_ledger_row,
    known_sources,
    load_env,
    upload_artifact,
)

USER_AGENT = "aleksandra_brain/1.0 (+https://github.com/navyforses/ALEKSANDRA_BRAIN_v4)"

# ---------------------------------------------------------------------------
# Feed set — PRC-03 Aleksandra facet
# ---------------------------------------------------------------------------
# Each entry: (source_type, label, url)
FEEDS: list[tuple[str, str, str]] = [
    (
        "biorxiv",
        "bioRxiv neuroscience subject feed",
        "https://connect.biorxiv.org/biorxiv_xml.php?subject=neuroscience",
    ),
    (
        "medrxiv",
        "medRxiv Pediatrics subject feed",
        # medRxiv subject names are case-sensitive — capital P matters.
        "https://connect.medrxiv.org/medrxiv_xml.php?subject=Pediatrics",
    ),
]

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)


def _extract_doi(entry: dict[str, Any]) -> str | None:
    """Pull a DOI out of a feedparser entry. Look at dc:identifier, link, id, summary."""
    # 1. id often looks like 'doi:10.1101/...' or 'https://www.biorxiv.org/.../doi'
    for field in ("id", "link"):
        v = entry.get(field, "") or ""
        m = DOI_RE.search(v)
        if m:
            return m.group(0).rstrip(".").rstrip(")").rstrip("/")
    # 2. dc:identifier (some feeds carry it as 'identifier')
    for key in ("dc_identifier", "identifier", "prism_doi"):
        v = entry.get(key, "") or ""
        if isinstance(v, str):
            m = DOI_RE.search(v)
            if m:
                return m.group(0).rstrip(".").rstrip(")").rstrip("/")
    # 3. summary HTML often has a DOI line
    v = entry.get("summary", "") or ""
    m = DOI_RE.search(v)
    if m:
        return m.group(0).rstrip(".").rstrip(")").rstrip("/")
    return None


def _entry_to_metadata(entry: dict[str, Any], doi: str) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "doi": doi,
        "title": entry.get("title", "").strip(),
        "link": entry.get("link", ""),
        "published": entry.get("published")
        or entry.get("updated")
        or entry.get("date"),
        "has_full_text": False,  # preprints land as PDF/HTML on biorxiv.org; full text reachable via gap_filler
    }
    authors_raw = entry.get("authors") or []
    if isinstance(authors_raw, list):
        names = []
        for a in authors_raw[:5]:
            if isinstance(a, dict):
                name = a.get("name") or a.get("nameOfPerson")
                if name:
                    names.append(name)
            elif isinstance(a, str):
                names.append(a)
        if names:
            meta["authors"] = names
    summary = entry.get("summary") or entry.get("description") or ""
    if summary:
        # Strip HTML tags coarsely; we just need an excerpt.
        plain = re.sub(r"<[^>]+>", " ", summary)
        plain = re.sub(r"\s+", " ", plain).strip()
        if plain:
            meta["abstract_full"] = (
                plain  # full text → papers.abstract (process_ledger)
            )
            meta["abstract_excerpt"] = plain[:300]  # kept for list-view previews
            meta["abstract_chars"] = len(plain)
    return meta


def _entry_payload(entry: dict[str, Any]) -> bytes:
    """Stable JSON representation for hashing. Drops mutable feedparser internals."""
    # feedparser uses FeedParserDict which is sometimes not JSON-clean —
    # cast through json.dumps with default=str so dates etc become strings.
    return json.dumps(
        {k: v for k, v in entry.items() if not k.startswith("_")},
        sort_keys=True,
        indent=2,
        default=str,
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Main fetch loop
# ---------------------------------------------------------------------------
def run(max_per_feed: int = 10, *, mode: str = "positive") -> dict[str, int]:
    load_env()

    counts = {
        "feeds_run": 0,
        "entries_seen": 0,
        "no_doi": 0,
        "new_entries": 0,
        "ledger_inserted": 0,
        "duplicates": 0,
        "errors": 0,
    }

    for source_type, label, url in FEEDS:
        counts["feeds_run"] += 1
        print(f"  feed: {label}")
        try:
            # feedparser doesn't accept a UA directly; pass as request_headers
            feed = feedparser.parse(url, request_headers={"User-Agent": USER_AGENT})
        except Exception as e:
            print(f"    [err] feed fetch failed: {e}")
            counts["errors"] += 1
            continue
        if feed.bozo and not feed.entries:
            print(f"    [err] feedparser bozo with 0 entries: {feed.bozo_exception}")
            counts["errors"] += 1
            continue

        entries = feed.entries[:max_per_feed]
        # P-4: one batch dedup query per feed (fail-open) instead of one GET per
        # entry. _extract_doi is pure parsing, so re-deriving the list is cheap.
        already = known_sources(
            [d for d in (_extract_doi(e) for e in entries) if d],
            source_type,
            mode=mode,
        )
        new_for_feed = 0
        for entry in entries:
            counts["entries_seen"] += 1
            doi = _extract_doi(entry)
            if not doi:
                counts["no_doi"] += 1
                continue
            if doi in already:
                counts["duplicates"] += 1
                continue
            try:
                payload = _entry_payload(entry)
                h = compute_hash(payload)
                url_artifact = upload_artifact(
                    source_type, doi, payload, "json", mode=mode
                )
                meta = _entry_to_metadata(entry, doi)
                ok = insert_ledger_row(
                    source_id=doi,
                    source_type=source_type,
                    retrieval_method="rss",
                    content_hash=h,
                    raw_artifact_url=url_artifact,
                    mode=mode,
                    query=label,
                    payload_metadata=meta,
                )
                if ok:
                    counts["new_entries"] += 1
                    counts["ledger_inserted"] += 1
                    new_for_feed += 1
                else:
                    counts["duplicates"] += 1
            except Exception as e:
                print(f"    [err] ledger write failed for DOI {doi}: {e}")
                counts["errors"] += 1
        print(f"    entries={len(entries):3d}  new={new_for_feed}")
        time.sleep(0.5)

    return counts


def _print_counts(counts: dict[str, int]) -> None:
    print()
    print("Preprint fetch summary:")
    for k, v in counts.items():
        print(f"  {k:18} {v}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=10, help="max entries per feed")
    ap.add_argument(
        "--mode",
        choices=("positive", "negative"),
        default="positive",
    )
    args = ap.parse_args()
    counts = run(max_per_feed=args.max, mode=args.mode)
    _print_counts(counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
