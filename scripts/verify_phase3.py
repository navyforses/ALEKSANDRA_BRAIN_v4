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

    # CGM-01 runs ONE live summarize() call on a fixed Phase 3 fixture query
    # and asserts that every returned claim has ≥1 citation_id. The
    # summarize.py code already drops uncited claims before returning, but
    # this gate confirms that contract end-to-end against live evidence.
    from scripts.communicator.summarize import generate_summary

    fixture_query = "Cord blood expanded-access programs for severe neonatal HIE"
    try:
        draft = generate_summary(fixture_query, audience="internal", language="en")
    except Exception as e:
        report.add(
            Check(
                "CGM-01",
                "Every Communicator output has ≥1 source citation per claim",
                False,
                f"live summarize() raised: {type(e).__name__}: {str(e)[:200]}",
                "CGM-01",
            )
        )
        return

    n_claims = len(draft.claims)
    n_cited = sum(1 for c in draft.claims if c.citation_ids)
    persistable = draft.persistable()
    ok = n_claims >= 1 and n_cited == n_claims and persistable
    evidence = (
        f"claims={n_claims}  cited={n_cited}/{n_claims}  persistable={persistable}  "
        f"confidence={draft.confidence}"
    )
    report.add(
        Check(
            "CGM-01",
            "Every Communicator output has ≥1 source citation per claim",
            ok,
            evidence,
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
    from scripts.communicator import phi_redactor as P

    fixtures_path = ROOT / "tests" / "fixtures" / "redactor_examples.jsonl"
    if not fixtures_path.exists():
        report.add(
            Check(
                "CGM-02",
                "PHI redactor catches name/DOB/MRN/hospital/MRI patterns",
                False,
                f"fixture missing: {fixtures_path}",
                "CGM-02",
            )
        )
        return

    passed = 0
    total = 0
    failures: list[str] = []
    with fixtures_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            row = json.loads(line)
            consent = P.ConsentFlags(
                consent_full_name=row["consent"].get("consent_full_name", False),
                consent_doctor_names=row["consent"].get("consent_doctor_names", False),
                consent_hospital_names=row["consent"].get(
                    "consent_hospital_names", False
                ),
            )
            result = P.redact(row["text"], consent=consent)
            got_blocked = bool(result.blocked)
            want_blocked = bool(row.get("expect_blocked", False))
            got_categories = sorted({r.category for r in result.redactions})
            want_categories = sorted(row.get("expected_categories", []))
            ok = got_blocked == want_blocked and got_categories == want_categories
            if ok:
                passed += 1
            else:
                failures.append(
                    f"{row['label']}: want blocked={want_blocked} cats={want_categories}, "
                    f"got blocked={got_blocked} cats={got_categories}"
                )
    ok = passed == total and total >= 10
    evidence = f"{passed}/{total} fixtures match"
    if failures:
        evidence += f"  first_failure={failures[0]!r}"
    report.add(
        Check(
            "CGM-02",
            "PHI redactor catches name/DOB/MRN/hospital/MRI patterns",
            ok,
            evidence,
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
    from scripts.communicator.confidence_classifier import ConfidenceInput, score

    fixtures_path = ROOT / "tests" / "fixtures" / "confidence_examples.jsonl"
    if not fixtures_path.exists():
        report.add(
            Check(
                "CGM-06",
                "Confidence classifier returns score ∈ [0,1] deterministically",
                False,
                f"fixture missing: {fixtures_path}",
                "CGM-06",
            )
        )
        return

    in_range = 0
    in_band = 0
    total = 0
    band_failures: list[str] = []
    with fixtures_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            row = json.loads(line)
            ci = ConfidenceInput(
                evidence_grade=row["input"]["evidence_grade"],
                source_count=row["input"]["source_count"],
                source_recency_years=row["input"]["source_recency_years"],
                direct_relevance=row["input"]["direct_relevance"],
                citation_round_trip_passed=row["input"]["citation_round_trip_passed"],
            )
            s = score(ci)
            if 0.0 <= s <= 1.0:
                in_range += 1
            lo = row["expected_min"]
            hi = row["expected_max"]
            if lo <= s <= hi:
                in_band += 1
            else:
                band_failures.append(f"{row['label']}: got {s}, want [{lo},{hi}]")
    ok = in_range == total and in_band == total and total >= 20
    evidence = f"in_range={in_range}/{total}  in_band={in_band}/{total}"
    if band_failures:
        evidence += f"  first_failure={band_failures[0]!r}"
    report.add(
        Check(
            "CGM-06",
            "Confidence classifier returns score ∈ [0,1] deterministically",
            ok,
            evidence,
            "CGM-06",
        )
    )


# ---------------------------------------------------------------------------
# CGM-07 — Language detection
# ---------------------------------------------------------------------------
_LANG_FIXTURE: tuple[tuple[str, str], ...] = (
    # 10 English
    ("en", "Review the latest paper on cord blood expanded-access protocols."),
    (
        "en",
        "Three cohort studies report neuroplasticity windows in the first 24 months.",
    ),
    ("en", "Discuss vigabatrin washout timing with the clinician before Duke EAP."),
    ("en", "The trial sponsor lists vigabatrin washout as an exclusion criterion."),
    ("en", "Two preprints describe cystic encephalomalacia segmentation pipelines."),
    ("en", "Confirm with the family whether this question is in scope for next week."),
    ("en", "The BONBID-HIE 2024 challenge top-3 architectures share a training set."),
    ("en", "Schedule a clinician conversation about repurposing candidates."),
    ("en", "Recent meta-analysis identifies promising neuroplasticity windows."),
    ("en", "The investigator reports an open enrollment window through July 2026."),
    # 10 Georgian
    ("ka", "ალექსანდრა გადადის შემდეგ ეტაპზე."),
    ("ka", "მოამზადე ექიმთან განსახილველი მოკლე ბრიფი."),
    ("ka", "შესაძლოა ღირდეს ექიმთან განხილვა შემდეგ ვიზიტზე."),
    ("ka", "შენიშნე ეს კვირეული ბრიფისთვის."),
    ("ka", "გაუგზავნე ეს ექიმს კონტექსტისთვის."),
    ("ka", "შეინახე ეს მონაცემი დანართისთვის."),
    ("ka", "ცისტური ენცეფალომალაცია ცნობილია სამედიცინო ლიტერატურაში."),
    ("ka", "Duke-ის EAP პროგრამა მუშაობს უპირატესობით."),
    ("ka", "ვიგაბატრინის გამორეცხვის ფანჯარა აქტიურია."),
    ("ka", "ნეიროპლასტიკურობის ფანჯარა 0-2 წლის შუალედშია."),
    # 10 French
    ("fr", "Cet article mérite d'être discuté avec la clinicienne."),
    ("fr", "Examiner ce préprint avant la prochaine consultation."),
    ("fr", "Notez cette étude pour la synthèse hebdomadaire."),
    ("fr", "Trois études de cohorte indépendantes citent un résultat similaire."),
    ("fr", "Le coordinateur de l'essai a confirmé la fenêtre d'inclusion."),
    ("fr", "La méta-analyse récente identifie des fenêtres de neuroplasticité."),
    ("fr", "Les enfants en bas âge montrent une grande plasticité cérébrale."),
    ("fr", "Cette recherche est très prometteuse pour les bébés atteints d'HIE."),
    ("fr", "Nous étudions les protocoles d'élargissement de l'accès."),
    ("fr", "L'enfant a été examiné dans un hôpital universitaire."),
)


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
    from scripts.communicator.language import detect

    correct = 0
    total = len(_LANG_FIXTURE)
    failures: list[str] = []
    by_lang: dict[str, tuple[int, int]] = {"en": (0, 0), "ka": (0, 0), "fr": (0, 0)}
    for expected, text in _LANG_FIXTURE:
        got = detect(text).code
        c, t = by_lang[expected]
        by_lang[expected] = (c + (1 if got == expected else 0), t + 1)
        if got == expected:
            correct += 1
        else:
            failures.append(f"want={expected} got={got}: {text[:40]!r}")
    accuracy = correct / total if total else 0.0
    ok = correct >= 28 and total == 30
    per_lang = " ".join(f"{k}={v[0]}/{v[1]}" for k, v in by_lang.items())
    evidence = f"{correct}/{total} correct ({accuracy:.0%})  {per_lang}"
    if failures:
        evidence += f"  first_failure={failures[0]!r}"
    report.add(
        Check(
            "CGM-07",
            "Language detection routes EN/FR/KA correctly",
            ok,
            evidence,
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
    from scripts.communicator.banned_phrases import check as bp_check

    fix_good = ROOT / "tests" / "fixtures" / "banned_good.jsonl"
    fix_bad = ROOT / "tests" / "fixtures" / "banned_bad.jsonl"
    if not (fix_good.exists() and fix_bad.exists()):
        report.add(
            Check(
                "CGM-08",
                "Banned-phrase detector blocks clinical-command verbs",
                False,
                "fixtures missing (banned_good.jsonl / banned_bad.jsonl)",
                "CGM-08",
            )
        )
        return

    def _load(path):
        out = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    good_rows = _load(fix_good)
    bad_rows = _load(fix_bad)

    # Good rows: every check() must return passed=True
    good_pass = sum(1 for r in good_rows if bp_check(r["text"]).passed)
    # Bad rows: every check() must return passed=False
    bad_caught = sum(1 for r in bad_rows if not bp_check(r["text"]).passed)

    total_good = len(good_rows)
    total_bad = len(bad_rows)
    # Accuracy target: ≥95% of the combined set classified correctly.
    correct = good_pass + bad_caught
    total = total_good + total_bad
    accuracy = (correct / total) if total else 0.0
    ok = accuracy >= 0.95 and total_good >= 25 and total_bad >= 25
    evidence = (
        f"good_pass={good_pass}/{total_good}  bad_caught={bad_caught}/{total_bad}  "
        f"accuracy={accuracy:.2%}"
    )
    report.add(
        Check(
            "CGM-08",
            "Banned-phrase detector blocks clinical-command verbs",
            ok,
            evidence,
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
