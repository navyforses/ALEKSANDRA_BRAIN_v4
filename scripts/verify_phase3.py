"""
verify_phase3.py — Phase 3 Cognition Minimum exit-gate harness.

10-item PASS/FAIL audit covering the Phase 3 cognition surface:

  CGM-01  Source round-trip for every PMID/DOI/NCT/URL claim       (Day 3)
  CGM-02  PHI redactor catches name/DOB/MRN/hospital/MRI patterns  (Day 2)
  CGM-03  Tier router ≥ 90% accuracy on 100 labeled events         (Day 4)
  CGM-04  Outreach drafts save to Gmail (compose-only, not sent)   (Day 5)
  CGM-05  Weekly Brief renders end-to-end with citation appendix   (Day 6)
  CGM-06  Confidence classifier returns score ∈ [0,1] deterministically (Day 2)
  CGM-07  Language detection routes EN/FR/KA correctly             (Day 3)
  CGM-08  Banned-phrase detector blocks clinical-command verbs     (Day 2)
  CGM-09  Daily outreach draft cap of 5 enforced                   (Day 5)
  CGM-10  Migration 008 applied; no USING(true) on base tables     (Day 1) ← Day 0/1 baseline

Plus a final REGR row that re-runs verify_phase2_5 to confirm Phase 1/2/2.5
remain green (HC-7 gate-before-next discipline).

This file deliberately mirrors scripts/verify_phase2_5.py's structure and
helper signatures so all four verifiers can later be merged mechanically.

Day 0 / Day 1 baseline state:
  - CGM-10 is GREEN (Migration 008 applied 2026-05-16).
  - CGM-01..CGM-09 are RED with "module not implemented" evidence until the
    corresponding day ships its module under scripts/communicator/.

Usage:
    .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase3
    .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase3 --gate cgm-10
    .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase3 --gate regr
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import psycopg2

from scripts.ledger import load_env


ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Helpers (identical shape to scripts/verify_phase2_5.py — intentional)
# ---------------------------------------------------------------------------
@dataclass
class Check:
    code: str
    label: str
    passed: bool
    evidence: str
    requirement: str = ""


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
        print(f"{'#':>3}  {'CODE':<8}  {'STATUS':<6}  LABEL  →  EVIDENCE")
        print("-" * 110)
        for i, c in enumerate(self.checks, start=1):
            mark = "PASS" if c.passed else "FAIL"
            print(f"{i:>3}  {c.code:<8}  {mark:<6}  {c.label}  →  {c.evidence}")
        print("=" * 110)
        n_pass = sum(1 for c in self.checks if c.passed)
        print(
            f"  {n_pass}/{len(self.checks)} PASS  —  "
            f"{'ALL GREEN' if self.passed else 'NEEDS WORK'}"
        )


def _pg_query(sql: str, params: tuple = ()) -> list[tuple]:
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()


def _module_present(dotted: str) -> bool:
    try:
        importlib.import_module(dotted)
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# CGM-01 — Source round-trip
# ---------------------------------------------------------------------------
def check_cgm_01(report: Report) -> None:
    if not _module_present("scripts.communicator.summarize"):
        report.add(
            Check(
                "CGM-01",
                "Every Communicator output has ≥1 source citation per claim",
                False,
                "scripts.communicator.summarize not implemented (Day 3)",
                "CGM-01",
            )
        )
        return
    # Day 3 will populate the real check: walk recent outreach_log + briefs.sections,
    # confirm every claim sentence cites a PMID/DOI/NCT/URL that round-trips.
    report.add(
        Check(
            "CGM-01",
            "Every Communicator output has ≥1 source citation per claim",
            False,
            "implementation present but check body not wired (Day 3 task)",
            "CGM-01",
        )
    )


# ---------------------------------------------------------------------------
# CGM-02 — PHI redactor
# ---------------------------------------------------------------------------
def check_cgm_02(report: Report) -> None:
    if not _module_present("scripts.communicator.phi_redactor"):
        report.add(
            Check(
                "CGM-02",
                "PHI redactor catches name/DOB/MRN/hospital/MRI patterns",
                False,
                "scripts.communicator.phi_redactor not implemented (Day 2)",
                "CGM-02",
            )
        )
        return
    # Day 2 will populate: load tests/fixtures/redactor_examples.jsonl,
    # run each through redact(), assert all PHI patterns caught with consent=False.
    report.add(
        Check(
            "CGM-02",
            "PHI redactor catches name/DOB/MRN/hospital/MRI patterns",
            False,
            "implementation present but check body not wired (Day 2 task)",
            "CGM-02",
        )
    )


# ---------------------------------------------------------------------------
# CGM-03 — Tier router accuracy
# ---------------------------------------------------------------------------
def check_cgm_03(report: Report) -> None:
    if not _module_present("scripts.communicator.tier_router"):
        report.add(
            Check(
                "CGM-03",
                "Tier router ≥ 90% accuracy on 100 labeled events",
                False,
                "scripts.communicator.tier_router not implemented (Day 4)",
                "CGM-03",
            )
        )
        return
    # Day 4 will populate: load tests/fixtures/tier_router_events.jsonl (100 rows),
    # run classify() over each, assert ≥90 match the labeled tier.
    report.add(
        Check(
            "CGM-03",
            "Tier router ≥ 90% accuracy on 100 labeled events",
            False,
            "implementation present but check body not wired (Day 4 task)",
            "CGM-03",
        )
    )


# ---------------------------------------------------------------------------
# CGM-04 — Outreach drafts in Gmail
# ---------------------------------------------------------------------------
def check_cgm_04(report: Report) -> None:
    if not _module_present("scripts.communicator.outreach_drafter"):
        report.add(
            Check(
                "CGM-04",
                "Outreach drafts save to Gmail (compose-only, not sent)",
                False,
                "scripts.communicator.outreach_drafter not implemented (Day 5)",
                "CGM-04",
            )
        )
        return
    # Day 5 will populate: query outreach_log, assert ≥1 row with gmail_draft_id
    # non-null AND sent_at NULL (drafted but not sent).
    report.add(
        Check(
            "CGM-04",
            "Outreach drafts save to Gmail (compose-only, not sent)",
            False,
            "implementation present but check body not wired (Day 5 task)",
            "CGM-04",
        )
    )


# ---------------------------------------------------------------------------
# CGM-05 — Weekly Brief renders
# ---------------------------------------------------------------------------
def check_cgm_05(report: Report) -> None:
    if not _module_present("scripts.communicator.weekly_brief"):
        report.add(
            Check(
                "CGM-05",
                "Weekly Brief renders end-to-end with citation appendix",
                False,
                "scripts.communicator.weekly_brief not implemented (Day 6)",
                "CGM-05",
            )
        )
        return
    # Day 6 will populate: query briefs, assert ≥1 row with pdf_r2_path non-empty
    # and sections.citations non-empty.
    report.add(
        Check(
            "CGM-05",
            "Weekly Brief renders end-to-end with citation appendix",
            False,
            "implementation present but check body not wired (Day 6 task)",
            "CGM-05",
        )
    )


# ---------------------------------------------------------------------------
# CGM-06 — Confidence classifier
# ---------------------------------------------------------------------------
def check_cgm_06(report: Report) -> None:
    if not _module_present("scripts.communicator.confidence_classifier"):
        report.add(
            Check(
                "CGM-06",
                "Confidence classifier returns score ∈ [0,1] deterministically",
                False,
                "scripts.communicator.confidence_classifier not implemented (Day 2)",
                "CGM-06",
            )
        )
        return
    # Day 2 will populate: load tests/fixtures/confidence_examples.jsonl,
    # run score() for each, assert every output in [0.0, 1.0].
    report.add(
        Check(
            "CGM-06",
            "Confidence classifier returns score ∈ [0,1] deterministically",
            False,
            "implementation present but check body not wired (Day 2 task)",
            "CGM-06",
        )
    )


# ---------------------------------------------------------------------------
# CGM-07 — Language detection
# ---------------------------------------------------------------------------
def check_cgm_07(report: Report) -> None:
    if not _module_present("scripts.communicator.language"):
        report.add(
            Check(
                "CGM-07",
                "Language detection routes EN/FR/KA correctly",
                False,
                "scripts.communicator.language not implemented (Day 3)",
                "CGM-07",
            )
        )
        return
    # Day 3 will populate: 30 sample inputs (10 each EN/FR/KA), assert detect()
    # returns the right code on ≥ 28/30.
    report.add(
        Check(
            "CGM-07",
            "Language detection routes EN/FR/KA correctly",
            False,
            "implementation present but check body not wired (Day 3 task)",
            "CGM-07",
        )
    )


# ---------------------------------------------------------------------------
# CGM-08 — Banned-phrase detector
# ---------------------------------------------------------------------------
def check_cgm_08(report: Report) -> None:
    if not _module_present("scripts.communicator.banned_phrases"):
        report.add(
            Check(
                "CGM-08",
                "Banned-phrase detector blocks clinical-command verbs",
                False,
                "scripts.communicator.banned_phrases not implemented (Day 2)",
                "CGM-08",
            )
        )
        return
    # Day 2 will populate: load tests/fixtures/banned_good.jsonl + banned_bad.jsonl,
    # assert ≥ 95% correct classification on the combined set.
    report.add(
        Check(
            "CGM-08",
            "Banned-phrase detector blocks clinical-command verbs",
            False,
            "implementation present but check body not wired (Day 2 task)",
            "CGM-08",
        )
    )


# ---------------------------------------------------------------------------
# CGM-09 — Daily outreach cap
# ---------------------------------------------------------------------------
def check_cgm_09(report: Report) -> None:
    if not _module_present("scripts.communicator.outreach_drafter"):
        report.add(
            Check(
                "CGM-09",
                "Daily outreach draft cap of 5 enforced",
                False,
                "scripts.communicator.outreach_drafter not implemented (Day 5)",
                "CGM-09",
            )
        )
        return
    # Day 5 will populate: integration test that creates 5 drafts then asserts the
    # 6th attempt returns OutreachDraft(blocked=True, reason='daily_cap_reached').
    report.add(
        Check(
            "CGM-09",
            "Daily outreach draft cap of 5 enforced",
            False,
            "implementation present but check body not wired (Day 5 task)",
            "CGM-09",
        )
    )


# ---------------------------------------------------------------------------
# CGM-10 — Migration 008 applied + RLS audit clean
# ---------------------------------------------------------------------------
def check_cgm_10(report: Report) -> None:
    # Three sub-conditions, all must hold:
    #   (a) The three new tables exist.
    #   (b) The ten base tables have no policy named "Service role full access".
    #   (c) The contacts table has the six new consent/outreach columns.
    try:
        new_tables = _pg_query(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='public'
              AND table_name IN ('outreach_log','alerts_log','briefs')
            """
        )
        new_set = {r[0] for r in new_tables}
        cond_a = new_set == {"outreach_log", "alerts_log", "briefs"}

        bad_policies = _pg_query(
            """
            SELECT tablename, policyname FROM pg_policies
            WHERE schemaname='public'
              AND policyname = 'Service role full access'
            """
        )
        cond_b = len(bad_policies) == 0

        new_cols = _pg_query(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name='contacts'
              AND column_name IN (
                'consent_full_name','consent_doctor_names','consent_hospital_names',
                'outreach_language','last_contacted_at','outreach_count'
              )
            """
        )
        cond_c = len(new_cols) == 6

        ok = cond_a and cond_b and cond_c
        evidence = (
            f"new_tables={sorted(new_set)} "
            f"bad_policies={len(bad_policies)} "
            f"new_contact_cols={len(new_cols)}/6"
        )
        report.add(
            Check(
                "CGM-10",
                "Migration 008 applied; no USING(true) on base tables",
                ok,
                evidence,
                "CGM-10",
            )
        )
    except Exception as e:
        report.add(
            Check(
                "CGM-10",
                "Migration 008 applied; no USING(true) on base tables",
                False,
                f"{type(e).__name__}: {e}",
                "CGM-10",
            )
        )


# ---------------------------------------------------------------------------
# Regression — Phase 2.5 still green
# ---------------------------------------------------------------------------
def check_regression(report: Report) -> None:
    try:
        from scripts.verify_phase2_5 import (
            check_gate_a,
            check_gate_b,
            check_gate_c,
            check_gate_d,
        )
        from scripts.verify_phase2_5 import check_regression as p25_regr

        sub = Report()
        check_gate_a(sub)
        check_gate_b(sub)
        check_gate_c(sub)
        check_gate_d(sub)
        p25_regr(sub)
        passed = sum(1 for c in sub.checks if c.passed)
        total = len(sub.checks)
        report.add(
            Check(
                "REGR",
                "verify_phase2_5 still PASS (no Phase 2.5 regression)",
                passed == total,
                f"{passed}/{total} PASS",
                "REGR",
            )
        )
    except Exception as e:
        report.add(
            Check(
                "REGR",
                "verify_phase2_5 still PASS (no Phase 2.5 regression)",
                False,
                f"{type(e).__name__}: {e}",
                "REGR",
            )
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
GATES = {
    "cgm-01": check_cgm_01,
    "cgm-02": check_cgm_02,
    "cgm-03": check_cgm_03,
    "cgm-04": check_cgm_04,
    "cgm-05": check_cgm_05,
    "cgm-06": check_cgm_06,
    "cgm-07": check_cgm_07,
    "cgm-08": check_cgm_08,
    "cgm-09": check_cgm_09,
    "cgm-10": check_cgm_10,
    "regr": check_regression,
}

ALL_ORDER = (
    check_cgm_01,
    check_cgm_02,
    check_cgm_03,
    check_cgm_04,
    check_cgm_05,
    check_cgm_06,
    check_cgm_07,
    check_cgm_08,
    check_cgm_09,
    check_cgm_10,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--gate",
        choices=list(GATES.keys()) + ["all"],
        default="all",
        help="Run only one gate (default: all).",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of the table.",
    )
    args = ap.parse_args()

    load_env()
    report = Report()

    if args.gate == "all":
        for fn in ALL_ORDER:
            fn(report)
        check_regression(report)
    else:
        GATES[args.gate](report)

    if args.json:
        out = {
            "passed": report.passed,
            "checks": [
                {
                    "code": c.code,
                    "gate": c.requirement,
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
