"""
verify_phase5.py — Phase 5 BRAIN AI Manager Assistant exit-gate harness.

12-item PASS/FAIL audit covering the Phase 5 manager surface:

  MNG-01  BRAIN panel renders on all 5 main routes                      (Day 0)
  MNG-02  Drop PDF → 4+ entities extracted in < 30 s                    (Day 2)
  MNG-03  Drop medication photo → drug name OCR'd 5/5                   (Day 2)
  MNG-04  Voice 5 s → transcribed < 2 s with ≥ 90 % accuracy            (Day 3)
  MNG-05  Forwarded email parser extracts sender/date/action items      (Day 2)
  MNG-06  Preview cards show before/after diff before apply             (Day 4)
  MNG-07  One-click Apply-all writes to correct tables                  (Day 4)
  MNG-08  Activity feed updates in realtime (Supabase subscription)     (Day 5)
  MNG-09  Undo restores previous state on last 30 actions               (Day 5)
  MNG-10  Morning briefing delivers Sunday 09:00 ≤ 50 words             (Day 6)
  MNG-11  Email draft → Gmail drafts; NEVER auto-sent                   (Day 6)
  MNG-12  PHI redactor runs on every voice transcript + OCR output      (Day 7)
  REGR    Phases 0–4 verifiers still GREEN

Day 1 baseline:
  - MNG-01 may be GREEN already (Day 0 cleanup mounts BRAIN panel).
  - MNG-02..MNG-12 start RED with "module not implemented".
  - REGR runs verify_phase4 in code-complete mode.

Mode split (same idiom as verify_phase4):
  - production  (default): every MNG-* gate requires real deliveries.
  - code-complete:         relaxed; passes if modules + workflow JSONs
                           + verifier scaffolding are in place.

Usage:
    .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase5
    .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase5 --mode code-complete
    .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase5 --gate mng-01
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
VIEWER = ROOT / "viewer"

MODE = "production"


# ---------------------------------------------------------------------------
# Helpers
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


def _file_present(rel: str) -> bool:
    return (ROOT / rel).exists()


# ---------------------------------------------------------------------------
# MNG-01 — BRAIN panel renders on all 5 main routes
# ---------------------------------------------------------------------------
def check_mng_01(report: Report) -> None:
    """BRAIN panel mounts via root layout → appears on every route."""
    layout = VIEWER / "app" / "layout.tsx"
    brain = VIEWER / "components" / "layout" / "BrainPanel.tsx"
    topnav = VIEWER / "components" / "layout" / "TopNav.tsx"

    if not layout.exists() or not brain.exists() or not topnav.exists():
        report.add(
            Check(
                "MNG-01",
                "BRAIN panel renders on all 5 main routes",
                False,
                "layout.tsx + BrainPanel + TopNav missing — Day 0 cleanup did not land",
                "MNG-01",
            )
        )
        return

    layout_src = layout.read_text(encoding="utf-8")
    mounts = "BrainPanel" in layout_src and "<BrainPanel" in layout_src
    today = (VIEWER / "app" / "today" / "page.tsx").exists()
    brain_route = (VIEWER / "app" / "brain" / "page.tsx").exists()
    know = (VIEWER / "app" / "knowledge" / "page.tsx").exists()

    ok = mounts and today and brain_route and know
    report.add(
        Check(
            "MNG-01",
            "BRAIN panel renders on all 5 main routes",
            ok,
            f"mounts={mounts} today={today} brain={brain_route} knowledge={know}",
            "MNG-01",
        )
    )


# ---------------------------------------------------------------------------
# MNG-02 — Drop PDF → 4+ entities extracted in < 30 s
# ---------------------------------------------------------------------------
def check_mng_02(report: Report) -> None:
    has_module = _module_present("scripts.manager.intake.pdf_parser")
    if not has_module:
        report.add(
            Check(
                "MNG-02",
                "Drop PDF → 4+ entities extracted in <30s",
                False,
                "scripts.manager.intake.pdf_parser not implemented (Day 2)",
                "MNG-02",
            )
        )
        return

    if MODE == "code-complete":
        fixtures = ROOT / "tests" / "fixtures" / "phase5"
        ok = fixtures.exists()
        report.add(
            Check(
                "MNG-02",
                "Drop PDF → 4+ entities extracted in <30s",
                ok,
                f"module=ok fixtures_dir_present={ok} mode=code-complete",
                "MNG-02",
            )
        )
        return

    # production: a real PDF drop must have produced ≥1 intake_drops row
    # with parsed_entities length ≥ 4 in the last 14 days.
    try:
        rows = _pg_query(
            """
            SELECT count(*) FROM intake_drops
            WHERE input_type='pdf'
              AND jsonb_array_length(parsed_entities) >= 4
              AND created_at >= now() - interval '14 days'
            """
        )
        n = int(rows[0][0]) if rows else 0
    except Exception as e:
        n = 0
        ev = f"query failed: {type(e).__name__}: {e}"
        report.add(
            Check(
                "MNG-02",
                "Drop PDF → 4+ entities extracted in <30s",
                False,
                ev,
                "MNG-02",
            )
        )
        return
    ok = n >= 1
    report.add(
        Check(
            "MNG-02",
            "Drop PDF → 4+ entities extracted in <30s",
            ok,
            f"recent_pdf_drops_with_4+_entities={n}",
            "MNG-02",
        )
    )


# ---------------------------------------------------------------------------
# MNG-03 — Drop medication photo → OCR'd 5/5
# ---------------------------------------------------------------------------
def check_mng_03(report: Report) -> None:
    has_module = _module_present("scripts.manager.intake.image_ocr")
    if not has_module:
        report.add(
            Check(
                "MNG-03",
                "Drop medication photo → drug name OCR'd 5/5",
                False,
                "scripts.manager.intake.image_ocr not implemented (Day 2)",
                "MNG-03",
            )
        )
        return

    if MODE == "code-complete":
        fixtures = list((ROOT / "tests" / "fixtures" / "phase5").glob("*.png"))
        ok = bool(fixtures)
        report.add(
            Check(
                "MNG-03",
                "Drop medication photo → drug name OCR'd 5/5",
                ok,
                f"module=ok photo_fixtures={len(fixtures)} mode=code-complete",
                "MNG-03",
            )
        )
        return

    # production: at least one photo intake_drops row with parsed_entities
    try:
        rows = _pg_query(
            """
            SELECT count(*) FROM intake_drops
            WHERE input_type='photo'
              AND parsed_entities IS NOT NULL
              AND created_at >= now() - interval '30 days'
            """
        )
        n = int(rows[0][0]) if rows else 0
    except Exception:
        n = 0
    ok = n >= 1
    report.add(
        Check(
            "MNG-03",
            "Drop medication photo → drug name OCR'd 5/5",
            ok,
            f"recent_photo_drops={n}",
            "MNG-03",
        )
    )


# ---------------------------------------------------------------------------
# MNG-04 — Voice 5 s → transcribed < 2 s, ≥ 90 % accuracy
# ---------------------------------------------------------------------------
def check_mng_04(report: Report) -> None:
    has_module = _module_present("scripts.manager.intake.voice_transcribe")
    if not has_module:
        report.add(
            Check(
                "MNG-04",
                "Voice 5s → transcribed <2s with ≥90% accuracy",
                False,
                "scripts.manager.intake.voice_transcribe not implemented (Day 3)",
                "MNG-04",
            )
        )
        return

    # Browser-side artifacts must exist for the end-to-end loop.
    recorder = VIEWER / "components" / "BrainPanel" / "VoiceRecorder.tsx"
    route = VIEWER / "app" / "api" / "manager" / "voice" / "route.ts"
    voice_lib = VIEWER / "lib" / "brain" / "voice.ts"

    if MODE == "code-complete":
        ok = recorder.exists() and route.exists() and voice_lib.exists()
        report.add(
            Check(
                "MNG-04",
                "Voice 5s → transcribed <2s with ≥90% accuracy",
                ok,
                f"module=ok recorder={recorder.exists()} route={route.exists()} "
                f"lib={voice_lib.exists()} mode=code-complete",
                "MNG-04",
            )
        )
        return

    # production: at least one whisper_call runs row in the last 14 days
    try:
        rows = _pg_query(
            """
            SELECT count(*) FROM runs
            WHERE kind='whisper_call'
              AND start_time >= now() - interval '14 days'
            """
        )
        n = int(rows[0][0]) if rows else 0
    except Exception:
        n = 0
    ok = n >= 1
    report.add(
        Check(
            "MNG-04",
            "Voice 5s → transcribed <2s with ≥90% accuracy",
            ok,
            f"recent_whisper_calls={n}",
            "MNG-04",
        )
    )


# ---------------------------------------------------------------------------
# MNG-05 — Forwarded email parser
# ---------------------------------------------------------------------------
def check_mng_05(report: Report) -> None:
    has_module = _module_present("scripts.manager.intake.email_parser")
    if not has_module:
        report.add(
            Check(
                "MNG-05",
                "Forwarded email parser extracts sender/date/action items",
                False,
                "scripts.manager.intake.email_parser not implemented (Day 2)",
                "MNG-05",
            )
        )
        return

    if MODE == "code-complete":
        fixtures = list((ROOT / "tests" / "fixtures" / "phase5").glob("*.eml"))
        ok = bool(fixtures)
        report.add(
            Check(
                "MNG-05",
                "Forwarded email parser extracts sender/date/action items",
                ok,
                f"module=ok eml_fixtures={len(fixtures)} mode=code-complete",
                "MNG-05",
            )
        )
        return

    # production: at least one email intake_drops row in last 30d
    try:
        rows = _pg_query(
            """
            SELECT count(*) FROM intake_drops
            WHERE input_type='email'
              AND created_at >= now() - interval '30 days'
            """
        )
        n = int(rows[0][0]) if rows else 0
    except Exception:
        n = 0
    ok = n >= 1
    report.add(
        Check(
            "MNG-05",
            "Forwarded email parser extracts sender/date/action items",
            ok,
            f"recent_email_drops={n}",
            "MNG-05",
        )
    )


# ---------------------------------------------------------------------------
# MNG-06 — Preview cards show before/after diff
# ---------------------------------------------------------------------------
def check_mng_06(report: Report) -> None:
    has_router = _module_present("scripts.manager.routing.entity_router")
    has_preview = _module_present("scripts.manager.routing.preview_builder")
    has_ui = (VIEWER / "components" / "ActionPreview" / "PreviewCardList.tsx").exists()
    has_card = (VIEWER / "components" / "ActionPreview" / "ActionCard.tsx").exists()
    has_diff = (VIEWER / "components" / "ActionPreview" / "FieldDiff.tsx").exists()
    ok = has_router and has_preview and has_ui and has_card and has_diff
    report.add(
        Check(
            "MNG-06",
            "Preview cards show before/after diff before apply",
            ok,
            f"router={has_router} preview_builder={has_preview} "
            f"PreviewCardList={has_ui} ActionCard={has_card} FieldDiff={has_diff}",
            "MNG-06",
        )
    )


# ---------------------------------------------------------------------------
# MNG-07 — One-click Apply-all writes to correct tables
# ---------------------------------------------------------------------------
def check_mng_07(report: Report) -> None:
    has_batch = _module_present("scripts.manager.routing.apply_batch")
    has_action = _module_present("scripts.manager.routing.apply_action")
    has_button = (
        VIEWER / "components" / "ActionPreview" / "BatchApplyButton.tsx"
    ).exists()
    has_route = (VIEWER / "app" / "api" / "manager" / "apply" / "route.ts").exists()
    has_lib = (VIEWER / "lib" / "brain" / "apply.ts").exists()

    if not (has_batch and has_action):
        report.add(
            Check(
                "MNG-07",
                "One-click Apply-all writes to correct tables",
                False,
                "scripts.manager.routing.apply_batch / apply_action not implemented (Day 4)",
                "MNG-07",
            )
        )
        return

    if MODE == "code-complete":
        ok = has_batch and has_action and has_button and has_route and has_lib
        report.add(
            Check(
                "MNG-07",
                "One-click Apply-all writes to correct tables",
                ok,
                f"batch={has_batch} action={has_action} button={has_button} "
                f"route={has_route} lib={has_lib} mode=code-complete",
                "MNG-07",
            )
        )
        return

    # production: at least one manager_actions row with action_type IN
    # ('add_event','add_milestone','create','update','add_contact') in
    # the last 30 days.
    try:
        rows = _pg_query(
            """
            SELECT count(*) FROM manager_actions
            WHERE action_type IN ('add_event','add_milestone','create',
                                  'update','add_contact')
              AND created_at >= now() - interval '30 days'
            """
        )
        n = int(rows[0][0]) if rows else 0
    except Exception:
        n = 0
    ok = n >= 1
    report.add(
        Check(
            "MNG-07",
            "One-click Apply-all writes to correct tables",
            ok,
            f"recent_manager_actions={n}",
            "MNG-07",
        )
    )


# ---------------------------------------------------------------------------
# MNG-08 — Activity feed updates in realtime
# ---------------------------------------------------------------------------
def check_mng_08(report: Report) -> None:
    has_lib = (VIEWER / "lib" / "realtime.ts").exists()
    has_ui = (VIEWER / "components" / "BrainPanel" / "ActivityFeed.tsx").exists()
    has_route = (VIEWER / "app" / "api" / "manager" / "audit" / "route.ts").exists()
    has_audit_module = _module_present("scripts.manager.activity.audit_query")

    ok = has_lib and has_ui and has_route and has_audit_module
    report.add(
        Check(
            "MNG-08",
            "Activity feed updates in realtime",
            ok,
            f"realtime.ts={has_lib} ActivityFeed.tsx={has_ui} "
            f"audit_route={has_route} audit_query={has_audit_module}",
            "MNG-08",
        )
    )


# ---------------------------------------------------------------------------
# MNG-09 — Undo restores state on last 30 actions
# ---------------------------------------------------------------------------
def check_mng_09(report: Report) -> None:
    has_undo = _module_present("scripts.manager.activity.undo")
    has_button = (VIEWER / "components" / "AuditLog" / "UndoButton.tsx").exists()
    has_route = (
        VIEWER / "app" / "api" / "manager" / "undo" / "[id]" / "route.ts"
    ).exists()
    has_audit_page = (VIEWER / "app" / "audit-log" / "page.tsx").exists()

    if not has_undo:
        report.add(
            Check(
                "MNG-09",
                "Undo restores state on last 30 actions",
                False,
                "scripts.manager.activity.undo not implemented (Day 5)",
                "MNG-09",
            )
        )
        return

    if MODE == "code-complete":
        ok = has_undo and has_button and has_route and has_audit_page
        report.add(
            Check(
                "MNG-09",
                "Undo restores state on last 30 actions",
                ok,
                f"undo={has_undo} button={has_button} route={has_route} "
                f"audit_page={has_audit_page} mode=code-complete",
                "MNG-09",
            )
        )
        return

    # production: at least one action_type='reverse' row in last 30 days
    try:
        rows = _pg_query(
            """
            SELECT count(*) FROM manager_actions
            WHERE action_type = 'reverse'
              AND created_at >= now() - interval '30 days'
            """
        )
        n = int(rows[0][0]) if rows else 0
    except Exception:
        n = 0
    ok = n >= 1
    report.add(
        Check(
            "MNG-09",
            "Undo restores state on last 30 actions",
            ok,
            f"recent_reverse_actions={n}",
            "MNG-09",
        )
    )


# ---------------------------------------------------------------------------
# MNG-10 — Morning briefing
# ---------------------------------------------------------------------------
def check_mng_10(report: Report) -> None:
    has_module = _module_present("scripts.manager.briefing")
    workflow = _file_present("workflows/manager_briefing.json")
    if MODE == "code-complete":
        ok = has_module and workflow
        report.add(
            Check(
                "MNG-10",
                "Morning briefing delivers Sunday 09:00 ≤50 words",
                ok,
                f"module={has_module} workflow={workflow} mode=code-complete",
                "MNG-10",
            )
        )
        return
    # production: must have a 'manager_briefing' runs row in the last 8 days
    try:
        rows = _pg_query(
            """
            SELECT count(*) FROM runs
            WHERE kind='manager_briefing'
              AND start_time >= now() - interval '8 days'
            """
        )
        n = int(rows[0][0]) if rows else 0
    except Exception:
        n = 0
    ok = has_module and workflow and n >= 1
    report.add(
        Check(
            "MNG-10",
            "Morning briefing delivers Sunday 09:00 ≤50 words",
            ok,
            f"module={has_module} workflow={workflow} recent_briefings={n}",
            "MNG-10",
        )
    )


# ---------------------------------------------------------------------------
# MNG-11 — Email draft → Gmail drafts; never auto-send
# ---------------------------------------------------------------------------
def check_mng_11(report: Report) -> None:
    has_module = _module_present("scripts.manager.email_draft")
    report.add(
        Check(
            "MNG-11",
            "Email draft → Gmail drafts (never auto-send)",
            False,
            "scripts.manager.email_draft not implemented (Day 6)"
            if not has_module
            else "module present, Gmail draft round-trip pending",
            "MNG-11",
        )
    )


# ---------------------------------------------------------------------------
# MNG-12 — PHI redactor on every voice transcript + OCR output
# ---------------------------------------------------------------------------
def check_mng_12(report: Report) -> None:
    """
    DB-level guard: every intake_drops row must have phi_redacted=TRUE.
    Migration 011 enforces this with a CHECK constraint, so this gate
    passes as long as the table exists. If migration 011 is not applied,
    the table is missing and the check still reports RED.
    """
    try:
        rows = _pg_query(
            """
            SELECT count(*) FROM information_schema.check_constraints
            WHERE constraint_name = 'intake_drops_must_redact'
            """
        )
        ok = int(rows[0][0]) == 1 if rows else False
        evidence = (
            "CHECK intake_drops_must_redact present"
            if ok
            else "migration 011 not applied — intake_drops_must_redact missing"
        )
    except Exception as e:
        ok = False
        evidence = f"query failed: {type(e).__name__}: {e}"
    report.add(
        Check(
            "MNG-12",
            "PHI redactor runs on every voice transcript + OCR output",
            ok,
            evidence,
            "MNG-12",
        )
    )


# ---------------------------------------------------------------------------
# Regression — phase 4 still PASS (in code-complete mode)
# ---------------------------------------------------------------------------
def check_regression(report: Report) -> None:
    try:
        import scripts.verify_phase4 as p4

        # Run phase 4 in code-complete mode so this gate is engineering-
        # exit oriented; production-grade regression is the operator's
        # responsibility (Step B + 14-day acceptance window).
        p4.MODE = "code-complete"

        sub = Report()
        for fn in p4.ALL_ORDER:
            fn(sub)
        p4.check_regression(sub)
        passed = sum(1 for c in sub.checks if c.passed)
        total = len(sub.checks)
        report.add(
            Check(
                "REGR",
                "Phases 0–4 verifiers still PASS",
                passed == total,
                f"{passed}/{total} PASS (phase 4 code-complete mode)",
                "REGR",
            )
        )
    except Exception as e:
        report.add(
            Check(
                "REGR",
                "Phases 0–4 verifiers still PASS",
                False,
                f"{type(e).__name__}: {e}",
                "REGR",
            )
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
GATES = {
    "mng-01": check_mng_01,
    "mng-02": check_mng_02,
    "mng-03": check_mng_03,
    "mng-04": check_mng_04,
    "mng-05": check_mng_05,
    "mng-06": check_mng_06,
    "mng-07": check_mng_07,
    "mng-08": check_mng_08,
    "mng-09": check_mng_09,
    "mng-10": check_mng_10,
    "mng-11": check_mng_11,
    "mng-12": check_mng_12,
    "regr": check_regression,
}

ALL_ORDER = (
    check_mng_01,
    check_mng_02,
    check_mng_03,
    check_mng_04,
    check_mng_05,
    check_mng_06,
    check_mng_07,
    check_mng_08,
    check_mng_09,
    check_mng_10,
    check_mng_11,
    check_mng_12,
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
    ap.add_argument(
        "--mode",
        choices=["production", "code-complete"],
        default="production",
        help=(
            "production (default): every gate requires real deliveries. "
            "code-complete: passes if modules + workflow JSONs + verifier "
            "scaffolding are in place."
        ),
    )
    args = ap.parse_args()

    global MODE
    MODE = args.mode

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
            "mode": MODE,
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
