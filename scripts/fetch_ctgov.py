"""
fetch_ctgov.py — PRC-02 ClinicalTrials.gov v2 REST fetcher.

Pulls new ClinicalTrials.gov records for the Aleksandra facet set via
the v2 REST API (https://clinicaltrials.gov/api/v2/studies). For every
NCT-id not already in evidence_ledger, fetches the full study JSON,
content-hashes it, uploads to R2, and writes one provenance row.

The v2 REST API is free, requires no key, and has no documented rate
limit for our volume (a few-dozen GETs per 6h cron). We still set a
descriptive User-Agent so we play nice.

Usage
-----
    .venv/Scripts/python.exe -m scripts.fetch_ctgov                  # all queries
    .venv/Scripts/python.exe -m scripts.fetch_ctgov --page-size 5    # smaller fan-out
    .venv/Scripts/python.exe -m scripts.fetch_ctgov --queries 1      # first N queries
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

import httpx

from scripts.ledger import (
    compute_hash,
    insert_ledger_row,
    is_known_source,
    load_env,
    upload_artifact,
)

CTGOV_BASE = "https://clinicaltrials.gov/api/v2/studies"
USER_AGENT = "aleksandra_brain/1.0 (+https://github.com/navyforses/ALEKSANDRA_BRAIN_v4)"

# ---------------------------------------------------------------------------
# Query set — PRC-02 Aleksandra facet
# ---------------------------------------------------------------------------
# Each entry is a dict of query params for /api/v2/studies. We only ask
# for recruiting / active / not-yet-recruiting trials — closed/withdrawn
# trials don't help us.
RECRUITING_STATUSES = (
    "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION,NOT_YET_RECRUITING"
)

QUERY_SETS: list[dict[str, str]] = [
    {
        "query.cond": "Hypoxic Ischemic Encephalopathy",
        "filter.overallStatus": RECRUITING_STATUSES,
    },
    {
        "query.cond": "Infantile Spasms",
        "filter.overallStatus": RECRUITING_STATUSES,
    },
    {
        "query.cond": "Cerebral Palsy",
        "query.intr": "stem cell OR cord blood",
        "filter.overallStatus": RECRUITING_STATUSES,
    },
    {
        "query.cond": "Neonatal Encephalopathy",
        "filter.overallStatus": RECRUITING_STATUSES,
    },
    {
        "query.intr": "Vigabatrin",
        "query.cond": "infantile spasms",
        "filter.overallStatus": RECRUITING_STATUSES,
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _query_describe(q: dict[str, str]) -> str:
    """Compact human-readable string for logs + ledger.query column."""
    bits = []
    for k in ("query.cond", "query.intr", "query.term"):
        if k in q:
            bits.append(f"{k.split('.')[1]}={q[k]}")
    return " ; ".join(bits) or json.dumps(q)


def _fetch_page(
    client: httpx.Client, params: dict[str, str], page_size: int
) -> dict[str, Any]:
    full_params = {**params, "pageSize": str(page_size), "format": "json"}
    r = client.get(CTGOV_BASE, params=full_params, timeout=30)
    r.raise_for_status()
    return r.json()


def _study_to_metadata(study: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Extract (nct_id, metadata) from a single CT.gov study JSON node."""
    proto = study.get("protocolSection", {})
    ident = proto.get("identificationModule", {})
    status = proto.get("statusModule", {})
    design = proto.get("designModule", {})
    arms = proto.get("armsInterventionsModule", {})
    elig = proto.get("eligibilityModule", {})
    contacts = proto.get("contactsLocationsModule", {})

    nct_id = ident.get("nctId", "")
    if not nct_id:
        return "", {}

    interventions = [
        i.get("name", "") for i in arms.get("interventions", []) if i.get("name")
    ][:5]
    locations = [
        f"{loc.get('facility', '')} ({loc.get('country', '')})"
        for loc in contacts.get("locations", [])
    ][:3]

    meta: dict[str, Any] = {
        "nct_id": nct_id,
        "title": ident.get("briefTitle", ""),
        "official_title": ident.get("officialTitle", ""),
        "overall_status": status.get("overallStatus", ""),
        "start_date": status.get("startDateStruct", {}).get("date"),
        "completion_date": status.get("completionDateStruct", {}).get("date"),
        "phases": design.get("phases", []),
        "study_type": design.get("studyType", ""),
        "interventions": interventions,
        "min_age": elig.get("minimumAge"),
        "max_age": elig.get("maximumAge"),
        "sex": elig.get("sex"),
        "healthy_volunteers": elig.get("healthyVolunteers"),
        "locations_sample": locations,
        "has_full_text": True,  # full protocol JSON IS the full record
    }
    return nct_id, meta


# ---------------------------------------------------------------------------
# Main fetch loop
# ---------------------------------------------------------------------------
def run(
    queries: list[dict[str, str]] | None = None,
    page_size: int = 10,
    *,
    mode: str = "positive",
) -> dict[str, int]:
    if queries is None:
        queries = QUERY_SETS
    load_env()

    counts = {
        "queries_run": 0,
        "studies_found": 0,
        "new_studies": 0,
        "ledger_inserted": 0,
        "duplicates": 0,
        "errors": 0,
    }

    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        for q in queries:
            counts["queries_run"] += 1
            try:
                page = _fetch_page(client, q, page_size)
            except Exception as e:
                print(f"  [err] CT.gov query failed for {_query_describe(q)!r}: {e}")
                counts["errors"] += 1
                continue
            studies = page.get("studies", [])
            counts["studies_found"] += len(studies)
            new_for_q = 0
            for study in studies:
                nct_id, meta = _study_to_metadata(study)
                if not nct_id:
                    continue
                if is_known_source(nct_id, "ctgov", mode=mode):
                    counts["duplicates"] += 1
                    continue
                try:
                    payload = json.dumps(study, sort_keys=True, indent=2).encode(
                        "utf-8"
                    )
                    h = compute_hash(payload)
                    url = upload_artifact("ctgov", nct_id, payload, "json", mode=mode)
                    ok = insert_ledger_row(
                        source_id=nct_id,
                        source_type="ctgov",
                        retrieval_method="ctgov_v2_rest",
                        content_hash=h,
                        raw_artifact_url=url,
                        mode=mode,
                        query=_query_describe(q),
                        payload_metadata=meta,
                    )
                    if ok:
                        counts["new_studies"] += 1
                        counts["ledger_inserted"] += 1
                        new_for_q += 1
                    else:
                        counts["duplicates"] += 1
                except Exception as e:
                    print(f"  [err] ledger write failed for {nct_id}: {e}")
                    counts["errors"] += 1
            print(
                f"  query: {_query_describe(q)[:48]:<48}"
                f"  found={len(studies):3d}  new={new_for_q}"
            )
            time.sleep(0.5)  # be polite between queries

    return counts


def _print_counts(counts: dict[str, int]) -> None:
    print()
    print("ClinicalTrials.gov fetch summary:")
    for k, v in counts.items():
        print(f"  {k:18} {v}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--page-size", type=int, default=10, help="studies per query (default 10)"
    )
    ap.add_argument(
        "--queries",
        type=int,
        default=0,
        help="Run only the first N query sets (0 = all)",
    )
    ap.add_argument(
        "--mode",
        choices=("positive", "negative"),
        default="positive",
    )
    args = ap.parse_args()

    qs = QUERY_SETS if args.queries == 0 else QUERY_SETS[: args.queries]
    counts = run(queries=qs, page_size=args.page_size, mode=args.mode)
    _print_counts(counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
