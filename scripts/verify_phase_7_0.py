# -*- coding: utf-8 -*-
"""Phase 7.0 — Belief State Foundation verifier.

11-item PASS/FAIL audit covering the `brain/belief/` Bayesian foundation:

  check_7_0_01  PyMC import + version (>=5.18 or 6.x)
  check_7_0_02  13 dimensions registered (TOML catalog or DB)
  check_7_0_03  All 13 priors have a primary-source citation (no TBD stubs)
  check_7_0_04  Beta-Binomial analytical match (delta < 0.005) — Day 4 script
  check_7_0_05  Sampler convergence rhat < 1.01 / ess_bulk > 400 — Day 10 sweep
  check_7_0_06  Idempotency: evidence_hash de-dupes update() calls
  check_7_0_07  Likelihood registry covers all 8 distribution kinds
  check_7_0_08  PosteriorDelta returned by update() end-to-end (beta-binomial)
  check_7_0_09  Adapters extract evidence from synthetic MRI + voice notes
  check_7_0_10  13 ArviZ PNG snapshots present in brain/belief/snapshots/
  check_7_0_11  RLS enabled on belief_dimensions/_evidence/_traces (prod only)

Mode split (mirrors verify_phase5 / verify_phase6 idiom):

  --mode code-complete (default)
      No live Supabase required. Uses TOML catalog, in-process PyMC, pytest
      sub-runs against brain/belief/tests/, and on-disk snapshots/.
      check_7_0_11 (RLS) returns SKIP — migration 016 not yet applied.

  --mode production
      Requires SUPABASE_DB_URL + migration 016 applied. Promotes
      check_7_0_02 to a `SELECT count(*) FROM belief_dimensions` query and
      runs check_7_0_11 (live pg_tables RLS introspection).

Usage:
    .venv-v7/Scripts/python.exe -m scripts.verify_phase_7_0
    .venv-v7/Scripts/python.exe -m scripts.verify_phase_7_0 --mode production
    .venv-v7/Scripts/python.exe -m scripts.verify_phase_7_0 --json
    .venv-v7/Scripts/python.exe -m scripts.verify_phase_7_0 --regression

Exit code: 0 if every non-SKIP check is PASS, else 1.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# Allow running this script both as a module (`python -m scripts.verify_phase_7_0`)
# and as a bare path (`python scripts/verify_phase_7_0.py`). The bare-path form
# does not put the project root on sys.path, so we add it explicitly.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PY = ROOT / ".venv-v7" / "Scripts" / "python.exe"
SNAPSHOT_DIR = ROOT / "brain" / "belief" / "snapshots"

EXPECTED_DIMS_COUNT = 13
EXPECTED_LIKELIHOOD_KINDS = 8
EXPECTED_PNG_MIN_SIZE = 5_000  # bytes
CITATION_MARKERS = ("PMID", "pubmed.ncbi.nlm.nih.gov", "doi.org", "10.", "github.com")


# ---------------------------------------------------------------------------
# Result + decorator scaffold
# ---------------------------------------------------------------------------
@dataclass
class CheckResult:
    id: str = ""
    description: str = ""
    status: str = "FAIL"  # PASS | FAIL | SKIP
    actual: str = ""
    expected: str = ""
    remediation: str = ""
    elapsed_s: float = 0.0


def check(
    check_id: str, description: str, mode_required: str = "any"
) -> Callable[[Callable[[str], CheckResult]], Callable[[str], CheckResult]]:
    """Wrap a check function with id binding, mode-gating, timing, error trap."""

    def deco(fn: Callable[[str], CheckResult]) -> Callable[[str], CheckResult]:
        def wrapper(mode: str) -> CheckResult:
            # Skip prod-only checks when running code-complete.
            if mode_required != "any" and mode != mode_required:
                return CheckResult(
                    id=check_id,
                    description=description,
                    status="SKIP",
                    remediation=f"requires --mode={mode_required}",
                    elapsed_s=0.0,
                )
            t0 = time.perf_counter()
            try:
                result = fn(mode)
            except Exception as exc:  # noqa: BLE001 — verifier surfaces every failure
                result = CheckResult(
                    status="FAIL",
                    actual=f"exception: {type(exc).__name__}: {exc}",
                    remediation="see traceback in caller log",
                )
            result.id = check_id
            result.description = description
            result.elapsed_s = time.perf_counter() - t0
            return result

        return wrapper

    return deco


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _run_pytest(node_ids: list[str], timeout: int = 180) -> tuple[int, str]:
    """Run pytest against specific node ids using the v7 venv; return (rc, tail)."""
    cmd = [str(PY), "-m", "pytest", *node_ids, "-q", "--tb=line", "--no-header"]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT)
    )
    tail = (proc.stdout or "").strip().splitlines()
    tail_str = "\n".join(tail[-6:]) if tail else (proc.stderr or "").strip()[-400:]
    return proc.returncode, tail_str


def _run_script(script: Path, timeout: int = 600) -> tuple[int, str]:
    """Run a v7 foundation_logs script with the v7 venv; return (rc, tail)."""
    proc = subprocess.run(
        [str(PY), str(script)],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(ROOT),
    )
    tail = (proc.stdout or "").strip().splitlines()
    tail_str = tail[-1] if tail else (proc.stderr or "").strip()[-200:]
    return proc.returncode, tail_str


# ---------------------------------------------------------------------------
# 11 checks
# ---------------------------------------------------------------------------
@check("check_7_0_01", "PyMC import + version (>=5.18 or 6.x)")
def check_pymc_version(mode: str) -> CheckResult:
    import pymc  # noqa: WPS433 — deferred until check runtime

    version = pymc.__version__
    parts = version.split(".")
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        return CheckResult(
            status="FAIL",
            actual=version,
            expected=">=5.18 or 6.x",
            remediation="uv add 'pymc>=5.18' --venv .venv-v7",
        )
    ok = (major >= 6) or (major == 5 and minor >= 18)
    if not ok:
        return CheckResult(
            status="FAIL",
            actual=version,
            expected=">=5.18 or 6.x",
            remediation="uv add 'pymc>=5.18' --venv .venv-v7",
        )
    return CheckResult(status="PASS", actual=version, expected=">=5.18 or 6.x")


@check("check_7_0_02", "13 dimensions registered (TOML or DB)")
def check_dim_count(mode: str) -> CheckResult:
    if mode == "production":
        import psycopg2  # noqa: WPS433

        dsn = os.environ.get("SUPABASE_DB_URL")
        if not dsn:
            return CheckResult(
                status="FAIL",
                actual="SUPABASE_DB_URL unset",
                expected="dsn",
                remediation="export SUPABASE_DB_URL or run with --mode code-complete",
            )
        with psycopg2.connect(dsn, sslmode="require") as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM belief_dimensions")
                n = int(cur.fetchone()[0])
        source = "belief_dimensions table"
    else:
        from brain.belief.schema import load_dimensions_from_toml  # noqa: WPS433

        n = len(load_dimensions_from_toml())
        source = "dimensions.toml"

    if n != EXPECTED_DIMS_COUNT:
        return CheckResult(
            status="FAIL",
            actual=f"{n} (from {source})",
            expected=str(EXPECTED_DIMS_COUNT),
            remediation="bootstrap catalog or re-run librarians A/B/C",
        )
    return CheckResult(
        status="PASS",
        actual=f"{n}/{EXPECTED_DIMS_COUNT} (from {source})",
        expected=str(EXPECTED_DIMS_COUNT),
    )


@check("check_7_0_03", "All 13 priors have primary-source citation (no TBD stubs)")
def check_citations(mode: str) -> CheckResult:
    from brain.belief.schema import (  # noqa: WPS433
        load_dimensions_from_toml,
        validate_dimension_catalog,
    )

    dims = load_dimensions_from_toml()
    report = validate_dimension_catalog(dims)

    if report.stubs_pending_citation:
        return CheckResult(
            status="FAIL",
            actual=(
                f"{len(report.stubs_pending_citation)} stub(s): "
                f"{report.stubs_pending_citation}"
            ),
            expected="0 stubs",
            remediation="run librarians A/B/C to clear TBD- citations",
        )

    bad = [
        d.name
        for d in dims
        if not any(marker in d.citation for marker in CITATION_MARKERS)
    ]
    if bad:
        return CheckResult(
            status="FAIL",
            actual=f"non-canonical citations: {bad}",
            expected="every citation has PMID|DOI|URL marker",
            remediation="hydrate citation field with PMID/DOI/URL",
        )

    return CheckResult(
        status="PASS",
        actual=f"{len(dims)}/{EXPECTED_DIMS_COUNT} with PubMed/DOI/URL markers",
    )


@check("check_7_0_04", "Beta-Binomial analytical match (delta < 0.005) — Day 4 script")
def check_analytical_sanity(mode: str) -> CheckResult:
    script = ROOT / "v7_architecture" / "foundation_logs" / "day_4_analytical_sanity.py"
    if not script.exists():
        return CheckResult(
            status="FAIL",
            actual="script missing",
            expected=str(script),
            remediation="restore v7_architecture/foundation_logs/day_4_analytical_sanity.py",
        )
    rc, tail = _run_script(script, timeout=180)
    if rc != 0:
        return CheckResult(
            status="FAIL",
            actual=f"exit={rc}; last: {tail}",
            expected="exit=0 (4/4 PASS)",
            remediation="see v7_architecture/foundation_logs/day_4_analytical_sanity.log",
        )
    return CheckResult(status="PASS", actual=f"Day 4 script exit 0 — {tail}")


@check(
    "check_7_0_05",
    "Sampler convergence rhat < 1.01 / ess_bulk > 400 across 13 dims — Day 10 sweep",
)
def check_convergence(mode: str) -> CheckResult:
    script = (
        ROOT / "v7_architecture" / "foundation_logs" / "day_10_sensitivity_sweep.py"
    )
    if not script.exists():
        return CheckResult(
            status="FAIL",
            actual="script missing",
            expected=str(script),
            remediation="restore v7_architecture/foundation_logs/day_10_sensitivity_sweep.py",
        )
    rc, tail = _run_script(script, timeout=900)
    if rc != 0:
        return CheckResult(
            status="FAIL",
            actual=f"exit={rc}; last: {tail}",
            expected="exit=0 (13/13 PASS)",
            remediation="see v7_architecture/foundation_logs/day_10_sensitivity_sweep.log",
        )
    return CheckResult(status="PASS", actual=f"Day 10 script exit 0 — {tail}")


@check(
    "check_7_0_06",
    "Idempotency: evidence_hash de-dupes update() calls",
)
def check_idempotency(mode: str) -> CheckResult:
    nodes = [
        "brain/belief/tests/test_update.py::test_update_returns_idempotent_hit_when_hash_exists",
        "brain/belief/tests/test_update.py::test_update_caches_after_first_call",
        "brain/belief/tests/test_update.py::test_update_idempotent_hit_skips_writes",
    ]
    rc, tail = _run_pytest(nodes, timeout=180)
    if rc != 0:
        return CheckResult(
            status="FAIL",
            actual=f"pytest exit={rc}; tail:\n{tail}",
            expected="3/3 pass",
            remediation="inspect brain/belief/update.py evidence_hash cache path",
        )
    return CheckResult(status="PASS", actual="3/3 idempotency tests pass")


@check("check_7_0_07", "Likelihood registry covers all 8 distribution kinds")
def check_likelihood_registry(mode: str) -> CheckResult:
    from brain.belief.likelihoods import LIKELIHOOD_REGISTRY  # noqa: WPS433

    n = len(LIKELIHOOD_REGISTRY)
    if n != EXPECTED_LIKELIHOOD_KINDS:
        return CheckResult(
            status="FAIL",
            actual=f"{n} kinds: {sorted(LIKELIHOOD_REGISTRY.keys())}",
            expected=str(EXPECTED_LIKELIHOOD_KINDS),
            remediation="restore missing likelihood functions in brain/belief/likelihoods.py",
        )
    return CheckResult(
        status="PASS",
        actual=f"{n} likelihoods: {sorted(LIKELIHOOD_REGISTRY.keys())}",
    )


@check(
    "check_7_0_08",
    "PosteriorDelta returned by update() end-to-end (beta-binomial)",
)
def check_posterior_delta(mode: str) -> CheckResult:
    nodes = [
        "brain/belief/tests/test_update.py::test_update_beta_binomial_end_to_end",
    ]
    rc, tail = _run_pytest(nodes, timeout=180)
    if rc != 0:
        return CheckResult(
            status="FAIL",
            actual=f"pytest exit={rc}; tail:\n{tail}",
            expected="1/1 pass",
            remediation="inspect brain/belief/update.py PosteriorDelta return path",
        )
    return CheckResult(
        status="PASS",
        actual="beta-binomial end-to-end update returns valid PosteriorDelta",
    )


@check(
    "check_7_0_09",
    "Adapters extract evidence from synthetic MRI + voice notes",
)
def check_evidence_adapters(mode: str) -> CheckResult:
    nodes = [
        "brain/belief/tests/test_adapters_mri.py",
        "brain/belief/tests/test_adapters_voice.py",
    ]
    rc, tail = _run_pytest(nodes, timeout=180)
    if rc != 0:
        return CheckResult(
            status="FAIL",
            actual=f"pytest exit={rc}; tail:\n{tail}",
            expected="all adapter tests pass",
            remediation="inspect brain/belief/adapters/{mri_report,voice_note}.py",
        )
    return CheckResult(
        status="PASS",
        actual="adapter tests pass (synthetic >=3 MRI + >=3 voice extractions)",
    )


@check(
    "check_7_0_10",
    "13 ArviZ PNG snapshots in brain/belief/snapshots/ (each > 5 KB)",
)
def check_snapshots(mode: str) -> CheckResult:
    if not SNAPSHOT_DIR.exists():
        return CheckResult(
            status="FAIL",
            actual=f"missing directory: {SNAPSHOT_DIR}",
            expected=f"{SNAPSHOT_DIR} with 13 *.png",
            remediation=f"{PY} -m brain.belief.viz",
        )
    pngs = sorted(SNAPSHOT_DIR.glob("*.png"))
    if len(pngs) != EXPECTED_DIMS_COUNT:
        return CheckResult(
            status="FAIL",
            actual=f"{len(pngs)} PNG(s) found",
            expected=f"{EXPECTED_DIMS_COUNT}",
            remediation=f"{PY} -m brain.belief.viz",
        )
    too_small = [p.name for p in pngs if p.stat().st_size < EXPECTED_PNG_MIN_SIZE]
    if too_small:
        return CheckResult(
            status="FAIL",
            actual=f"under {EXPECTED_PNG_MIN_SIZE} bytes: {too_small}",
            expected=f"every PNG >= {EXPECTED_PNG_MIN_SIZE} bytes",
            remediation="re-run brain.belief.viz; some renders failed",
        )
    total = sum(p.stat().st_size for p in pngs)
    avg = total // len(pngs)
    return CheckResult(
        status="PASS",
        actual=f"{len(pngs)} PNGs, total {total} bytes, avg {avg}/file",
    )


@check(
    "check_7_0_11",
    "RLS enabled on belief_dimensions / belief_evidence / belief_traces",
    mode_required="production",
)
def check_rls(mode: str) -> CheckResult:
    import psycopg2  # noqa: WPS433

    dsn = os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        return CheckResult(
            status="FAIL",
            actual="SUPABASE_DB_URL unset",
            expected="dsn",
            remediation="export SUPABASE_DB_URL before --mode production",
        )
    with psycopg2.connect(dsn, sslmode="require") as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tablename, rowsecurity
                FROM pg_tables
                WHERE schemaname='public'
                  AND tablename IN
                      ('belief_dimensions','belief_evidence','belief_traces')
                ORDER BY tablename
                """
            )
            rows = cur.fetchall()
    if len(rows) != 3:
        return CheckResult(
            status="FAIL",
            actual=f"found {len(rows)}/3 belief_* tables: {[r[0] for r in rows]}",
            expected="3 tables present",
            remediation="apply scripts/migrations/016_belief_tables.sql",
        )
    no_rls = [t for t, rls in rows if not rls]
    if no_rls:
        return CheckResult(
            status="FAIL",
            actual=f"RLS not enabled: {no_rls}",
            expected="rowsecurity=true on all 3 tables",
            remediation="re-apply RLS clauses from migration 016",
        )
    return CheckResult(
        status="PASS",
        actual="RLS enabled on belief_dimensions, belief_evidence, belief_traces",
    )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
