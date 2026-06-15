"""
eligibility_matcher.py — Phase A wave 1: ctgov → clinical_trials sync + matcher.

Reads every ClinicalTrials.gov row already captured in evidence_ledger
(source_type='ctgov', payload_metadata JSONB) and maps each into a
clinical_trials record with a *computed eligibility decision* for
Aleksandra. The result is UPSERTed into clinical_trials (idempotent on
nct_id) so re-running never duplicates.

Core Value alignment ("never miss a lead"): the decision is deliberately
conservative. A trial is only hidden (`ineligible`) on a CLEAR
disqualifier — closed status, or an age range Aleksandra clearly falls
outside of. Any ambiguity (unparseable age criteria) routes to
`evaluating` (needs-review), never silent removal. Location is purely
informational (D2) and never disqualifies on its own.

Usage
-----
    .venv/Scripts/python.exe -m scripts.trials.eligibility_matcher --self-test
    .venv/Scripts/python.exe -m scripts.trials.eligibility_matcher --dry-run
    .venv/Scripts/python.exe -m scripts.trials.eligibility_matcher --limit 10
    .venv/Scripts/python.exe -m scripts.trials.eligibility_matcher          # live seed
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from datetime import date, datetime, timezone
from typing import Any

import httpx

from scripts.ledger import _supabase_creds, _supabase_headers, load_env

# ---------------------------------------------------------------------------
# Patient constants — Aleksandra
# ---------------------------------------------------------------------------
DOB = date(2025, 8, 28)  # 2025-08-28
DAYS_PER_MONTH = 30.4375  # mean Gregorian month (365.25 / 12)

# Recruiting-ish statuses considered "open" for enrollment purposes.
OPEN_STATUSES = {
    "RECRUITING",
    "NOT_YET_RECRUITING",
    "ENROLLING_BY_INVITATION",
    "ACTIVE_NOT_RECRUITING",
}

# Country tokens that count as a US site.
US_COUNTRY_TOKENS = {"united states", "usa", "u.s.", "u.s.a."}


# ---------------------------------------------------------------------------
# Age parsing
# ---------------------------------------------------------------------------
def parse_age_to_months(s: str | None) -> float | None:
    """Parse a ClinicalTrials.gov age string to months.

    Handles "N Years/Year", "N Months/Month", "N Weeks/Week",
    "N Days/Day" (case-insensitive). Empty / "N/A" / None → None (unknown).

      years  → n * 12
      months → n
      weeks  → n * 7 / 30.4375
      days   → n / 30.4375
    """
    if s is None:
        return None
    text = s.strip()
    if not text or text.upper() in {"N/A", "NA", "NONE"}:
        return None

    m = re.search(r"(\d+(?:\.\d+)?)\s*(year|month|week|day)s?", text, re.IGNORECASE)
    if not m:
        return None
    n = float(m.group(1))
    unit = m.group(2).lower()
    if unit == "year":
        return n * 12.0
    if unit == "month":
        return n
    if unit == "week":
        return n * 7.0 / DAYS_PER_MONTH
    if unit == "day":
        return n / DAYS_PER_MONTH
    return None


def aleksandra_age_months(today: date | None = None) -> int:
    """Aleksandra's age in whole months as of `today` (default: now, UTC)."""
    if today is None:
        today = datetime.now(timezone.utc).date()
    days = (today - DOB).days
    return int(days / DAYS_PER_MONTH)


# ---------------------------------------------------------------------------
# Location flags
# ---------------------------------------------------------------------------
def _country_of(location: str) -> str:
    """Best-effort country extraction from a "Facility, Country" / "Facility (Country)"
    sample string. Returns the trailing token, lowercased and stripped."""
    if not location:
        return ""
    # fetch_ctgov writes "facility (country)"; older rows may use "facility, country".
    paren = re.search(r"\(([^)]*)\)\s*$", location)
    if paren:
        return paren.group(1).strip().lower()
    if "," in location:
        return location.rsplit(",", 1)[-1].strip().lower()
    return location.strip().lower()


def location_flags(locations_sample: list[str] | None) -> tuple[bool, bool]:
    """Return (is_us, is_international) from a locations_sample array.

    is_us: any sampled site is in the United States.
    is_international: any sampled site is in a country other than the US.
    """
    is_us = False
    is_international = False
    for loc in locations_sample or []:
        country = _country_of(str(loc))
        if not country:
            continue
        if country in US_COUNTRY_TOKENS:
            is_us = True
        else:
            is_international = True
    return is_us, is_international


