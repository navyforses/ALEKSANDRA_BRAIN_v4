"""
verify_trials.py — Phase A wave 1 exit-gate harness for clinical_trials.

PASS/FAIL audit over the seeded clinical_trials table. Mirrors the
Check/Report table style of scripts/verify_phase3.py. All checks run
against live Supabase via PostgREST (httpx), so the verifier needs only
SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY.

Checks
------
  TRIALS-01  clinical_trials reachable (PostgREST 200)
  TRIALS-02  row count > 0 after seed
  TRIALS-03  every row has non-null nct_id and title
  TRIALS-04  every aleksandra_status is within the allowed enum set
  TRIALS-05  counts reconcile: sum(by status) == total
  TRIALS-06  aleksandra_eligible is non-null for all rows
  TRIALS-07  title + brief_summary stored as JSONB {en,..} for shown trials
  TRIALS-08  detailed_description present (non-null) for >=1 shown trial
  TRIALS-09  >=1 shown trial has a non-empty ka in title (translation works)
  TRIALS-10  every row has a populated registry; >=1 non-ctgov trial after seed
  TRIALS-11  no duplicate (registry, registry_id) pair

"Shown" trials = aleksandra_status in {identified, evaluating} (the rows the
viewer surfaces). TRIALS-07..09 are Phase C (full ctgov detail + bilingual).
TRIALS-10..11 are Phase E (multi-registry: EU CTIS + UK ISRCTN + cross-registry
dedup).

Usage
-----
    .venv/Scripts/python.exe -m scripts.verify_trials
    .venv/Scripts/python.exe -m scripts.verify_trials --json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Any

import httpx

from scripts.ledger import _supabase_creds, _supabase_headers, load_env

SHOWN_STATUS = {"identified", "evaluating"}

ALLOWED_STATUS = {
    "identified",
    "evaluating",
    "applied",
    "enrolled",
    "ineligible",
    "declined",
    "waitlisted",
    "completed",
}


# ---------------------------------------------------------------------------
# Report scaffolding (same shape as verify_phase3.py)
# ---------------------------------------------------------------------------
@dataclass
class Check:
    code: str
    label: str
    passed: bool
    evidence: str


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)

    def add(self, c: Check) -> None:
        self.checks.append(c)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def print_table(self) -> None:
        print("=" * 110)
        print(f"{'#':>3}  {'CODE':<10}  {'STATUS':<6}  LABEL  →  EVIDENCE")
        print("-" * 110)
        for i, c in enumerate(self.checks, start=1):
            mark = "PASS" if c.passed else "FAIL"
            print(f"{i:>3}  {c.code:<10}  {mark:<6}  {c.label}  →  {c.evidence}")
        print("=" * 110)
        n_pass = sum(1 for c in self.checks if c.passed)
        print(
            f"  {n_pass}/{len(self.checks)} PASS  —  "
            f"{'ALL GREEN' if self.passed else 'NEEDS WORK'}"
        )


# ---------------------------------------------------------------------------
# Data fetch (shared across checks)
# ---------------------------------------------------------------------------
def _fetch_all_rows() -> list[dict]:
    """Pull all rows with the columns the checks need. Raises on non-200."""
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/clinical_trials",
        params={
            "select": (
                "nct_id,title,aleksandra_status,aleksandra_eligible,"
                "brief_summary,detailed_description,"
                "registry,registry_id,secondary_ids"
            ),
            "limit": "10000",
        },
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


def _is_bilingual(value: Any) -> bool:
    """True iff `value` is a JSONB {en, ...} object (not plain text / None).

    PostgREST returns a JSONB column as a parsed dict, and a TEXT column as a
    plain string — so dict-ness is exactly "stored as JSONB". We also require an
    'en' key so a stray empty {} does not count.
    """
    return isinstance(value, dict) and "en" in value


def _ka(value: Any) -> str:
    """Non-empty ka string from a {en, ka} JSONB dict, else ""."""
    if isinstance(value, dict):
        ka = value.get("ka")
        return str(ka).strip() if ka else ""
    return ""


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def check_reachable(report: Report) -> bool:
    """TRIALS-01 — PostgREST reachable (200)."""
    try:
        url, key = _supabase_creds()
        r = httpx.get(
            f"{url}/rest/v1/clinical_trials",
            params={"select": "nct_id", "limit": "1"},
            headers=_supabase_headers(key, prefer="count=none"),
            timeout=15,
        )
        ok = r.status_code == 200
        report.add(
            Check(
                "TRIALS-01",
                "clinical_trials reachable via PostgREST",
                ok,
                f"HTTP {r.status_code}",
            )
        )
        return ok
    except Exception as e:
        report.add(
            Check(
                "TRIALS-01",
                "clinical_trials reachable via PostgREST",
                False,
                f"{type(e).__name__}: {e}",
            )
        )
        return False


def run_checks(report: Report) -> None:
    _DEPENDENT_CHECKS = (
        ("TRIALS-02", "row count > 0 after seed"),
        ("TRIALS-03", "every row has non-null nct_id and title"),
        ("TRIALS-04", "every aleksandra_status within allowed enum"),
        ("TRIALS-05", "status counts reconcile with total"),
        ("TRIALS-06", "aleksandra_eligible non-null for all rows"),
        ("TRIALS-07", "title + brief_summary stored as JSONB for shown trials"),
        ("TRIALS-08", "detailed_description present for >=1 shown trial"),
        ("TRIALS-09", "at least one shown trial has a non-empty ka title"),
        ("TRIALS-10", "registry populated for all rows; >=1 non-ctgov trial"),
        ("TRIALS-11", "no duplicate (registry, registry_id) pair"),
    )

    if not check_reachable(report):
        # Without reachability the remaining checks cannot run meaningfully.
        for code, label in _DEPENDENT_CHECKS:
            report.add(Check(code, label, False, "skipped — table not reachable"))
        return

    try:
        rows = _fetch_all_rows()
    except Exception as e:
        for code, label in _DEPENDENT_CHECKS:
            report.add(
                Check(code, label, False, f"fetch failed: {type(e).__name__}: {e}")
            )
        return

    total = len(rows)

    # TRIALS-02 — row count > 0
    report.add(
        Check("TRIALS-02", "row count > 0 after seed", total > 0, f"rows={total}")
    )

    # TRIALS-03 — non-null nct_id + title
    bad_ident = [
        r.get("nct_id") for r in rows if not r.get("nct_id") or not r.get("title")
    ]
    report.add(
        Check(
            "TRIALS-03",
            "every row has non-null nct_id and title",
            len(bad_ident) == 0 and total > 0,
            f"{total - len(bad_ident)}/{total} complete; missing={len(bad_ident)}",
        )
    )

    # TRIALS-04 — status within enum
    bad_status = [
        r.get("aleksandra_status")
        for r in rows
        if r.get("aleksandra_status") not in ALLOWED_STATUS
    ]
    report.add(
        Check(
            "TRIALS-04",
            "every aleksandra_status within allowed enum",
            len(bad_status) == 0 and total > 0,
            f"out_of_enum={len(bad_status)}"
            + (f" e.g. {bad_status[0]!r}" if bad_status else ""),
        )
    )

    # TRIALS-05 — counts reconcile
    counts: dict[str, int] = {}
    for r in rows:
        st = r.get("aleksandra_status")
        counts[st] = counts.get(st, 0) + 1
    summed = sum(counts.values())
    report.add(
        Check(
            "TRIALS-05",
            "status counts reconcile with total",
            summed == total and total > 0,
            f"sum={summed} total={total}  breakdown={counts}",
        )
    )

    # TRIALS-06 — aleksandra_eligible non-null for all
    null_elig = [r for r in rows if r.get("aleksandra_eligible") is None]
    report.add(
        Check(
            "TRIALS-06",
            "aleksandra_eligible non-null for all rows",
            len(null_elig) == 0 and total > 0,
            f"{total - len(null_elig)}/{total} populated; null={len(null_elig)}",
        )
    )

    # "Shown" trials = the rows the viewer surfaces (Phase C checks scope here).
    shown = [r for r in rows if r.get("aleksandra_status") in SHOWN_STATUS]
    n_shown = len(shown)

    # TRIALS-07 — title + brief_summary stored as JSONB {en,..} for shown trials.
    # title is NOT NULL, so every shown title must be JSONB. brief_summary is
    # nullable, so only the non-null ones are required to be JSONB (a genuinely
    # missing summary stays NULL — not a defect).
    bad_title = [r for r in shown if not _is_bilingual(r.get("title"))]
    bad_summary = [
        r
        for r in shown
        if r.get("brief_summary") is not None
        and not _is_bilingual(r.get("brief_summary"))
    ]
    report.add(
        Check(
            "TRIALS-07",
            "title + brief_summary stored as JSONB for shown trials",
            n_shown > 0 and not bad_title and not bad_summary,
            f"shown={n_shown}; title_not_jsonb={len(bad_title)}; "
            f"summary_not_jsonb={len(bad_summary)}",
        )
    )

    # TRIALS-08 — detailed_description present (non-null) for >=1 shown trial.
    with_detail = [r for r in shown if r.get("detailed_description") is not None]
    report.add(
        Check(
            "TRIALS-08",
            "detailed_description present for >=1 shown trial",
            len(with_detail) >= 1,
            f"{len(with_detail)}/{n_shown} shown trials have detailed_description",
        )
    )

    # TRIALS-09 — >=1 shown trial has a non-empty ka in title (translation path).
    with_ka_title = [r for r in shown if _ka(r.get("title"))]
    report.add(
        Check(
            "TRIALS-09",
            "at least one shown trial has a non-empty ka title",
            len(with_ka_title) >= 1,
            f"{len(with_ka_title)}/{n_shown} shown titles have ka",
        )
    )

    # TRIALS-10 (Phase E) — every row has a populated registry, AND >=1 non-ctgov
    # trial exists after seed (proves the EU CTIS / UK ISRCTN sources landed).
    null_registry = [r for r in rows if not (r.get("registry") or "").strip()]
    by_registry: dict[str, int] = {}
    for r in rows:
        reg = (r.get("registry") or "(null)").strip() or "(null)"
        by_registry[reg] = by_registry.get(reg, 0) + 1
    non_ctgov = sum(v for k, v in by_registry.items() if k not in ("ctgov", "(null)"))
    report.add(
        Check(
            "TRIALS-10",
            "registry populated for all rows; >=1 non-ctgov trial",
            len(null_registry) == 0 and total > 0 and non_ctgov >= 1,
            f"null_registry={len(null_registry)}; non_ctgov={non_ctgov}; "
            f"breakdown={by_registry}",
        )
    )

    # TRIALS-11 (Phase E) — no duplicate (registry, registry_id) pair (the partial
    # dedup natural key must be unique; cross-registry dedup must not double-write).
    seen: dict[tuple[str, str], int] = {}
    for r in rows:
        reg = (r.get("registry") or "").strip()
        rid = (r.get("registry_id") or "").strip()
        if not reg or not rid:
            continue
        key = (reg, rid)
        seen[key] = seen.get(key, 0) + 1
    dupes = {k: n for k, n in seen.items() if n > 1}
    report.add(
        Check(
            "TRIALS-11",
            "no duplicate (registry, registry_id) pair",
            len(dupes) == 0 and total > 0,
            f"distinct_keys={len(seen)}; duplicate_pairs={len(dupes)}"
            + (f" e.g. {next(iter(dupes))}" if dupes else ""),
        )
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of the table.",
    )
    args = ap.parse_args()

    load_env()
    report = Report()
    run_checks(report)

    if args.json:
        out = {
            "passed": report.passed,
            "checks": [
                {
                    "code": c.code,
                    "label": c.label,
                    "passed": c.passed,
                    "evidence": c.evidence,
                }
                for c in report.checks
            ],
        }
        print(json.dumps(out, indent=2, default=str))
    else:
        report.print_table()

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
