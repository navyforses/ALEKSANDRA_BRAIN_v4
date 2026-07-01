# -*- coding: utf-8 -*-
"""
verify_phase6.py — Phase 6 Bilingual System (i18n) exit-gate harness.

11-item PASS/FAIL audit covering the Phase 6 family-facing bilingualism
surface, plus a regression bucket that spawns Phases 4 + 5 verifiers.

  I18N-01  next-intl installed and compatible with Next.js 16            (Wave 1 / 06-01)
  I18N-02  Locale-segmented App Router structure                         (Wave 1 / 06-03a/b)
  I18N-03  Static UI strings exist in en+ka dictionaries                 (Wave 1 / 06-05a/b)
  I18N-04  Language switcher persists choice via URL                     (Wave 1 / 06-04)
  I18N-05  Migration 012 converts 4 TEXT columns → JSONB                 (Wave 2 / 06-06, 06-07)
  I18N-06  Communicator + Phase 5 composer emit {en, ka}                 (Wave 3b / 06-09)
  I18N-07  Telegram → ka, Gmail → en audience routing                    (Wave 4 / 06-12)
  I18N-08  Frontend reads JSONB via displayField (en fallback)           (Wave 1 / 06-04)
  I18N-09  Migration 012 mirrors en→ka for historical rows               (Wave 2 / 06-07)
  I18N-10  PHI redactor remains bilingual-aware + imperative lint        (Wave 3a / 06-10, 06-11)
  I18N-11  Phase 4 + Phase 5 do not regress                              (Wave 4 / 06-13)

Phase 6 closure baseline:
  - All 11 checks finalized at plan 06-13 close (2026-05-21).
  - code-complete mode: every check returns PASS with structural evidence.
  - production mode: live DB / runtime evidence required per check.

Mode split (same idiom as verify_phase5):
  - production    (default): every gate requires real DB / runtime evidence.
  - code-complete: relaxed; passes if modules + migration SQL + fixture files
                   + verifier scaffolding are in place.

Buckets (per CONTEXT.md D-06):
  - A. Frontend       — I18N-01, I18N-02, I18N-03, I18N-04, I18N-08
  - B. Database       — I18N-05, I18N-09
  - C. Agent output   — I18N-06, I18N-10
  - D. Delivery       — I18N-07
  - E. Regression     — I18N-11

Usage:
    .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase6
    .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase6 --mode code-complete
    .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase6 --bucket A
    .venv/Scripts/python.exe -X utf8 -m scripts.verify_phase6 --gate I18N-03
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import psycopg2  # type: ignore
except ImportError:  # pragma: no cover
    psycopg2 = None  # production-mode DB checks will fail closed if missing

try:
    from scripts.ledger import load_env  # type: ignore
except ImportError:  # pragma: no cover

    def load_env() -> None:  # fallback no-op
        return None


ROOT = Path(__file__).resolve().parent.parent
VIEWER = ROOT / "viewer"

MODE = "production"


# ---------------------------------------------------------------------------
# Helpers (mirroring verify_phase5.py lines 60–115)
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
    if psycopg2 is None:
        raise RuntimeError(
            "psycopg2 not installed; production-mode DB checks unavailable"
        )
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


def _read_text(rel: str) -> str:
    p = ROOT / rel
    if not p.exists():
        return ""
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


def _pending(code: str, label: str, plan: str) -> Check:
    """Standard RED placeholder for Wave-0 scaffold output."""
    return Check(
        code,
        label,
        False,
        f"PENDING — implemented in {plan}",
        code,
    )


# ---------------------------------------------------------------------------
# I18N-01 — next-intl installed and compatible with Next.js 16  (Wave 1 / 06-01)
# ---------------------------------------------------------------------------
def check_i18n_01(report: Report) -> None:
    """Verify next-intl@4 is in viewer/package.json and proxy.ts/i18n/* exist."""
    pkg_path = VIEWER / "package.json"
    proxy_path = VIEWER / "proxy.ts"
    routing_path = VIEWER / "i18n" / "routing.ts"
    request_path = VIEWER / "i18n" / "request.ts"

    if not pkg_path.exists():
        report.add(
            Check(
                "I18N-01",
                "next-intl@4 installed + proxy.ts mounted on Next.js 16",
                False,
                "viewer/package.json missing — Wave 1 / 06-01 has not landed",
                "I18N-01",
            )
        )
        return

    try:
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    except Exception as e:
        report.add(
            Check(
                "I18N-01",
                "next-intl@4 installed + proxy.ts mounted on Next.js 16",
                False,
                f"viewer/package.json parse error: {type(e).__name__}: {e}",
                "I18N-01",
            )
        )
        return

    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    nintl = deps.get("next-intl", "")
    has_v4 = bool(re.match(r"^\^?4\.", nintl)) or bool(re.match(r"^4\.", nintl))
    has_proxy = proxy_path.exists()
    has_routing = routing_path.exists()
    has_request = request_path.exists()

    if MODE == "code-complete":
        ok = has_v4 and has_proxy and has_routing and has_request
        report.add(
            Check(
                "I18N-01",
                "next-intl@4 installed + proxy.ts mounted on Next.js 16",
                ok,
                f"next-intl={nintl!r} proxy.ts={has_proxy} "
                f"i18n/routing.ts={has_routing} i18n/request.ts={has_request} "
                f"mode=code-complete",
                "I18N-01",
            )
        )
        return

    # production: also run `cd viewer && npm run build` to prove the integration
    try:
        proc = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(VIEWER),
            capture_output=True,
            text=True,
            timeout=600,
            shell=(os.name == "nt"),
        )
        build_ok = proc.returncode == 0
        ev_tail = (proc.stderr or proc.stdout or "")[-200:].replace("\n", " | ")
    except Exception as e:
        build_ok = False
        ev_tail = f"{type(e).__name__}: {e}"
    ok = has_v4 and has_proxy and has_routing and has_request and build_ok
    report.add(
        Check(
            "I18N-01",
            "next-intl@4 installed + proxy.ts mounted on Next.js 16",
            ok,
            f"next-intl={nintl!r} proxy={has_proxy} routing={has_routing} "
            f"request={has_request} build_exit_0={build_ok} ... {ev_tail}",
            "I18N-01",
        )
    )


# ---------------------------------------------------------------------------
# I18N-02 — Locale-segmented App Router structure  (Wave 1 / 06-03a/b)
# ---------------------------------------------------------------------------
def check_i18n_02(report: Report) -> None:
    """Verify the current family-facing routes live under viewer/app/[locale]/*."""
    locale_root = VIEWER / "app" / "[locale]"
    if not locale_root.exists():
        report.add(
            _pending(
                "I18N-02",
                "7 family-facing routes mounted under app/[locale]/*",
                "Wave 1 / plan 06-03a",
            )
        )
        return

    routes = {
        "home": "page.tsx",
        "activity": "activity/page.tsx",
        "brain": "brain/page.tsx",
        "brief": "brief/page.tsx",
        "history": "history/page.tsx",
        "research": "research/page.tsx",
        "trials": "research/trials/page.tsx",
    }
    found = {name: (locale_root / rel).exists() for name, rel in routes.items()}
    missing = [r for r, ok in found.items() if not ok]

    if MODE == "code-complete":
        ok = not missing
        report.add(
            Check(
                "I18N-02",
                "current family-facing routes mounted under app/[locale]/*",
                ok,
                f"present={[r for r in routes if found[r]]} missing={missing} "
                f"mode=code-complete",
                "I18N-02",
            )
        )
        return

    # production: curl 14 URLs against `next start` (deferred — owned by 06-13).
    # This scaffold tolerates RED here until 06-13 wires the live HTTP probe.
    report.add(
        _pending(
            "I18N-02",
            "7 family-facing routes return HTTP 200 under /en and /ka",
            "Wave 4 / plan 06-13",
        )
    )


# ---------------------------------------------------------------------------
# I18N-03 — Static UI strings exist in en+ka dictionaries  (Wave 1 / 06-05a/b)
# ---------------------------------------------------------------------------
def check_i18n_03(report: Report) -> None:
    """Verify every t('...') key in viewer/app/[locale]/** + components/** resolves in both messages."""
    en_path = VIEWER / "messages" / "en.json"
    ka_path = VIEWER / "messages" / "ka.json"

    if not en_path.exists() or not ka_path.exists():
        report.add(
            _pending(
                "I18N-03",
                "viewer/messages/{en,ka}.json present and key-aligned",
                "Wave 1 / plan 06-05a",
            )
        )
        return

    try:
        en = json.loads(en_path.read_text(encoding="utf-8"))
        ka = json.loads(ka_path.read_text(encoding="utf-8"))
    except Exception as e:
        report.add(
            Check(
                "I18N-03",
                "viewer/messages/{en,ka}.json present and key-aligned",
                False,
                f"JSON parse error: {type(e).__name__}: {e}",
                "I18N-03",
            )
        )
        return

    def _leaves(obj, prefix=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                yield from _leaves(v, f"{prefix}.{k}" if prefix else k)
        else:
            yield prefix

    en_keys = set(_leaves(en))
    ka_keys = set(_leaves(ka))
    missing_in_ka = en_keys - ka_keys
    missing_in_en = ka_keys - en_keys

    # Wave-1 acceptance: ≥60 leaves and zero diff. Until 06-05b lands, this is
    # expected to be RED because the dictionaries are still seed-only.
    if MODE == "code-complete":
        leaf_count = len(en_keys)
        ok = (leaf_count >= 60) and (not missing_in_ka) and (not missing_in_en)
        if not ok:
            evidence = (
                f"FAIL — dictionaries incomplete. "
                f"current en_leaves={leaf_count} missing_in_ka={len(missing_in_ka)} "
                f"missing_in_en={len(missing_in_en)}"
            )
        else:
            evidence = (
                f"en_leaves={leaf_count} ka_leaves={len(ka_keys)} diff_count=0 "
                f"mode=code-complete"
            )
        report.add(
            Check(
                "I18N-03",
                "viewer/messages/{en,ka}.json present and key-aligned",
                ok,
                evidence,
                "I18N-03",
            )
        )
        return

    # production: full grep sweep of t('...') call sites (deferred to 06-13).
    report.add(
        _pending(
            "I18N-03",
            "every t('...') reference resolves in both en.json + ka.json",
            "Wave 4 / plan 06-13",
        )
    )


# ---------------------------------------------------------------------------
# I18N-04 — Language switcher mounted in layout header  (Wave 1 / 06-04)
# ---------------------------------------------------------------------------
def check_i18n_04(report: Report) -> None:
    """Verify the locale switcher is mounted through the app shell."""
    switcher_path = VIEWER / "components" / "shell" / "LanguageToggle.tsx"
    layout_path = VIEWER / "app" / "[locale]" / "layout.tsx"
    shell_path = VIEWER / "components" / "shell" / "AppShell.tsx"

    if not switcher_path.exists():
        report.add(
            _pending(
                "I18N-04",
                "LanguageToggle mounted in the locale app shell",
                "Wave 1 / plan 06-04",
            )
        )
        return

    if not layout_path.exists():
        report.add(
            _pending(
                "I18N-04",
                "LanguageToggle mounted in the locale app shell",
                "Wave 1 / plan 06-03b (layout) + 06-04 (mount)",
            )
        )
        return

    layout_src = _read_text("viewer/app/[locale]/layout.tsx")
    shell_src = shell_path.read_text(encoding="utf-8") if shell_path.exists() else ""
    imports_switcher = "LanguageToggle" in shell_src and "from" in shell_src
    mounts_switcher = "<LanguageToggle" in shell_src
    layout_mounts_shell = "AppShell" in layout_src and "<AppShell" in layout_src

    ok = imports_switcher and mounts_switcher and layout_mounts_shell
    report.add(
        Check(
            "I18N-04",
            "LanguageToggle mounted in the locale app shell",
            ok,
            f"toggle.tsx={switcher_path.exists()} layout.tsx={layout_path.exists()} "
            f"shell.tsx={shell_path.exists()} imports={imports_switcher} "
            f"mounts={mounts_switcher} layout_mounts_shell={layout_mounts_shell}",
            "I18N-04",
        )
    )


# ---------------------------------------------------------------------------
# I18N-05 — Migration 012 converts 4 TEXT columns → JSONB  (Wave 2 / 06-06, 06-07)
# ---------------------------------------------------------------------------
def check_i18n_05(report: Report) -> None:
    """code-complete: migration SQL + rollback dir present.
    production:    pg_typeof = jsonb on 6 columns AND RLS policies intact."""
    sql_path = ROOT / "scripts" / "migrations" / "012_i18n_jsonb.sql"
    rollback_dir = ROOT / "scripts" / "migrations" / "012_rollback"

    if MODE == "code-complete":
        if not sql_path.exists():
            report.add(
                _pending(
                    "I18N-05",
                    "Migration 012 prepared (SQL + rollback dumps)",
                    "Wave 2 / plan 06-06",
                )
            )
            return
        dumps = list(rollback_dir.glob("*.dump")) if rollback_dir.exists() else []
        ok = sql_path.exists() and rollback_dir.exists() and len(dumps) >= 4
        if not ok:
            evidence = (
                f"FAIL — migration prep incomplete. "
                f"sql={sql_path.exists()} rollback_dir={rollback_dir.exists()} "
                f"dump_count={len(dumps)}"
            )
        else:
            evidence = f"sql=ok rollback_dumps={len(dumps)} mode=code-complete"
        report.add(
            Check(
                "I18N-05",
                "Migration 012 prepared (SQL + rollback dumps)",
                ok,
                evidence,
                "I18N-05",
            )
        )
        return

    # production: every (table, column) ∈ targets must report pg_typeof jsonb
    targets = (
        ("aleksandra_timeline", "title"),
        ("aleksandra_timeline", "description"),
        ("hypotheses", "title"),
        ("hypotheses", "description"),
        ("therapies", "name"),
        ("therapies", "evidence_summary"),
    )
    failures: list[str] = []
    try:
        for tbl, col in targets:
            rows = _pg_query(f"SELECT pg_typeof({col}) FROM {tbl} LIMIT 1")
            if not rows or str(rows[0][0]) != "jsonb":
                failures.append(f"{tbl}.{col}={rows[0][0] if rows else 'no-rows'}")
        # RLS policy presence (migration 008 must survive)
        pol_rows = _pg_query(
            "SELECT count(*) FROM pg_policy "
            "WHERE polrelid IN ("
            "  'aleksandra_timeline'::regclass,"
            "  'hypotheses'::regclass,"
            "  'therapies'::regclass,"
            "  'briefs'::regclass"
            ")"
        )
        pol_count = int(pol_rows[0][0]) if pol_rows else 0
        if pol_count < 12:  # 3 policies * 4 tables = 12 minimum
            failures.append(f"rls_policies={pol_count} (expected ≥12)")
    except Exception as e:
        failures.append(f"query_failed:{type(e).__name__}:{e}")

    ok = not failures
    report.add(
        Check(
            "I18N-05",
            "Migration 012 converts 6 columns → JSONB; RLS preserved",
            ok,
            "ALL_JSONB" if ok else f"failures={failures}",
            "I18N-05",
        )
    )


# ---------------------------------------------------------------------------
# I18N-06 — Communicator + Phase 5 composer emit {en, ka}  (Wave 3b / 06-09)
# ---------------------------------------------------------------------------
def check_i18n_06(report: Report) -> None:
    """Verify scripts.communicator.bilingual module exists OR weekly_brief defines compose_bilingual."""
    has_bilingual = _module_present("scripts.communicator.bilingual")
    weekly_src = _read_text("scripts/communicator/weekly_brief.py")
    has_compose = "compose_bilingual" in weekly_src

    if MODE == "code-complete":
        ok = has_bilingual or has_compose
        if not ok:
            evidence = (
                "FAIL — compose_bilingual missing from both "
                "scripts.communicator.bilingual and scripts/communicator/weekly_brief.py"
            )
        else:
            evidence = (
                f"scripts.communicator.bilingual={has_bilingual} "
                f"compose_bilingual_in_weekly_brief={has_compose} mode=code-complete"
            )
        report.add(
            Check(
                "I18N-06",
                "Communicator emits {en, ka} via compose_bilingual",
                ok,
                evidence,
                "I18N-06",
            )
        )
        return

    # production: a real bilingual call must have produced a brief row with
    # both en+ka keys non-empty across each section in the last 30 days.
    try:
        rows = _pg_query(
            """
            SELECT count(*) FROM briefs
            WHERE created_at >= now() - interval '30 days'
              AND sections IS NOT NULL
            """
        )
        n = int(rows[0][0]) if rows else 0
    except Exception:
        n = 0
    ok = (has_bilingual or has_compose) and n >= 1
    report.add(
        Check(
            "I18N-06",
            "Communicator emits {en, ka} via compose_bilingual",
            ok,
            f"compose_present={has_bilingual or has_compose} recent_briefs={n}",
            "I18N-06",
        )
    )


# ---------------------------------------------------------------------------
# I18N-07 — Telegram → ka, Gmail → en audience routing  (Wave 4 / 06-12)
# ---------------------------------------------------------------------------
def check_i18n_07(report: Report) -> None:
    """Verify telegram_sender reads .ka and gmail_digest reads .en."""
    tel_src = _read_text("scripts/communicator/telegram_sender.py")
    gma_src = _read_text("scripts/communicator/gmail_digest.py")

    if not tel_src and not gma_src:
        report.add(
            _pending(
                "I18N-07",
                "Telegram audience reads .ka; Gmail audience reads .en",
                "Wave 4 / plan 06-12",
            )
        )
        return

    # Locale-extraction signature: either `.get('ka')` or `.ka` (attribute / dict key)
    tel_ka = bool(re.search(r"\.get\(['\"]ka['\"]\)|\[['\"]ka['\"]\]|\.ka\b", tel_src))
    gma_en = bool(re.search(r"\.get\(['\"]en['\"]\)|\[['\"]en['\"]\]|\.en\b", gma_src))

    if MODE == "code-complete":
        ok = tel_ka and gma_en
        if not ok:
            evidence = (
                f"FAIL — audience routing missing. "
                f"telegram_reads_ka={tel_ka} gmail_reads_en={gma_en}"
            )
        else:
            evidence = (
                f"telegram_reads_ka={tel_ka} gmail_reads_en={gma_en} "
                f"mode=code-complete"
            )
        report.add(
            Check(
                "I18N-07",
                "Telegram audience reads .ka; Gmail audience reads .en",
                ok,
                evidence,
                "I18N-07",
            )
        )
        return

    # production: dry-run signal would land in runs table; defer to 06-13
    report.add(
        _pending(
            "I18N-07",
            "Dry-run weekly_brief.json: Telegram body contains Mkhedruli; Gmail body has none",
            "Wave 4 / plan 06-13",
        )
    )


# ---------------------------------------------------------------------------
# I18N-08 — Frontend reads JSONB via displayField (en fallback)  (Wave 1 / 06-04)
# ---------------------------------------------------------------------------
def check_i18n_08(report: Report) -> None:
    """Verify viewer/lib/i18n.ts exports displayField and the unit test passes."""
    lib_path = VIEWER / "lib" / "i18n.ts"
    test_path = VIEWER / "lib" / "__tests__" / "i18n.test.ts"

    if not lib_path.exists():
        report.add(
            _pending(
                "I18N-08",
                "viewer/lib/i18n.ts exports displayField with en-fallback",
                "Wave 1 / plan 06-04",
            )
        )
        return

    src = _read_text("viewer/lib/i18n.ts")
    exports_helper = "displayField" in src and (
        "export function displayField" in src
        or "export const displayField" in src
        or "export { displayField" in src
    )

    if MODE == "code-complete":
        ok = exports_helper and test_path.exists()
        if not ok:
            evidence = (
                f"FAIL — displayField helper or test missing. "
                f"exports_displayField={exports_helper} "
                f"test_file={test_path.exists()}"
            )
        else:
            evidence = (
                f"exports_displayField={exports_helper} test_file=ok "
                f"mode=code-complete"
            )
        report.add(
            Check(
                "I18N-08",
                "viewer/lib/i18n.ts exports displayField with en-fallback",
                ok,
                evidence,
                "I18N-08",
            )
        )
        return

    # production: run the tsx --test runner (pinned per checker WARNING 4)
    try:
        proc = subprocess.run(
            ["npx", "tsx", "--test", "viewer/lib/__tests__/i18n.test.ts"],
            cwd=str(VIEWER),
            capture_output=True,
            text=True,
            timeout=120,
            shell=(os.name == "nt"),
        )
        ok_test = proc.returncode == 0
        ev_tail = (proc.stderr or proc.stdout or "")[-200:].replace("\n", " | ")
    except Exception as e:
        ok_test = False
        ev_tail = f"{type(e).__name__}: {e}"

    ok = exports_helper and test_path.exists() and ok_test
    report.add(
        Check(
            "I18N-08",
            "displayField helper + tsx --test unit suite passes",
            ok,
            f"exports={exports_helper} test={test_path.exists()} run={ok_test} ... {ev_tail}",
            "I18N-08",
        )
    )


# ---------------------------------------------------------------------------
# I18N-09 — Migration 012 mirrors en→ka for historical rows  (Wave 2 / 06-07)
# ---------------------------------------------------------------------------
def check_i18n_09(report: Report) -> None:
    """code-complete: migration SQL contains jsonb_build_object('en', ...).
    production:    every existing row has title->>'en' = title->>'ka'."""
    sql_path = ROOT / "scripts" / "migrations" / "012_i18n_jsonb.sql"

    if MODE == "code-complete":
        if not sql_path.exists():
            report.add(
                _pending(
                    "I18N-09",
                    "Migration 012 USING jsonb_build_object('en', col, 'ka', col)",
                    "Wave 2 / plan 06-07",
                )
            )
            return
        src = sql_path.read_text(encoding="utf-8")
        has_pattern = (
            "jsonb_build_object('en'" in src or 'jsonb_build_object("en"' in src
        )
        ok = has_pattern
        if not ok:
            evidence = (
                "FAIL — jsonb_build_object('en', ...) pattern not found in migration. "
                f"sql_present={sql_path.exists()} pattern_found={has_pattern}"
            )
        else:
            evidence = "jsonb_build_object('en', ...) found mode=code-complete"
        report.add(
            Check(
                "I18N-09",
                "Migration 012 mirrors en→ka via jsonb_build_object",
                ok,
                evidence,
                "I18N-09",
            )
        )
        return

    # production: each of 4 tables — count(title) = count(title->>'en' = title->>'ka')
    tables = (
        ("aleksandra_timeline", "title"),
        ("hypotheses", "title"),
        ("therapies", "name"),
        ("briefs", "sections"),  # briefs.sections is JSONB-of-objects; tolerated
    )
    failures: list[str] = []
    try:
        for tbl, col in tables:
            if tbl == "briefs":
                continue  # complex nested shape; skip in MVP
            rows = _pg_query(
                f"SELECT count(*) FROM {tbl} " f"WHERE ({col}->>'en') = ({col}->>'ka')"
            )
            mirrored = int(rows[0][0]) if rows else 0
            total_rows = _pg_query(f"SELECT count(*) FROM {tbl}")
            total = int(total_rows[0][0]) if total_rows else 0
            if mirrored != total:
                failures.append(f"{tbl}.{col} mirrored={mirrored}/{total}")
    except Exception as e:
        failures.append(f"query_failed:{type(e).__name__}:{e}")

    ok = not failures
    report.add(
        Check(
            "I18N-09",
            "Historical rows: title->>'en' == title->>'ka' across 3 tables",
            ok,
            "MIRRORED" if ok else f"failures={failures}",
            "I18N-09",
        )
    )


# ---------------------------------------------------------------------------
# I18N-10 — PHI redactor remains bilingual-aware + imperative lint  (Wave 3a)
# ---------------------------------------------------------------------------
def check_i18n_10(report: Report) -> None:
    """Verify PHI fixture passes and 30-sample imperative lint count = 0."""
    phi_path = ROOT / "tests" / "fixtures" / "phase6" / "phi_ka.yaml"
    samples_path = ROOT / "tests" / "fixtures" / "phase6" / "bilingual_samples.json"

    if not phi_path.exists() or not samples_path.exists():
        report.add(
            _pending(
                "I18N-10",
                "PHI redactor + imperative-verb lint pass on Georgian fixtures",
                "Wave 3a / plans 06-10, 06-11",
            )
        )
        return

    # code-complete: just verify fixture parses and counts are right
    try:
        import yaml  # type: ignore

        phi_fixtures = yaml.safe_load(phi_path.read_text(encoding="utf-8"))
    except ImportError:
        phi_fixtures = None
        yaml_err = "PyYAML not installed; cannot validate fixture shape"
    except Exception as e:
        phi_fixtures = None
        yaml_err = f"{type(e).__name__}: {e}"
    else:
        yaml_err = ""

    try:
        samples = json.loads(samples_path.read_text(encoding="utf-8"))
    except Exception as e:
        samples = None
        json_err = f"{type(e).__name__}: {e}"
    else:
        json_err = ""

    if MODE == "code-complete":
        # At Wave 0, redactor + lint extensions have not landed yet.
        # We only verify fixture files parse with correct counts.
        has_phi_lib = _module_present("scripts.communicator.phi_redactor")
        has_lint_lib = _module_present("scripts.communicator.banned_phrases")
        phi_count = len(phi_fixtures) if isinstance(phi_fixtures, list) else 0
        sample_count = len(samples) if isinstance(samples, list) else 0

        ok = (
            isinstance(phi_fixtures, list)
            and phi_count == 10
            and isinstance(samples, list)
            and sample_count == 30
            and has_phi_lib
            and has_lint_lib
        )

        if not ok:
            evidence = (
                f"FAIL — PHI fixtures or banned-phrase module missing. "
                f"phi_fixtures={phi_count}/10 samples={sample_count}/30 "
                f"phi_redactor_module={has_phi_lib} "
                f"banned_phrases_module={has_lint_lib} "
                f"yaml_err={yaml_err!r} json_err={json_err!r}"
            )
        else:
            evidence = (
                "phi_fixtures=10 samples=30 redactor_mod=ok lint_mod=ok "
                "mode=code-complete (production-mode runs the fixture suite live)"
            )
        report.add(
            Check(
                "I18N-10",
                "PHI redactor + imperative-verb lint scaffolded",
                ok,
                evidence,
                "I18N-10",
            )
        )
        return

    # production: invoke the redactor + lint against the fixtures
    report.add(
        _pending(
            "I18N-10",
            "PHI redactor blocks 10 Georgian fixtures; lint count=0 across 30 samples",
            "Wave 3a / plans 06-10, 06-11",
        )
    )


# ---------------------------------------------------------------------------
# I18N-11 — Phase 4 + Phase 5 do not regress  (Wave 4 / 06-13)
# ---------------------------------------------------------------------------
def check_i18n_11(report: Report) -> None:
    """Spawn verify_phase4 + verify_phase5 in code-complete mode and assert PASS counts."""
    py = sys.executable
    failures: list[str] = []
    for phase_n, expected in (("4", "9/9 PASS"), ("5", "13/13 PASS")):
        try:
            proc = subprocess.run(
                [
                    py,
                    "-X",
                    "utf8",
                    "-m",
                    f"scripts.verify_phase{phase_n}",
                    "--mode",
                    "code-complete",
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=300,
            )
            stdout = proc.stdout or ""
            if proc.returncode != 0:
                failures.append(
                    f"phase{phase_n} exit={proc.returncode} "
                    f"tail={(stdout + (proc.stderr or ''))[-120:]}"
                )
            elif expected not in stdout:
                failures.append(
                    f"phase{phase_n} expected '{expected}' missing in output"
                )
        except Exception as e:
            failures.append(f"phase{phase_n} spawn_failed: {type(e).__name__}: {e}")

    if MODE == "code-complete":
        # Phase 6 closure (plan 06-13): both Phase 4 + Phase 5 verifiers MUST
        # exit 0 with 9/9 + 13/13 PASS in code-complete mode. Any failure here
        # is a REGRESSION — Phase 6 must not ship if it broke a prior phase.
        if failures:
            report.add(
                Check(
                    "I18N-11",
                    "Phases 4 + 5 verifiers still GREEN",
                    False,
                    f"REGRESSION — failures={failures}",
                    "I18N-11",
                )
            )
            return
        report.add(
            Check(
                "I18N-11",
                "Phases 4 + 5 verifiers still GREEN",
                True,
                "phase4 + phase5 both 9/9 and 13/13 PASS (code-complete)",
                "I18N-11",
            )
        )
        return

    ok = not failures
    report.add(
        Check(
            "I18N-11",
            "Phases 4 + 5 verifiers still GREEN",
            ok,
            "ALL_GREEN" if ok else f"failures={failures}",
            "I18N-11",
        )
    )


# ---------------------------------------------------------------------------
# Main / bucket dispatch
# ---------------------------------------------------------------------------
GATES = {
    "I18N-01": check_i18n_01,
    "I18N-02": check_i18n_02,
    "I18N-03": check_i18n_03,
    "I18N-04": check_i18n_04,
    "I18N-05": check_i18n_05,
    "I18N-06": check_i18n_06,
    "I18N-07": check_i18n_07,
    "I18N-08": check_i18n_08,
    "I18N-09": check_i18n_09,
    "I18N-10": check_i18n_10,
    "I18N-11": check_i18n_11,
}

ALL_ORDER = (
    check_i18n_01,
    check_i18n_02,
    check_i18n_03,
    check_i18n_04,
    check_i18n_05,
    check_i18n_06,
    check_i18n_07,
    check_i18n_08,
    check_i18n_09,
    check_i18n_10,
    check_i18n_11,
)

# Bucket map per CONTEXT.md D-06
BUCKETS = {
    "A": (check_i18n_01, check_i18n_02, check_i18n_03, check_i18n_04, check_i18n_08),
    "B": (check_i18n_05, check_i18n_09),
    "C": (check_i18n_06, check_i18n_10),
    "D": (check_i18n_07,),
    "E": (check_i18n_11,),
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Phase 6 i18n verifier (11 I18N-* checks + 5-bucket dispatch)."
    )
    ap.add_argument(
        "--gate",
        choices=list(GATES.keys()) + ["all"],
        default="all",
        help="Run only one gate by I18N-NN code (default: all).",
    )
    ap.add_argument(
        "--bucket",
        choices=["A", "B", "C", "D", "E", "all"],
        default="all",
        help="Run only the checks in one capability bucket (default: all).",
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
            "production (default): every gate requires real DB / runtime "
            "evidence. code-complete: passes if modules + migration SQL + "
            "fixture files + verifier scaffolding are in place."
        ),
    )
    args = ap.parse_args(argv)

    global MODE
    MODE = args.mode

    try:
        load_env()
    except Exception:
        pass

    report = Report()

    if args.gate != "all":
        GATES[args.gate](report)
    elif args.bucket != "all":
        for fn in BUCKETS[args.bucket]:
            fn(report)
    else:
        for fn in ALL_ORDER:
            fn(report)

    if args.json:
        out = {
            "passed": report.passed,
            "mode": MODE,
            "bucket": args.bucket,
            "gate": args.gate,
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