# ---------------------------------------------------------------------------
# Mapping + eligibility decision
# ---------------------------------------------------------------------------
def _join_list(value: Any, limit: int | None = None) -> str | None:
    """Join a list into a comma string; pass through plain strings; None → None."""
    if value is None:
        return None
    if isinstance(value, list):
        items = [str(v) for v in value if v]
        if limit is not None:
            items = items[:limit]
        return ", ".join(items) if items else None
    text = str(value).strip()
    return text or None


def map_and_evaluate(
    source_id: str,
    payload: dict[str, Any],
    age_months: int,
    now_iso: str,
) -> dict[str, Any]:
    """Map one evidence_ledger ctgov payload → a clinical_trials record dict
    with a computed eligibility decision."""
    payload = payload or {}

    nct_id = (payload.get("nct_id") or source_id or "").strip()
    title = (
        payload.get("title")
        or payload.get("official_title")
        or nct_id
        or "(untitled trial)"
    )
    brief_summary = payload.get("official_title") or None
    overall_status = payload.get("overall_status") or None

    phase = _join_list(payload.get("phases"))
    study_type = _join_list(payload.get("study_type"))
    intervention_name = _join_list(payload.get("interventions"), limit=5)

    min_age = payload.get("min_age")
    max_age = payload.get("max_age")
    sex = payload.get("sex")
    hv = payload.get("healthy_volunteers")
    eligibility_criteria = (
        f"Age {min_age or '?'}-{max_age or '?'}; sex={sex or '?'}; "
        f"healthy_volunteers={hv if hv is not None else '?'}"
    )

    locations_sample = payload.get("locations_sample") or []
    if not isinstance(locations_sample, list):
        locations_sample = [locations_sample]

    # --- eligibility computation ---
    status_norm = (overall_status or "").strip().upper()
    status_ok = status_norm in OPEN_STATUSES

    min_m = parse_age_to_months(min_age if isinstance(min_age, str) else None)
    max_m = parse_age_to_months(max_age if isinstance(max_age, str) else None)
    lower = min_m if min_m is not None else 0.0
    upper = max_m if max_m is not None else math.inf
    age_clearly_out = (min_m is not None and age_months < lower) or (
        max_m is not None and age_months > upper
    )
    age_unknown = min_m is None and max_m is None

    is_us, is_international = location_flags(locations_sample)

    issues: list[str] = []

    if not status_ok:
        status = "ineligible"
        issues.append(f"not actively recruiting (status={overall_status or 'unknown'})")
    elif age_clearly_out:
        status = "ineligible"
        issues.append(
            f"age out of range (Aleksandra ~{age_months}mo vs "
            f"{min_age or '?'}-{max_age or '?'})"
        )
    elif age_unknown:
        status = "evaluating"
        issues.append("age criteria could not be parsed — needs review")
    else:
        status = "identified"

    # Location is informational only (D2): never flips the decision, but is
    # recorded so the family/clinician sees travel implications.
    if is_international and not is_us:
        issues.append("international site only (no US location in sample)")
    elif not is_us and not is_international:
        issues.append("no location data available")

    aleksandra_eligible = status == "identified"

    return {
        "nct_id": nct_id,
        "title": title,
        "brief_summary": brief_summary,
        "overall_status": overall_status,
        "phase": phase,
        "study_type": study_type,
        "intervention_name": intervention_name,
        "min_age": str(min_age) if min_age is not None else None,
        "max_age": str(max_age) if max_age is not None else None,
        "eligibility_criteria": eligibility_criteria,
        "locations": locations_sample,
        "aleksandra_eligible": aleksandra_eligible,
        "eligibility_issues": issues,
        "aleksandra_status": status,
        "last_checked": now_iso,
        # carry derived flags for the summary printer (NOT a DB column)
        "_is_us": is_us,
        "_is_international": is_international,
    }


# ---------------------------------------------------------------------------
# Supabase I/O
# ---------------------------------------------------------------------------
def fetch_ctgov_rows(limit: int = 1000) -> list[dict[str, Any]]:
    """Read all evidence_ledger ctgov rows (source_id + payload_metadata)."""
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/evidence_ledger",
        params={
            "source_type": "eq.ctgov",
            "select": "source_id,payload_metadata",
            "limit": str(limit),
        },
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(
            f"fetch_ctgov_rows failed: HTTP {r.status_code}: {r.text[:300]}"
        )
    return r.json()


