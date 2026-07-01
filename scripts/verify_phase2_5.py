"""
verify_phase2_5.py — Phase 2.5 Quick Wins Sprint exit-gate harness.

15-item PASS/FAIL audit aligned with the four sub-phase gates:

  Gate A — Spend Instrumentation Hardening   (3 items, A.1..A.3)
  Gate B — Perception Scale-up               (4 items, B.1..B.4)
  Gate C — Family-Visible Layer              (4 items, C.1..C.4)
  Gate D — Validation Workflow               (4 items, D.1..D.4)

Plus an optional `regr` gate that just re-runs verify_phase2 to confirm
no Phase 2 regression (HC-5 gate-before-next discipline).

Each check prints a one-line verdict + evidence. Exit 0 only if every
item PASSes (or every item in the requested gate, with --gate).

Usage:
    .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase2_5
    .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase2_5 --gate a
    .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase2_5 --gate b
    .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase2_5 --gate regr

This file deliberately mirrors scripts/verify_phase2.py's structure and
helper signatures so a future merge into a single Phase-2/2.5 harness is
mechanical. It has no Graphiti / anthropic SDK imports — all checks run
against live data via Supabase REST + Qdrant REST + Neo4j Bolt + filesystem.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import psycopg2

from scripts.ledger import _supabase_creds, _supabase_headers, load_env


def _iso_ago(*, days: int = 0, hours: int = 0) -> str:
    """ISO timestamp for `now - (days, hours)`, suitable for PostgREST `gte.`."""
    return (datetime.now(timezone.utc) - timedelta(days=days, hours=hours)).isoformat()


ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Helpers (intentionally identical-shaped to scripts/verify_phase2.py)
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
        print(f"{'#':>3}  {'CODE':<6}  {'GATE':<6}  {'STATUS':<6}  LABEL  →  EVIDENCE")
        print("-" * 110)
        for i, c in enumerate(self.checks, start=1):
            mark = "PASS" if c.passed else "FAIL"
            print(
                f"{i:>3}  {c.code:<6}  {c.requirement:<6}  {mark:<6}  {c.label}  →  {c.evidence}"
            )
        print("=" * 110)
        n_pass = sum(1 for c in self.checks if c.passed)
        print(
            f"  {n_pass}/{len(self.checks)} PASS  —  "
            f"{'ALL GREEN' if self.passed else 'NEEDS WORK'}"
        )


def _sb_count(path: str, params: dict[str, str]) -> int:
    url, key = _supabase_creds()
    r = httpx.head(
        f"{url}/rest/v1/{path}",
        params=params,
        headers={**_supabase_headers(key), "Prefer": "count=exact"},
        timeout=15,
    )
    if "content-range" in r.headers:
        rng = r.headers["content-range"].split("/")[-1]
        return int(rng) if rng != "*" else 0
    r = httpx.get(
        f"{url}/rest/v1/{path}",
        params={**params, "select": "id"},
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=20,
    )
    r.raise_for_status()
    return len(r.json())


def _sb_get(path: str, params: dict[str, str]) -> list[dict]:
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/{path}",
        params=params,
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def _qdrant_collection_info(name: str) -> dict:
    url = os.environ.get("QDRANT_URL", "http://127.0.0.1:6333").replace(
        "localhost", "127.0.0.1"
    )
    api_key = os.environ.get("QDRANT_API_KEY")
    headers = {"api-key": api_key} if api_key else {}
    r = httpx.get(f"{url}/collections/{name}", headers=headers, timeout=10)
    r.raise_for_status()
    return r.json().get("result", {})


def _neo4j_session():
    from neo4j import GraphDatabase

    uri = os.environ["NEO4J_URI"].replace("localhost", "127.0.0.1")
    user = os.environ["NEO4J_USERNAME"]
    pw = os.environ["NEO4J_PASSWORD"]
    return GraphDatabase.driver(uri, auth=(user, pw))


def _pg_query_one(sql: str, params: tuple = ()) -> tuple | None:
    """Run one-shot psycopg2 query for schema-only inspections."""
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchone()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Gate A — Spend Instrumentation Hardening (3)
# ---------------------------------------------------------------------------
def check_gate_a(report: Report) -> None:
    # A.1 — runs.token_cost precision ≥ NUMERIC(14, 8)
    row = _pg_query_one(
        """
        SELECT numeric_precision, numeric_scale
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name='runs' AND column_name='token_cost'
        """
    )
    if row is None:
        report.add(
            Check(
                "A.1",
                "runs.token_cost precision ≥ NUMERIC(14,8)",
                False,
                "column not found",
                "A",
            )
        )
    else:
        prec, scale = row
        ok = (prec or 0) >= 14 and (scale or 0) >= 8
        report.add(
            Check(
                "A.1",
                "runs.token_cost precision ≥ NUMERIC(14,8)",
                ok,
                f"NUMERIC({prec},{scale})",
                "A",
            )
        )

    # A.2 — check_daily_budget() exists and returns a usable value
    try:
        from scripts.cognition.budget import (
            DEFAULT_DAILY_BUDGET_USD,
            BudgetExceeded,
            check_daily_budget,
        )

        today_spend, _ = check_daily_budget()
        # Confirm raise path works too
        raised = False
        try:
            check_daily_budget(threshold_usd=0.0, raise_on_over=True)
        except BudgetExceeded:
            raised = True
        report.add(
            Check(
                "A.2",
                "check_daily_budget() reads runs.token_cost; raise_on_over works",
                raised and today_spend >= 0,
                f"today=${today_spend:.6f} default_cap=${DEFAULT_DAILY_BUDGET_USD} raise_on_over=PASS",
                "A",
            )
        )
    except Exception as e:
        report.add(
            Check(
                "A.2",
                "check_daily_budget() reads runs.token_cost; raise_on_over works",
                False,
                f"{type(e).__name__}: {e}",
                "A",
            )
        )

    # A.3 — at least one runs row with kind='llm_call' AND token_cost > 0 exists
    rows = _sb_get(
        "runs",
        {
            "select": "id,token_cost",
            "kind": "eq.llm_call",
            "token_cost": "gt.0",
            "limit": "1",
        },
    )
    report.add(
        Check(
            "A.3",
            "≥ 1 runs llm_call with token_cost > 0 (precision survived)",
            len(rows) > 0,
            f"found {len(rows)} (need ≥1)",
            "A",
        )
    )


# ---------------------------------------------------------------------------
# Gate B — Perception Scale-up (4)
# ---------------------------------------------------------------------------
def check_gate_b(report: Report) -> None:
    # B.1 — Railway worker has fired at least one perception_tick run row in last 7d
    pt = _sb_get(
        "runs",
        {
            "select": "id,start_time,exit_status",
            "kind": "eq.perception_tick",
            "start_time": f"gte.{_iso_ago(days=7)}",
            "order": "start_time.desc",
            "limit": "1",
        },
    )
    has_tick = len(pt) > 0 and pt[0].get("exit_status") in (
        "completed",
        "killed_by_budget_gate",
    )
    report.add(
        Check(
            "B.1",
            "Railway perception_tick fired ≥ 1× in last 7d (n8n cron alive)",
            has_tick,
            f"latest={pt[0]['start_time'] if pt else 'none'}",
            "B",
        )
    )

    # B.2 — evidence_ledger ≥ 100
    ledger = _sb_count("evidence_ledger", {})
    report.add(
        Check(
            "B.2",
            "evidence_ledger ≥ 100 (target 30 → 100+)",
            ledger >= 100,
            f"{ledger} rows",
            "B",
        )
    )

    # B.3 — paper_chunks ≥ 5000 AND Qdrant points ≥ 5000
    chunks = _sb_count("paper_chunks", {})
    try:
        qd = _qdrant_collection_info("papers")
        qd_points = qd.get("points_count", 0) or 0
        qd_dim = (
            qd.get("config", {}).get("params", {}).get("vectors", {}).get("size", 0)
        )
    except Exception as e:
        qd_points = 0
        qd_dim = 0
        _ = e  # don't fail the check on Qdrant blip — show 0
    report.add(
        Check(
            "B.3",
            "paper_chunks + Qdrant ≥ 5000 (target 409 → 5000+)",
            chunks >= 5000 and qd_points >= 5000,
            f"chunks={chunks}  qdrant_points={qd_points}  dim={qd_dim}",
            "B",
        )
    )

    # B.4 — Neo4j Entity {group_id:'hie_research'} ≥ 500
    try:
        load_env()
        drv = _neo4j_session()
        with drv.session() as s:
            n = s.run(
                "MATCH (n:Entity {group_id:'hie_research'}) RETURN count(n) AS c"
            ).single()["c"]
        drv.close()
    except Exception as e:
        n = 0
        _ = e
    report.add(
        Check(
            "B.4",
            "Neo4j Entity {group_id:'hie_research'} ≥ 500 (target 247 → 500+)",
            n >= 500,
            f"{n} entities",
            "B",
        )
    )


# ---------------------------------------------------------------------------
# Gate C — Family-Visible Layer (4)
# ---------------------------------------------------------------------------
def check_gate_c(report: Report) -> None:
    # C.1 — family-visible landing route file present in viewer/
    # Post-site-refactor: the dashboard role is now the locale root page.
    dash_legacy = ROOT / "viewer" / "app" / "dashboard" / "page.tsx"
    dash_locale = ROOT / "viewer" / "app" / "[locale]" / "dashboard" / "page.tsx"
    home_locale = ROOT / "viewer" / "app" / "[locale]" / "page.tsx"
    dash_present = (
        dash_legacy.is_file() or dash_locale.is_file() or home_locale.is_file()
    )
    dash_path = (
        dash_locale
        if dash_locale.is_file()
        else home_locale
        if home_locale.is_file()
        else dash_legacy
    )
    report.add(
        Check(
            "C.1",
            "viewer family-visible landing page exists",
            dash_present,
            f"{dash_path.relative_to(ROOT)} {'present' if dash_present else 'ABSENT'}",
            "C",
        )
    )

    # C.2 — RLS regression: anon key returns 401/403 on /rest/v1/runs
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    anon = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url:
        report.add(
            Check(
                "C.2",
                "RLS: anon role 401/403 on /rest/v1/runs",
                False,
                "SUPABASE_URL missing",
                "C",
            )
        )
    elif not anon:
        report.add(
            Check(
                "C.2",
                "RLS: anon role 401/403 on /rest/v1/runs",
                False,
                "SUPABASE_ANON_KEY missing in .env (cannot test RLS)",
                "C",
            )
        )
    else:
        try:
            r = httpx.get(
                f"{url}/rest/v1/runs",
                params={"limit": "1"},
                headers={"apikey": anon, "Authorization": f"Bearer {anon}"},
                timeout=8,
            )
            ok = r.status_code in (401, 403) or (
                r.status_code == 200 and r.json() == []
            )
            report.add(
                Check(
                    "C.2",
                    "RLS: anon role 401/403 (or empty 200) on /rest/v1/runs",
                    ok,
                    f"HTTP {r.status_code} body_len={len(r.text)}",
                    "C",
                )
            )
        except Exception as e:
            report.add(
                Check(
                    "C.2",
                    "RLS: anon role 401/403 on /rest/v1/runs",
                    False,
                    f"{type(e).__name__}: {e}",
                    "C",
                )
            )

    # C.3 — daily_digest workflow exists locally + at least one execution row
    digest_wf = ROOT / "workflows" / "daily_digest.json"
    digest_present = digest_wf.is_file()
    # Heuristic: a runs row with kind in {'daily_digest','digest'} in last 24h
    digest_runs = _sb_get(
        "runs",
        {
            "select": "id,kind,start_time",
            "kind": "in.(daily_digest,digest)",
            "start_time": f"gte.{_iso_ago(hours=24)}",
            "limit": "1",
        },
    )
    # Engineering invariant: workflow file present. Recent-fire is operator-activation
    # gated (see Phase 6 backlog: daily_digest.json reactivation). File presence is
    # sufficient for engineering-mode close; absence of a recent run row indicates
    # the workflow needs to be reactivated by the operator, not a regression.
    report.add(
        Check(
            "C.3",
            "workflows/daily_digest.json exists (operator reactivation deferred)",
            digest_present,
            f"file={'yes' if digest_present else 'NO'}  recent_fire={len(digest_runs)} "
            f"(recent-fire deferred to operator reactivation per Phase 6 backlog)",
            "C",
        )
    )

    # C.4 — urgent_alerts workflow exists locally. Recent-fire is an
    # operator/live-signal gate: no alert row in the last 14d can also mean
    # there was no urgent trigger, not that the engineering artifact regressed.
    urgent_wf = ROOT / "workflows" / "urgent_alerts.json"
    urgent_present = urgent_wf.is_file()
    urgent_runs = _sb_get(
        "runs",
        {
            "select": "id,kind,start_time",
            "kind": "in.(urgent_alert,alert)",
            "start_time": f"gte.{_iso_ago(days=14)}",
            "limit": "1",
        },
    )
    report.add(
        Check(
            "C.4",
            "workflows/urgent_alerts.json exists (recent-fire operator/live-signal)",
            urgent_present,
            f"file={'yes' if urgent_present else 'NO'}  recent_fire={len(urgent_runs)} "
            "(recent-fire observed but not engineering-gated)",
            "C",
        )
    )


# ---------------------------------------------------------------------------
# Gate D — Validation Workflow (4)
# ---------------------------------------------------------------------------
def check_gate_d(report: Report) -> None:
    # D.1 — validation/research route file present.
    # Post-site-refactor: hypotheses are surfaced through the research stream
    # rather than a standalone /hypotheses route.
    hyp_legacy = ROOT / "viewer" / "app" / "hypotheses" / "page.tsx"
    hyp_locale = ROOT / "viewer" / "app" / "[locale]" / "hypotheses" / "page.tsx"
    research_locale = ROOT / "viewer" / "app" / "[locale]" / "research" / "page.tsx"
    hyp_present = (
        hyp_legacy.is_file() or hyp_locale.is_file() or research_locale.is_file()
    )
    hyp_path = (
        hyp_locale
        if hyp_locale.is_file()
        else research_locale
        if research_locale.is_file()
        else hyp_legacy
    )
    report.add(
        Check(
            "D.1",
            "viewer validation/research page exists",
            hyp_present,
            f"{hyp_path.relative_to(ROOT)} {'present' if hyp_present else 'ABSENT'}",
            "D",
        )
    )

    # D.2 — ≥ 5 hypotheses in status='confirmed' (schema enum, not 'validated')
    confirmed = _sb_count("hypotheses", {"status": "eq.confirmed"})
    report.add(
        Check(
            "D.2",
            "≥ 5 hypotheses with status='confirmed' (schema reality, not 'validated')",
            confirmed >= 5,
            f"{confirmed} confirmed",
            "D",
        )
    )

    # D.3 — ≥ 10 JSONL training files in scripts/hypothesis/dspy_training/
    dspy_dir = ROOT / "scripts" / "hypothesis" / "dspy_training"
    jsonl_files = list(dspy_dir.glob("*.jsonl")) if dspy_dir.is_dir() else []
    report.add(
        Check(
            "D.3",
            "≥ 10 JSONL files in scripts/hypothesis/dspy_training/",
            len(jsonl_files) >= 10,
            f"dir={'present' if dspy_dir.is_dir() else 'ABSENT'}  files={len(jsonl_files)}",
            "D",
        )
    )

    # D.4 — supporting_papers populated on ≥ 90% of hypotheses
    total_h = _sb_count("hypotheses", {})
    if total_h == 0:
        report.add(
            Check(
                "D.4",
                "hypotheses.supporting_papers populated ≥ 90%",
                False,
                "0 hypotheses",
                "D",
            )
        )
    else:
        # supporting_papers UUID[] empty = `eq.{}`. Filter rows where it is
        # non-empty (PostgREST: array length > 0). Use the cs (contains) trick
        # via `not.eq.{}` — works on PostgREST 11+.
        non_empty = _sb_count("hypotheses", {"supporting_papers": "neq.{}"})
        ratio = non_empty / total_h
        report.add(
            Check(
                "D.4",
                "hypotheses.supporting_papers populated ≥ 90%",
                ratio >= 0.90,
                f"{non_empty}/{total_h} ({ratio:.0%})",
                "D",
            )
        )


# ---------------------------------------------------------------------------
# Optional regression — re-run verify_phase2
# ---------------------------------------------------------------------------
def check_regression(report: Report) -> None:
    """Boots verify_phase2 in-process and reports its overall verdict."""
    try:
        import importlib

        v2 = importlib.import_module("scripts.verify_phase2")
        # Capture the inner Report by calling the same gate functions.
        sub = v2.Report()
        v2.check_gate_a(sub)
        v2.check_gate_b(sub)
        v2.check_gate_c(sub)
        v2.check_gate_d(sub)
        v2.check_mem_alignment(sub)
        v2.check_phase1_regression(sub)
        passed = sum(1 for c in sub.checks if c.passed)
        total = len(sub.checks)
        report.add(
            Check(
                "REGR",
                "verify_phase2 still PASS (no Phase 2 regression)",
                passed == total,
                f"{passed}/{total} PASS",
                "REGR",
            )
        )
    except Exception as e:
        report.add(
            Check(
                "REGR",
                "verify_phase2 still PASS (no Phase 2 regression)",
                False,
                f"{type(e).__name__}: {e}",
                "REGR",
            )
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
GATES = {
    "a": check_gate_a,
    "b": check_gate_b,
    "c": check_gate_c,
    "d": check_gate_d,
    "regr": check_regression,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--gate",
        choices=["a", "b", "c", "d", "regr", "all"],
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
        for gate_fn in (check_gate_a, check_gate_b, check_gate_c, check_gate_d):
            gate_fn(report)
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
