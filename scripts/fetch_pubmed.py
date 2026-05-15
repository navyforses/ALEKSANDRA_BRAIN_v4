"""
fetch_pubmed.py — PRC-01 PubMed E-utilities fetcher.

Pulls new PubMed records via NCBI E-utilities for the Aleksandra facet
set (10 direct + 10 cross-disease queries). For every PMID not already
in evidence_ledger, fetches the raw XML, content-hashes it, uploads it
to R2, and writes one provenance row to evidence_ledger.

NCBI compliance (PRC-01 wording):
  - api_key  — registered key, 10 req/sec allowance
  - mailto   — NCBI_EMAIL header
  - tool     — "aleksandra_brain" identifying user-agent

If NCBI_API_KEY is unset, the script falls back to anonymous use
(3 req/sec) with a printed warning — PRC-01 still wants the key, this
is just so the script can do useful work locally before the key arrives.

Usage
-----
    .venv/Scripts/python.exe -m scripts.fetch_pubmed                 # all queries
    .venv/Scripts/python.exe -m scripts.fetch_pubmed --retmax 5      # smaller fan-out
    .venv/Scripts/python.exe -m scripts.fetch_pubmed --queries 2     # first N queries
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any
from xml.etree import ElementTree as ET

from Bio import Entrez

from scripts.ledger import (
    compute_hash,
    insert_ledger_row,
    is_known_source,
    load_env,
    upload_artifact,
)

# ---------------------------------------------------------------------------
# Query set — PRC-01 Aleksandra facet
# ---------------------------------------------------------------------------
DIRECT_QUERIES: list[str] = [
    "hypoxic ischemic encephalopathy treatment",
    "neonatal brain injury therapy",
    "infantile spasms novel treatment",
    "cystic encephalomalacia outcome",
    "cortical visual impairment intervention",
    "neonatal seizure management",
    "perinatal asphyxia neuroprotection",
    "therapeutic hypothermia adjunct",
    "cord blood brain injury pediatric",
    "cerebral palsy prevention early intervention",
]

CROSS_DISEASE_QUERIES: list[str] = [
    "AMPK neuroprotection brain",
    "oligodendrocyte precursor remyelination",
    "microglial modulation pediatric",
    "blood brain barrier repair neonatal",
    "exosome therapy brain injury",
    "focused ultrasound neuromodulation pediatric",
    "erythropoietin neuroprotection neonatal",
    "melatonin hypoxia neuroprotection",
    "lithium neuroprotection brain",
    "NAC oxidative stress neonatal brain",
]

ALL_QUERIES: list[str] = DIRECT_QUERIES + CROSS_DISEASE_QUERIES


# ---------------------------------------------------------------------------
# NCBI compliance setup
# ---------------------------------------------------------------------------
def configure_entrez() -> bool:
    """Wire Entrez globals from .env. Returns True if api_key was set."""
    import os

    load_env()
    email = os.environ.get("NCBI_EMAIL", "").strip()
    api_key = os.environ.get("NCBI_API_KEY", "").strip()
    tool = os.environ.get("NCBI_TOOL", "aleksandra_brain").strip()

    if not email or "@example.com" in email:
        raise RuntimeError(
            "NCBI_EMAIL must be set in .env to a real mailto for PRC-01 compliance."
        )

    Entrez.email = email
    Entrez.tool = tool
    if api_key:
        Entrez.api_key = api_key
        return True
    print(
        "[warn] NCBI_API_KEY not set — falling back to 3 req/sec anonymous rate.\n"
        "       PRC-01 requires a registered key; register at "
        "https://www.ncbi.nlm.nih.gov/account/settings/"
    )
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _esearch_pmids(query: str, retmax: int) -> list[str]:
    handle = Entrez.esearch(db="pubmed", term=query, retmax=retmax, sort="date")
    record = Entrez.read(handle)
    handle.close()
    return list(record.get("IdList", []))


def _efetch_xml(pmid: str) -> bytes:
    handle = Entrez.efetch(db="pubmed", id=pmid, rettype="xml", retmode="xml")
    xml = handle.read()
    handle.close()
    return xml if isinstance(xml, bytes) else xml.encode("utf-8")


def _xml_to_metadata(xml: bytes, pmid: str) -> dict[str, Any]:
    """
    Minimal best-effort metadata extraction. We're NOT doing analysis here —
    just enough to make the ledger row useful in a list view: title, authors
    (first 3), journal, year, doi (if any), and a 300-char abstract excerpt.
    """
    meta: dict[str, Any] = {"pmid": pmid, "has_full_text": False}
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return meta

    article = root.find(".//PubmedArticle/MedlineCitation/Article")
    if article is None:
        return meta

    t = article.findtext("ArticleTitle")
    if t:
        meta["title"] = t.strip()

    journal = article.findtext("Journal/Title")
    if journal:
        meta["journal"] = journal.strip()

    year = article.findtext("Journal/JournalIssue/PubDate/Year") or article.findtext(
        "Journal/JournalIssue/PubDate/MedlineDate"
    )
    if year:
        meta["publication_year"] = year.strip()

    authors: list[str] = []
    for au in article.findall(".//AuthorList/Author")[:3]:
        last = au.findtext("LastName") or ""
        init = au.findtext("Initials") or ""
        name = f"{last} {init}".strip()
        if name:
            authors.append(name)
    if authors:
        meta["authors"] = authors

    abstract_parts: list[str] = []
    for ab in article.findall(".//Abstract/AbstractText"):
        if ab.text:
            abstract_parts.append(ab.text.strip())
    if abstract_parts:
        full_abstract = " ".join(abstract_parts)
        meta["abstract_excerpt"] = full_abstract[:300]
        meta["abstract_chars"] = len(full_abstract)

    # DOI is in ArticleIdList
    for aid in root.findall(".//PubmedData/ArticleIdList/ArticleId"):
        if aid.get("IdType") == "doi" and aid.text:
            meta["doi"] = aid.text.strip()
        if aid.get("IdType") == "pmc" and aid.text:
            meta["pmc_id"] = aid.text.strip()
            meta["has_full_text"] = True  # PMC = free full text

    return meta


# ---------------------------------------------------------------------------
# Main fetch loop
# ---------------------------------------------------------------------------
def run(
    queries: list[str] | None = None,
    retmax: int = 10,
    rate_delay: float | None = None,
    *,
    mode: str = "positive",
) -> dict[str, int]:
    """
    Run the PubMed fetch pass. Returns a dict of counters.

    rate_delay: seconds between efetch calls. None → auto (0.11s with api_key,
    0.34s without — both with a safety margin).
    """
    if queries is None:
        queries = ALL_QUERIES

    has_key = configure_entrez()
    if rate_delay is None:
        rate_delay = 0.11 if has_key else 0.34

    counts = {
        "queries_run": 0,
        "pmids_found": 0,
        "new_pmids": 0,
        "ledger_inserted": 0,
        "duplicates": 0,
        "errors": 0,
    }

    for q in queries:
        counts["queries_run"] += 1
        try:
            pmids = _esearch_pmids(q, retmax=retmax)
        except Exception as e:
            print(f"  [err] esearch failed for {q!r}: {e}")
            counts["errors"] += 1
            continue
        counts["pmids_found"] += len(pmids)
        new_for_q = 0
        for pmid in pmids:
            if is_known_source(pmid, "pubmed", mode=mode):
                counts["duplicates"] += 1
                continue
            try:
                xml = _efetch_xml(pmid)
                h = compute_hash(xml)
                url = upload_artifact("pubmed", pmid, xml, "xml", mode=mode)
                meta = _xml_to_metadata(xml, pmid)
                ok = insert_ledger_row(
                    source_id=pmid,
                    source_type="pubmed",
                    retrieval_method="eutils",
                    content_hash=h,
                    raw_artifact_url=url,
                    mode=mode,
                    query=q,
                    payload_metadata=meta,
                )
                if ok:
                    counts["new_pmids"] += 1
                    counts["ledger_inserted"] += 1
                    new_for_q += 1
                else:
                    counts["duplicates"] += 1
                time.sleep(rate_delay)
            except Exception as e:
                print(f"  [err] efetch/ledger failed for PMID {pmid}: {e}")
                counts["errors"] += 1
        print(f"  query: {q[:48]:<48} found={len(pmids):3d} new={new_for_q}")

    return counts


def _print_counts(counts: dict[str, int]) -> None:
    print()
    print("PubMed fetch summary:")
    for k, v in counts.items():
        print(f"  {k:18} {v}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--retmax", type=int, default=10, help="PMIDs per query (default 10)"
    )
    ap.add_argument(
        "--queries",
        type=int,
        default=0,
        help="Run only the first N queries (0 = all 20)",
    )
    ap.add_argument(
        "--mode",
        choices=("positive", "negative"),
        default="positive",
        help="Ledger branch (default: positive)",
    )
    args = ap.parse_args()

    qs = ALL_QUERIES if args.queries == 0 else ALL_QUERIES[: args.queries]
    counts = run(queries=qs, retmax=args.retmax, mode=args.mode)
    _print_counts(counts)
    return 0 if counts["ledger_inserted"] >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