def upsert_trials(records: list[dict[str, Any]]) -> int:
    """Batch UPSERT records into clinical_trials on conflict nct_id.

    Strips the internal underscore-prefixed helper keys before writing.
    Returns the number of rows the server echoed back.
    """
    if not records:
        return 0
    url, key = _supabase_creds()
    clean = [{k: v for k, v in rec.items() if not k.startswith("_")} for rec in records]
    r = httpx.post(
        f"{url}/rest/v1/clinical_trials",
        params={"on_conflict": "nct_id"},
        json=clean,
        headers=_supabase_headers(
            key, prefer="resolution=merge-duplicates,return=representation"
        ),
        timeout=60,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(
            f"upsert_trials failed: HTTP {r.status_code}: {r.text[:500]}"
        )
    try:
        return len(r.json())
    except ValueError:
        return len(clean)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_status = {"identified": 0, "evaluating": 0, "ineligible": 0}
    id_us = 0
    id_intl = 0
    for rec in records:
        st = rec["aleksandra_status"]
        by_status[st] = by_status.get(st, 0) + 1
        if st == "identified":
            if rec.get("_is_us"):
                id_us += 1
            elif rec.get("_is_international"):
                id_intl += 1
    return {
        "total": len(records),
        "by_status": by_status,
        "identified_us": id_us,
        "identified_intl": id_intl,
    }


def _print_summary(summary: dict[str, Any], *, dry_run: bool, written: int) -> None:
    bs = summary["by_status"]
    print()
    print("Clinical-trial eligibility summary:")
    print(f"  mode               {'DRY-RUN (no write)' if dry_run else 'LIVE upsert'}")
    print(f"  total processed    {summary['total']}")
    print(f"  identified         {bs.get('identified', 0)}")
    print(f"  evaluating         {bs.get('evaluating', 0)}")
    print(f"  ineligible         {bs.get('ineligible', 0)}")
    print(f"  identified · US    {summary['identified_us']}")
    print(f"  identified · intl  {summary['identified_intl']}")
    if not dry_run:
        print(f"  rows upserted      {written}")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
def run(*, dry_run: bool = False, limit: int = 0) -> dict[str, Any]:
    load_env()
    age_months = aleksandra_age_months()
    now_iso = datetime.now(timezone.utc).isoformat()

    rows = fetch_ctgov_rows()
    if limit and limit > 0:
        rows = rows[:limit]

    records: list[dict[str, Any]] = []
    for row in rows:
        rec = map_and_evaluate(
            source_id=row.get("source_id", ""),
            payload=row.get("payload_metadata") or {},
            age_months=age_months,
            now_iso=now_iso,
        )
        records.append(rec)

    summary = summarize(records)
    written = 0
    if not dry_run:
        written = upsert_trials(records)

    print(f"Aleksandra age at run: ~{age_months} months (DOB {DOB.isoformat()})")
    _print_summary(summary, dry_run=dry_run, written=written)
    return {"summary": summary, "written": written, "records": records}


# ---------------------------------------------------------------------------
# Self-test (only behind --self-test)
# ---------------------------------------------------------------------------
def _self_test() -> int:
    assert parse_age_to_months("0 Years") == 0, parse_age_to_months("0 Years")
    assert parse_age_to_months("36 Months") == 36, parse_age_to_months("36 Months")
    assert parse_age_to_months("2 Years") == 24, parse_age_to_months("2 Years")
    assert parse_age_to_months("") is None
    assert parse_age_to_months(None) is None
    assert parse_age_to_months("N/A") is None
    # case-insensitivity + singular units
    assert parse_age_to_months("1 year") == 12
    assert parse_age_to_months("1 Month") == 1
    # weeks / days conversions
    assert abs(parse_age_to_months("4 Weeks") - (4 * 7 / DAYS_PER_MONTH)) < 1e-9
    assert abs(parse_age_to_months("30 Days") - (30 / DAYS_PER_MONTH)) < 1e-9
    # location flags
    us, intl = location_flags(["Duke University (United States)"])
    assert us and not intl, (us, intl)
    us, intl = location_flags(["Some Hospital (Germany)"])
    assert (not us) and intl, (us, intl)
    us, intl = location_flags(["A (United States)", "B (Canada)"])
    assert us and intl, (us, intl)
    print("[OK] self-test passed")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute + print summary, do NOT write to the DB.",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only the first N ledger rows (0 = all).",
    )
    ap.add_argument(
        "--self-test",
        action="store_true",
        help="Run the pure-function assertions and exit (no DB access).",
    )
    args = ap.parse_args()

    if args.self_test:
        return _self_test()

    run(dry_run=args.dry_run, limit=args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