CHECKS: list[Callable[[str], CheckResult]] = [
    check_pymc_version,
    check_dim_count,
    check_citations,
    check_analytical_sanity,
    check_convergence,
    check_idempotency,
    check_likelihood_registry,
    check_posterior_delta,
    check_evidence_adapters,
    check_snapshots,
    check_rls,
]


@dataclass
class Summary:
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == "PASS")

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == "SKIP")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == "FAIL")


def _print_result(r: CheckResult) -> None:
    marker = {"PASS": "[PASS]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}[r.status]
    print(f"{marker} {r.id}  {r.description}")
    if r.actual:
        print(f"         actual: {r.actual}")
    if r.expected and r.status != "PASS":
        print(f"         expect: {r.expected}")
    if r.status == "FAIL" and r.remediation:
        print(f"         fix:    {r.remediation}")
    if r.elapsed_s >= 0.5:
        print(f"         ({r.elapsed_s:.1f}s)")


MAIN_VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"


def _run_regression() -> None:
    print("\n=== REGRESSION (Phase 4 + 5 + 6) ===")
    # Prior-phase verifiers depend on the main `.venv` (boto3, psycopg2, etc.)
    # — NOT the isolated `.venv-v7` used for Bayesian work. They also import
    # `scripts.ledger`, so invocation MUST be `python -m scripts.verify_phaseN`.
    # `-X utf8` avoids cp1252 UnicodeEncodeError on Windows for arrow chars.
    if not MAIN_VENV_PY.exists():
        print(f"  main venv missing at {MAIN_VENV_PY} — regression skipped")
        return
    for module_name in (
        "scripts.verify_phase4",
        "scripts.verify_phase5",
        "scripts.verify_phase6",
    ):
        py_module_path = ROOT / module_name.replace(".", "/")
        if not py_module_path.with_suffix(".py").exists():
            print(f"  {module_name}: NOT FOUND (skipping)")
            continue
        proc = subprocess.run(
            [
                str(MAIN_VENV_PY),
                "-X",
                "utf8",
                "-m",
                module_name,
                "--mode",
                "code-complete",
            ],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(ROOT),
        )
        verdict = "GREEN" if proc.returncode == 0 else "RED"
        # Extract last summary line if available for context.
        tail_lines = (proc.stdout or "").strip().splitlines()
        summary = tail_lines[-1].strip() if tail_lines else ""
        print(f"  {module_name}: exit={proc.returncode}  [{verdict}]  {summary}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--mode",
        choices=["code-complete", "production"],
        default="code-complete",
        help="code-complete (default): no live DB. production: requires migration 016.",
    )
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON after summary"
    )
    parser.add_argument(
        "--regression",
        action="store_true",
        help="also run Phase 4/5/6 verifiers in code-complete mode",
    )
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print(f"=== verify_phase_7_0 (mode: {args.mode}) ===")

    summary = Summary()
    for ck in CHECKS:
        result = ck(args.mode)
        _print_result(result)
        summary.results.append(result)

    total = len(summary.results)
    verdict = "GREEN" if summary.failed == 0 else "RED"
    print(
        f"=== TOTAL {summary.passed}/{total} PASS "
        f"({summary.skipped} SKIP, {summary.failed} FAIL) ==="
    )
    print(f"=== {verdict} ===")

    if args.regression:
        _run_regression()

    if args.json:
        out = [
            {
                "id": r.id,
                "description": r.description,
                "status": r.status,
                "actual": r.actual,
                "expected": r.expected,
                "remediation": r.remediation,
                "elapsed_s": round(r.elapsed_s, 3),
            }
            for r in summary.results
        ]
        print(json.dumps(out, indent=2))

    return 0 if summary.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
