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
  CGM-10  Migration 008 + contacts seed + anon RLS smoke           (Day 1) ← Day 0/1 baseline

Plus a final REGR row that re-runs verify_phase2_5 to confirm Phase 1/2/2.5
remain green (HC-7 gate-before-next discipline).

This file deliberately mirrors scripts/verify_phase2_5.py's structure and
helper signatures so all four verifiers can later be merged mechanically.

Day 0 / Day 1 baseline state:
  - CGM-10 is GREEN only after Migration 008 is applied, contacts has >=75 rows,
    and anon REST smoke tests return 401/403 or no rows.
  - Later CGM gates may already be GREEN if a future-day module was built early.

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

import httpx
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


def _anon_rest_no_rows(table: str) -> tuple[bool, str]:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    anon = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url:
        return False, "SUPABASE_URL missing"
    if not anon:
        return False, "SUPABASE_ANON_KEY missing"

    try:
        r = httpx.get(
            f"{url}/rest/v1/{table}",
            params={"select": "id", "limit": "1"},
            headers={"apikey": anon, "Authorization": f"Bearer {anon}"},
            timeout=8,
        )
        if r.status_code in (401, 403):
            return True, f"{table}=HTTP {r.status_code}"
        if r.status_code == 200:
            try:
                body = r.json()
            except ValueError:
                return False, f"{table}=HTTP 200 non-json body_len={len(r.text)}"
            return (
                body == [],
                f"{table}=HTTP 200 rows={len(body) if isinstance(body, list) else 'non-list'}",
            )
        return False, f"{table}=HTTP {r.status_code} body_len={len(r.text)}"
    except Exception as e:
        return False, f"{table}={type(e).__name__}: {e}"


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
    banned_passed = draft.banned.passed if draft.banned else True
    redaction_blocked = draft.redaction.blocked if draft.redaction else False
    # CGM-01's contract is the citation-per-claim ratio. The persistable
    # status is a downstream-safety signal that's surfaced for visibility
    # but not gated here — banned phrasing is the CGM-08 contract and
    # redaction is the CGM-02 contract, both already enforced by separate
    # gates. Gating CGM-01 on persistable would make it flake on the
    # non-deterministic Sonnet output.
    ok = n_claims >= 1 and n_cited == n_claims
    evidence = (
        f"claims={n_claims}  cited={n_cited}/{n_claims}  "
        f"persistable={persistable}  banned_passed={banned_passed}  "
        f"redaction_blocked={redaction_blocked}  confidence={draft.confidence}"
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
    from datetime import datetime

    from scripts.communicator.tier_router import Event, classify

    fixture_path = ROOT / "tests" / "fixtures" / "tier_router_events.jsonl"
    if not fixture_path.exists():
        report.add(
            Check(
                "CGM-03",
                "Tier router ≥ 90% accuracy on 100 labeled events",
                False,
                f"fixture missing: {fixture_path}",
                "CGM-03",
            )
        )
        return

    correct = 0
    total = 0
    by_tier: dict[str, list[int]] = {t: [0, 0] for t in ("T0", "T1", "T2", "T3", "T4")}
    failures: list[str] = []
    with fixture_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            row = json.loads(line)
            expected = row["expected_tier"]
            by_tier[expected][1] += 1
            ev = Event(
                kind=row["kind"],
                confidence=row["confidence"],
                phi_blocked=row.get("phi_blocked", False),
                banned_blocked=row.get("banned_blocked", False),
                source_round_trip_passed=row.get("source_round_trip_passed", True),
                is_duplicate=row.get("is_duplicate", False),
                payload=row.get("payload", {}),
                timestamp=datetime.fromisoformat(row["timestamp_iso"]),
            )
            decision = classify(ev, t1_count_today=row.get("t1_count_today", 0))
            if decision.tier == expected:
                correct += 1
                by_tier[expected][0] += 1
            else:
                failures.append(
                    f"{row['id']}: want={expected} got={decision.tier} ({decision.reason})"
                )

    accuracy = correct / total if total else 0.0
    ok = correct >= 90 and total == 100
    per_tier = " ".join(f"{k}={v[0]}/{v[1]}" for k, v in by_tier.items())
    evidence = f"{correct}/{total} correct ({accuracy:.0%})  {per_tier}"
    if failures:
        evidence += f"  first_failure={failures[0]!r}"
    report.add(
        Check(
            "CGM-03",
            "Tier router ≥ 90% accuracy on 100 labeled events",
            ok,
            evidence,
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
    from scripts.communicator import outreach_drafter as OD

    # Structural compose-only contract: scope is gmail.compose, gmail.send
    # is NEVER in the scope list. Send action stays manual (months 1–6).
    scopes_ok = OD.GMAIL_SCOPES == ("https://www.googleapis.com/auth/gmail.compose",)
    no_send_anywhere = "gmail.send" not in " ".join(OD.GMAIL_SCOPES)

    # Live drafts: count of outreach_log rows with gmail_draft_id non-null
    # AND sent_at NULL. >=1 means at least one draft is staged for Shako.
    drafts_pending = _pg_query(
        """
        SELECT count(*) FROM outreach_log
        WHERE gmail_draft_id IS NOT NULL AND sent_at IS NULL
        """
    )
    n_pending = int(drafts_pending[0][0]) if drafts_pending else 0

    # The structural contract is required, and Day 5 is not actually GREEN
    # until at least one compose-only Gmail draft has been staged and logged.
    workflow_file = ROOT / "workflows" / "outreach_review_queue.json"
    ok = scopes_ok and no_send_anywhere and workflow_file.exists() and n_pending >= 1
    evidence = (
        f"scopes={list(OD.GMAIL_SCOPES)}  no_send={no_send_anywhere}  "
        f"workflow={workflow_file.exists()}  pending_drafts={n_pending}"
    )
    report.add(
        Check(
            "CGM-04",
            "Outreach drafts save to Gmail (compose-only, not sent)",
            ok,
            evidence,
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
    import tempfile
    from datetime import date

    from scripts.communicator.weekly_brief import collect_sections, render_pdf

    try:
        sections = collect_sections(date(2026, 5, 18), fixture=True)
    except Exception as e:
        report.add(
            Check(
                "CGM-05",
                "Weekly Brief renders end-to-end with citation appendix",
                False,
                f"collect_sections raised: {type(e).__name__}: {str(e)[:200]}",
                "CGM-05",
            )
        )
        return

    out = Path(tempfile.gettempdir()) / "phase3_cgm05_smoke.pdf"
    try:
        render_pdf(sections, out)
    except Exception as e:
        report.add(
            Check(
                "CGM-05",
                "Weekly Brief renders end-to-end with citation appendix",
                False,
                f"render_pdf raised: {type(e).__name__}: {str(e)[:200]}",
                "CGM-05",
            )
        )
        return

    pdf_ok = out.exists() and out.stat().st_size > 1024
    citations_ok = len(sections.citations) >= 1
    questions_ok = isinstance(sections.questions, list)
    section_count = (
        len(sections.papers)
        + len(sections.hypotheses)
        + len(sections.therapies)
        + len(sections.outreach)
    )
    ok = pdf_ok and citations_ok and questions_ok and section_count >= 4

    evidence = (
        f"pdf={out.exists()}({out.stat().st_size if out.exists() else 0}B)  "
        f"citations={len(sections.citations)}  "
        f"sections_filled={section_count}  "
        f"questions_loaded={len(sections.questions)}"
    )
    try:
        out.unlink()
    except OSError:
        pass

    report.add(
        Check(
            "CGM-05",
            "Weekly Brief renders end-to-end with citation appendix",
            ok,
            evidence,
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
    from scripts.communicator.outreach_drafter import (
        MAX_DAILY_DRAFTS,
        draft_outreach,
    )

    # Unit-style cap verification — we pass today_draft_count explicitly so
    # this check doesn't depend on the contacts seed or live DB state.
    # The contact_id is a synthetic UUID-shaped string; with dry_run=True,
    # draft_outreach() short-circuits BEFORE the contact lookup when the cap
    # is reached, so the test stays isolated from contacts.
    draft = draft_outreach(
        contact_id="00000000-0000-0000-0000-000000000000",
        query="research follow-up on cord blood expanded-access programs",
        purpose="follow_up",
        language="en",
        today_draft_count=MAX_DAILY_DRAFTS,
        dry_run=True,
    )
    cap_ok = (
        draft.blocked is True
        and "daily_cap_reached" in (draft.block_reason or "")
        and MAX_DAILY_DRAFTS == 5
    )
    evidence = (
        f"MAX_DAILY_DRAFTS={MAX_DAILY_DRAFTS}  "
        f"blocked={draft.blocked}  "
        f"block_reason={draft.block_reason!r}"
    )
    report.add(
        Check(
            "CGM-09",
            "Daily outreach draft cap of 5 enforced",
            cap_ok,
            evidence,
            "CGM-09",
        )
    )


# ---------------------------------------------------------------------------
# CGM-10 — Migration 008 applied + contacts seeded + RLS audit clean
# ---------------------------------------------------------------------------
def check_cgm_10(report: Report) -> None:
    # Five sub-conditions, all must hold:
    #   (a) The three new tables exist.
    #   (b) The ten base tables have no policy named "Service role full access".
    #   (c) The contacts table has the six new consent/outreach columns.
    #   (d) The contacts table has the Day 1 minimum seed count.
    #   (e) Anon REST reads on family-sensitive tables return no rows or 401/403.
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

        contact_count = _pg_query("SELECT count(*) FROM contacts")[0][0]
        cond_d = contact_count >= 75

        smoke_tables = ("papers", "therapies", "hypotheses", "contacts", "outreach_log")
        smoke_results = [_anon_rest_no_rows(t) for t in smoke_tables]
        cond_e = all(ok for ok, _msg in smoke_results)
        smoke_evidence = "; ".join(msg for _ok, msg in smoke_results)

        ok = cond_a and cond_b and cond_c and cond_d and cond_e
        evidence = (
            f"new_tables={sorted(new_set)} "
            f"bad_policies={len(bad_policies)} "
            f"new_contact_cols={len(new_cols)}/6 "
            f"contacts={contact_count}/75 "
            f"anon_smoke=[{smoke_evidence}]"
        )
        report.add(
            Check(
                "CGM-10",
                "Migration 008, contacts seed, and anon RLS smoke pass",
                ok,
                evidence,
                "CGM-10",
            )
        )
    except Exception as e:
        report.add(
            Check(
                "CGM-10",
                "Migration 008, contacts seed, and anon RLS smoke pass",
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
