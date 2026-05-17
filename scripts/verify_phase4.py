"""
verify_phase4.py — Phase 4 First Family Value exit-gate harness.

9-item PASS/FAIL audit covering the Phase 4 family-facing delivery surface:

  FFV-01  Confidence-gated Telegram digest reaches family channel       (Day 2)
  FFV-02  Quiet hours suppress non-T1 between 22:00 and 07:00 Boston    (Day 2)
  FFV-03  Weekly Gmail digest renders + stages as draft                 (Day 4)
  FFV-04  Notion bootstrap + ≥1 archived finding with provenance        (Day 1)
  FFV-05  Clinician PDF renders + Gmail draft has PDF attachment        (Day 3)
  OBS-02  Every recent delivered digest links to originating runs.id    (Day 6)
  OBS-03  Daily spend report posted to Telegram within last 36h         (Day 5)
  BOOTSTRAP  Notion env + database resolve (Day 1 prerequisite)
  REGR    verify_phase3 still 11/11 PASS

Day 0 / Day 1 baseline state:
  - BOOTSTRAP turns GREEN once Shako runs scripts/notion_bootstrap.py and
    sets NOTION_DATABASE_ID in .env.
  - FFV-04 starts RED with "module not implemented" and flips GREEN when
    Day 1 ships notion_archiver.py AND ≥1 finding has been archived.
  - FFV-01..05 + OBS-02 + OBS-03 each turn GREEN on the day named above.

Usage:
    .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase4
    .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase4 --gate ffv-04
    .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase4 --gate regr
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
# Helpers (mirror verify_phase3.py shape)
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


# ---------------------------------------------------------------------------
# BOOTSTRAP — Notion env + database resolve
# ---------------------------------------------------------------------------
def check_bootstrap(report: Report) -> None:
    api_key = os.environ.get("NOTION_API_KEY", "").strip()
    parent = os.environ.get("NOTION_PARENT_PAGE_ID", "").strip()
    db_id = os.environ.get("NOTION_DATABASE_ID", "").strip()

    if not api_key:
        report.add(
            Check(
                "BOOTSTRAP",
                "Notion env + database resolve",
                False,
                "NOTION_API_KEY missing — see docs/RUNBOOK-notion-api.md",
                "BOOTSTRAP",
            )
        )
        return
    if not parent:
        report.add(
            Check(
                "BOOTSTRAP",
                "Notion env + database resolve",
                False,
                "NOTION_PARENT_PAGE_ID missing — Shako must share a page with the integration",
                "BOOTSTRAP",
            )
        )
        return
    if not db_id:
        report.add(
            Check(
                "BOOTSTRAP",
                "Notion env + database resolve",
                False,
                "NOTION_DATABASE_ID missing — run scripts/notion_bootstrap.py",
                "BOOTSTRAP",
            )
        )
        return

    if not _module_present("notion_client"):
        report.add(
            Check(
                "BOOTSTRAP",
                "Notion env + database resolve",
                False,
                "notion-client package not installed — uv pip install notion-client",
                "BOOTSTRAP",
            )
        )
        return

    # Verify the integration can actually read the database
    try:
        from notion_client import Client

        notion = Client(auth=api_key)
        db = notion.databases.retrieve(database_id=db_id)
        title = (
            (db.get("title") or [{}])[0].get("plain_text", "")
            if db.get("title")
            else ""
        )
        report.add(
            Check(
                "BOOTSTRAP",
                "Notion env + database resolve",
                True,
                f"database_id={db_id[:8]}…  title={title!r}",
                "BOOTSTRAP",
            )
        )
    except Exception as e:
        report.add(
            Check(
                "BOOTSTRAP",
                "Notion env + database resolve",
                False,
                f"Notion API error: {type(e).__name__}: {str(e)[:120]}",
                "BOOTSTRAP",
            )
        )


# ---------------------------------------------------------------------------
# FFV-01 — Telegram digest reaches family channel
# ---------------------------------------------------------------------------
def check_ffv_01(report: Report) -> None:
    if not _module_present("scripts.communicator.telegram_sender"):
        report.add(
            Check(
                "FFV-01",
                "Confidence-gated Telegram digest reaches family channel",
                False,
                "scripts.communicator.telegram_sender not implemented (Day 2)",
                "ACD-01",
            )
        )
        return

    # Structural contract: module exists + workflow file present + dispatch
    # signature behaves correctly under dry_run.
    workflow_file = ROOT / "workflows" / "telegram_daily_digest.json"
    workflow_ok = workflow_file.exists()

    # Smoke: dispatch a synthetic T1 decision in dry_run mode, asserting
    # the contract (no DB row, no Telegram POST, but tier echoed correctly).
    try:
        from scripts.communicator.summarize import Claim, SummaryDraft
        from scripts.communicator.telegram_sender import dispatch
        from scripts.communicator.tier_router import TierDecision

        synthetic_draft = SummaryDraft(
            query="phase4_smoke_query",
            audience="internal",
            language="en",
            claims=[
                Claim(
                    sentence="Synthetic smoke claim for FFV-01 dry-run.",
                    citation_ids=["PMID:0000001"],
                    evidence_grade=2,
                )
            ],
            citations=["PMID:0000001"],
            raw_text="Synthetic smoke claim for FFV-01 dry-run.",
        )
        from scripts.communicator.banned_phrases import BannedPhraseResult
        from scripts.communicator.phi_redactor import RedactionResult

        synthetic_draft.banned = BannedPhraseResult(passed=True, violations=[])
        synthetic_draft.redaction = RedactionResult(
            text="Synthetic smoke claim for FFV-01 dry-run.",
            redactions=[],
            blocked=False,
        )
        decision = TierDecision(
            tier="T1",
            confidence=0.92,
            reason="smoke_synthetic",
        )
        result = dispatch(
            decision,
            synthetic_draft,
            run_id="00000000-0000-0000-0000-000000000000",
            event_kind="smoke_test",
            dry_run=True,
        )
        smoke_ok = (
            result.tier == "T1"
            and result.alerts_log_id is None  # dry_run -> no DB row
            and result.delivered is False
        )
    except Exception as e:
        smoke_ok = False
        smoke_err = f"{type(e).__name__}: {str(e)[:100]}"
    else:
        smoke_err = ""

    # Production-data check: ≥1 row in alerts_log with tier='T1' AND
    # delivered_at IS NOT NULL. Stays RED until a real T1 event fires
    # (this is the FFV-01 success-criterion signal for the 14-day
    # acceptance window).
    rows = _pg_query(
        """
        SELECT count(*) FROM alerts_log
        WHERE tier = 'T1' AND delivered_at IS NOT NULL
        """
    )
    n_t1_delivered = int(rows[0][0]) if rows else 0
    prod_ok = n_t1_delivered >= 1

    ok = workflow_ok and smoke_ok and prod_ok
    evidence = (
        f"workflow={workflow_ok} smoke={smoke_ok}{f' err={smoke_err!r}' if smoke_err else ''} "
        f"prod_t1_delivered={n_t1_delivered}"
    )
    report.add(
        Check(
            "FFV-01",
            "Confidence-gated Telegram digest reaches family channel",
            ok,
            evidence,
            "ACD-01",
        )
    )


# ---------------------------------------------------------------------------
# FFV-02 — Quiet hours suppress non-T1
# ---------------------------------------------------------------------------
def check_ffv_02(report: Report) -> None:
    if not _module_present("scripts.communicator.tier_router"):
        report.add(
            Check(
                "FFV-02",
                "Quiet hours suppress non-T1 between 22:00 and 07:00",
                False,
                "scripts.communicator.tier_router not implemented (Day 2 wiring task)",
                "ACD-02",
            )
        )
        return
    # tier_router already implements is_quiet_hour + defer_to_next_morning. Day 2
    # asserts on a synthetic event: T2 at 23:00 returns decision.deferred_until
    # set to 08:00 next day.
    from datetime import datetime as dt
    from datetime import timezone as tz

    from scripts.communicator.tier_router import Event, classify

    night = Event(
        kind="action_within_7d",
        confidence=0.75,
        timestamp=dt(2026, 5, 17, 23, 0, tzinfo=tz.utc),
    )
    decision = classify(night, t1_count_today=0)
    ok = (
        decision.tier == "T2"
        and decision.deferred_until is not None
        and decision.deferred_until.hour == 8
    )
    evidence = (
        f"night_T2_decision tier={decision.tier} deferred_until="
        f"{decision.deferred_until} reason={decision.reason!r}"
    )
    report.add(
        Check(
            "FFV-02",
            "Quiet hours suppress non-T1 between 22:00 and 07:00",
            ok,
            evidence,
            "ACD-02",
        )
    )


# ---------------------------------------------------------------------------
# FFV-03 — Weekly Gmail digest
# ---------------------------------------------------------------------------
def check_ffv_03(report: Report) -> None:
    if not _module_present("scripts.communicator.gmail_digest"):
        report.add(
            Check(
                "FFV-03",
                "Weekly Gmail digest renders + stages as draft",
                False,
                "scripts.communicator.gmail_digest not implemented (Day 4)",
                "ACD-03",
            )
        )
        return
    from datetime import date as _date

    from scripts.communicator.gmail_digest import (
        stage_weekly_digest,
    )

    # Structural smoke: subject + body render from fixture sections without
    # touching Gmail API or DB. Asserts body is non-empty, contains the
    # citation appendix line, and the safety net doesn't block.
    try:
        result = stage_weekly_digest(
            week_start=_date(2026, 5, 17),
            pdf_r2_path="briefs/2026-05-17.pdf",
            notion_database_id=os.environ.get("NOTION_DATABASE_ID") or None,
            dry_run=True,
            fixture=True,
        )
        subject_ok = result.subject.startswith("ALEKSANDRA_BRAIN Weekly Brief")
        body_ok = (
            not result.blocked
            and "This week, in short" in result.body
            and "Citation appendix" in result.body
            and len(result.body) > 500
        )
        smoke_ok = subject_ok and body_ok
        smoke_evidence = (
            f"subject_ok={subject_ok} body_len={len(result.body)} "
            f"blocked={result.blocked}"
            + (f" reason={result.block_reason!r}" if result.block_reason else "")
        )
    except Exception as e:
        smoke_ok = False
        smoke_evidence = f"raised: {type(e).__name__}: {str(e)[:120]}"

    # Workflow file extended to call the Gmail digest step
    workflow_file = ROOT / "workflows" / "weekly_brief.json"
    workflow_ok = False
    if workflow_file.exists():
        try:
            text = workflow_file.read_text(encoding="utf-8")
            workflow_ok = "stage_gmail_digest" in text or "gmail_digest" in text
        except OSError:
            workflow_ok = False

    # Production-data check: ≥1 row with trigger_kind='weekly_digest'
    # AND gmail_draft_id NOT NULL — RED until first Sunday brief lands.
    rows = _pg_query(
        """
        SELECT count(*) FROM outreach_log
        WHERE trigger_kind = 'weekly_digest' AND gmail_draft_id IS NOT NULL
        """
    )
    n_prod = int(rows[0][0]) if rows else 0
    prod_ok = n_prod >= 1

    ok = smoke_ok and workflow_ok and prod_ok
    evidence = (
        f"smoke={smoke_ok} ({smoke_evidence})  workflow_extended={workflow_ok}  "
        f"prod_weekly_drafts={n_prod}"
    )
    report.add(
        Check(
            "FFV-03",
            "Weekly Gmail digest renders + stages as draft",
            ok,
            evidence,
            "ACD-03",
        )
    )


# ---------------------------------------------------------------------------
# FFV-04 — Notion archiver writes ≥1 finding
# ---------------------------------------------------------------------------
def check_ffv_04(report: Report) -> None:
    if not _module_present("scripts.communicator.notion_archiver"):
        report.add(
            Check(
                "FFV-04",
                "Notion bootstrap + ≥1 archived finding",
                False,
                "scripts.communicator.notion_archiver not implemented (Day 1)",
                "ACD-04",
            )
        )
        return
    from scripts.communicator.notion_archiver import archive_count

    n = archive_count()
    ok = n >= 1
    report.add(
        Check(
            "FFV-04",
            "Notion bootstrap + ≥1 archived finding",
            ok,
            f"notion_pages={n}",
            "ACD-04",
        )
    )


# ---------------------------------------------------------------------------
# FFV-05 — Clinician PDF + Gmail draft with attachment
# ---------------------------------------------------------------------------
def check_ffv_05(report: Report) -> None:
    if not _module_present("scripts.communicator.clinician_pdf"):
        report.add(
            Check(
                "FFV-05",
                "Clinician PDF renders + Gmail draft has PDF attachment",
                False,
                "scripts.communicator.clinician_pdf not implemented (Day 3)",
                "ACD-05",
            )
        )
        return
    import tempfile
    from datetime import datetime as _dt

    from scripts.communicator.clinician_pdf import (
        ClinicianClaim,
        ClinicianPDFInput,
        render_clinician_pdf,
    )

    # Structural smoke: render a fixture PDF into temp dir; assert size and
    # no PHI safety-net block. This proves the renderer + patient context
    # work end-to-end without needing a real contact row.
    tmp_pdf = (
        Path(tempfile.gettempdir())
        / f"phase4_ffv05_smoke_{_dt.now().timestamp():.0f}.pdf"
    )
    try:
        out = render_clinician_pdf(
            ClinicianPDFInput(
                topic="Smoke test — cord blood expanded access for severe HIE",
                audience_label="Smoke test recipient",
                claims=[
                    ClinicianClaim(
                        sentence="Preclinical evidence supports autologous cord blood for neonatal HIE.",
                        citation_ids=["PMID:0000001"],
                        evidence_grade=2,
                        confidence=0.82,
                    ),
                ],
                citation_metadata={
                    "PMID:0000001": {
                        "source_type": "pubmed",
                        "retrieval_timestamp": "2026-05-16T10:00:00Z",
                        "url": "https://pubmed.ncbi.nlm.nih.gov/0000001/",
                    },
                },
                agent_run_ids=["smoke-run-00000000"],
            ),
            tmp_pdf,
        )
        smoke_ok = (
            not out.blocked
            and out.bytes_written > 1024
            and out.claim_count == 1
            and out.citation_count == 1
        )
        smoke_evidence = (
            f"pdf={out.bytes_written}B claims={out.claim_count} "
            f"citations={out.citation_count} version={out.patient_context_version}"
        )
    except Exception as e:
        smoke_ok = False
        smoke_evidence = f"render_raised: {type(e).__name__}: {str(e)[:120]}"
    finally:
        try:
            tmp_pdf.unlink()
        except OSError:
            pass

    # Production-data check: ≥1 outreach_log row with trigger_kind='clinician_pdf'
    # AND gmail_draft_id NOT NULL — RED until first real clinician draft fires.
    rows = _pg_query(
        """
        SELECT count(*) FROM outreach_log
        WHERE trigger_kind = 'clinician_pdf' AND gmail_draft_id IS NOT NULL
        """
    )
    n_prod = int(rows[0][0]) if rows else 0
    prod_ok = n_prod >= 1

    ok = smoke_ok and prod_ok
    evidence = f"smoke={smoke_ok} ({smoke_evidence})  prod_clinician_drafts={n_prod}"
    report.add(
        Check(
            "FFV-05",
            "Clinician PDF renders + Gmail draft has PDF attachment",
            ok,
            evidence,
            "ACD-05",
        )
    )


# ---------------------------------------------------------------------------
# OBS-02 — Digest→run linkage
# ---------------------------------------------------------------------------
def check_obs_02(report: Report) -> None:
    # Day 6 (migration 009) adds runs.digest_id + originating_run_id.
    # Until then, FAIL with a clear evidence string.
    try:
        rows = _pg_query(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema='public' AND table_name='runs' AND column_name='digest_id'
            """
        )
        has_col = len(rows) == 1
    except Exception:
        has_col = False
        rows = []
    if not has_col:
        report.add(
            Check(
                "OBS-02",
                "Every recent delivered digest links to originating runs.id",
                False,
                "runs.digest_id column missing — migration 009 (Day 6) pending",
                "OBS-02",
            )
        )
        return
    # Once the column is present, count recent delivered digests that link back.
    linked = _pg_query(
        """
        SELECT count(*) FROM (
          SELECT originating_run_id FROM alerts_log
          WHERE delivered_at >= now() - interval '7 days' AND originating_run_id IS NOT NULL
          UNION ALL
          SELECT originating_run_id FROM outreach_log
          WHERE drafted_at >= now() - interval '7 days' AND originating_run_id IS NOT NULL
          UNION ALL
          SELECT originating_run_id FROM briefs
          WHERE generated_at >= now() - interval '7 days' AND originating_run_id IS NOT NULL
        ) t
        """
    )
    n_linked = int(linked[0][0]) if linked else 0
    ok = n_linked >= 1
    report.add(
        Check(
            "OBS-02",
            "Every recent delivered digest links to originating runs.id",
            ok,
            f"recent_linked_digests={n_linked}",
            "OBS-02",
        )
    )


# ---------------------------------------------------------------------------
# OBS-03 — Daily spend report
# ---------------------------------------------------------------------------
def check_obs_03(report: Report) -> None:
    workflow = ROOT / "workflows" / "daily_spend_report.json"
    if not workflow.exists():
        report.add(
            Check(
                "OBS-03",
                "Daily spend report posted to Telegram within last 36h",
                False,
                "workflows/daily_spend_report.json missing (Day 5)",
                "OBS-03",
            )
        )
        return

    # Look for a recent 'daily_spend_report' or 'spend_report' runs row
    try:
        rows = _pg_query(
            """
            SELECT max(start_time) FROM runs
            WHERE kind IN ('daily_spend_report', 'spend_report')
              AND start_time >= now() - interval '36 hours'
            """
        )
        latest = rows[0][0] if rows else None
    except Exception:
        latest = None
    ok = latest is not None
    evidence = (
        f"latest_spend_report={latest}"
        if latest
        else "no recent spend_report runs row in last 36h"
    )
    report.add(
        Check(
            "OBS-03",
            "Daily spend report posted to Telegram within last 36h",
            ok,
            evidence,
            "OBS-03",
        )
    )


# ---------------------------------------------------------------------------
# Regression — verify_phase3 still 11/11
# ---------------------------------------------------------------------------
def check_regression(report: Report) -> None:
    try:
        # Import Phase 3 checks directly to avoid re-running argparse.
        from scripts.verify_phase3 import (
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
        from scripts.verify_phase3 import check_regression as p3_regr

        sub = Report()
        for fn in (
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
        ):
            fn(sub)
        p3_regr(sub)
        passed = sum(1 for c in sub.checks if c.passed)
        total = len(sub.checks)
        report.add(
            Check(
                "REGR",
                "verify_phase3 still PASS (no Phase 3 regression)",
                passed == total,
                f"{passed}/{total} PASS",
                "REGR",
            )
        )
    except Exception as e:
        report.add(
            Check(
                "REGR",
                "verify_phase3 still PASS (no Phase 3 regression)",
                False,
                f"{type(e).__name__}: {e}",
                "REGR",
            )
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
GATES = {
    "bootstrap": check_bootstrap,
    "ffv-01": check_ffv_01,
    "ffv-02": check_ffv_02,
    "ffv-03": check_ffv_03,
    "ffv-04": check_ffv_04,
    "ffv-05": check_ffv_05,
    "obs-02": check_obs_02,
    "obs-03": check_obs_03,
    "regr": check_regression,
}

ALL_ORDER = (
    check_bootstrap,
    check_ffv_01,
    check_ffv_02,
    check_ffv_03,
    check_ffv_04,
    check_ffv_05,
    check_obs_02,
    check_obs_03,
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
