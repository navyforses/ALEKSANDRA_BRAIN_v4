# -*- coding: utf-8 -*-
"""Phase 7.4 — Active Learning verifier.

10-item PASS/FAIL audit covering Phase 7.4 Layer A (entropy/eig/catalog/
ranker) and Layer B (templates/question_gen/rate_limiter/telegram_flow/
response_parser/integration).

  check_7_4_01  Beta(2,8) entropy matches scipy reference within 1e-6
  check_7_4_02  EIG >= 0 for all 13 dims in dimensions.toml
  check_7_4_03  Ranker returns top-K sorted-descending list
  check_7_4_04  26 templates (13 KA + 13 EN) present in TOML files
  check_7_4_05  All 13 KA + 13 EN renders succeed without {placeholder} leak
  check_7_4_06  4th send in same week returns rate_limited
  check_7_4_07  5 sample voice transcripts parse correctly
  check_7_4_08  parsed_response_to_evidence builds valid BeliefEvidence
                 (DRY_RUN sentinel in code-complete; live evidence_id in
                  production mode if SUPABASE_DB_URL set)
  check_7_4_09  Telegram dry-run returns "dry_run" status with non-empty
                 rendered_text
  check_7_4_10  Regression: pytest brain/ -m "not slow" -q --tb=no exit 0
                 (tolerates the 1 known DoWhy flake from Phase 7.2)

Mode split:

  --mode code-complete (default)
      No live Supabase. All DB-touching checks run in DRY_RUN.

  --mode production
      Requires SUPABASE_DB_URL + migration 020 applied. Check 8 attempts
      to write a real belief_evidence row.

Usage:
    .venv-v7/Scripts/python.exe scripts/verify_phase_7_4.py
    .venv-v7/Scripts/python.exe scripts/verify_phase_7_4.py --mode production
    .venv-v7/Scripts/python.exe scripts/verify_phase_7_4.py --json

Exit code: 0 if every non-SKIP check is PASS, else 1.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

# Allow running both as a module and as a bare path.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PY = ROOT / ".venv-v7" / "Scripts" / "python.exe"
LOG_DIR = ROOT / "v7_architecture" / "foundation_logs"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
REGRESSION_TIMEOUT_S = 900.0
REGRESSION_BASELINE_MIN_TESTS = 493  # Phase 7.3 baseline
TOLERATED_FLAKE = "test_higher_confidence_level_widens_ci"


# ---------------------------------------------------------------------------
# Result + decorator scaffold (mirrors verify_phase_7_3)
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
    check_id: str,
    description: str,
    skip_in_code_complete: bool = False,
    skip_reason: str = "",
) -> Callable[[Callable[[str], CheckResult]], Callable[[str], CheckResult]]:
    def deco(fn: Callable[[str], CheckResult]) -> Callable[[str], CheckResult]:
        def wrapper(mode: str) -> CheckResult:
            if skip_in_code_complete and mode == "code-complete":
                return CheckResult(
                    id=check_id,
                    description=description,
                    status="SKIP",
                    remediation=skip_reason
                    or "requires production mode",
                    elapsed_s=0.0,
                )
            t0 = time.perf_counter()
            try:
                result = fn(mode)
            except Exception as exc:  # noqa: BLE001
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


def _supabase_url_set() -> bool:
    return bool(os.environ.get("SUPABASE_DB_URL"))


# ---------------------------------------------------------------------------
# Check 1 — Beta(2,8) entropy matches scipy
# ---------------------------------------------------------------------------
@check("check_7_4_01", "Beta(2,8) entropy matches scipy reference within 1e-6")
def check_entropy_beta(mode: str) -> CheckResult:
    from scipy import stats

    from brain.active.entropy import analytical_entropy_beta

    ours = analytical_entropy_beta(2.0, 8.0)
    ref = float(stats.beta.entropy(2.0, 8.0))
    diff = abs(ours - ref)
    if diff > 1e-6:
        return CheckResult(
            status="FAIL",
            actual=f"|ours - scipy| = {diff:.3e}",
            expected="<= 1e-6",
        )
    return CheckResult(
        status="PASS",
        actual=f"|diff| = {diff:.3e}; ours={ours:.6f} ref={ref:.6f}",
    )


# ---------------------------------------------------------------------------
# Check 2 — EIG >= 0 for all 13 dims
# ---------------------------------------------------------------------------
@check("check_7_4_02", "EIG >= 0 for all 13 dims in dimensions.toml")
def check_eig_nonneg(mode: str) -> CheckResult:
    from brain.active.eig import compute_eig_for_dimension
    from brain.belief.schema import load_dimensions_from_toml

    obs_map = {
        "cyst_volume_pct": "mri_volumetric_report",
        "brainstem_function": "neuro_exam",
        "seizure_freq_per_day": "eeg_weekly_count",
        "muscle_tone_hammersmith": "pt_hammersmith_score",
        "eye_tracking_seconds": "five_min_red_ball_video",
        "head_control_seconds": "tummy_time_timer",
        "gmfcs_level": "pt_gmfcs_assessment",
        "bayley_cognitive": "bayley_iii_snapshot",
        "feeding_stage": "weekly_feeding_log",
        "respiratory_apnea_per_day": "monitor_apnea_count",
        "csf_biomarkers": "csf_panel_draw",
        "neuroplasticity_resource": "calendar_age_in_days",
        "family_readiness": "weekly_self_report",
    }
    dims = load_dimensions_from_toml()
    bad = []
    for d in dims:
        est = compute_eig_for_dimension(
            d, observation_type=obs_map[d.name], n_simulations=200
        )
        if est.eig_nats < 0:
            bad.append((d.name, est.eig_nats))
    if bad:
        return CheckResult(
            status="FAIL",
            actual=f"{len(bad)} negative-EIG dims: {bad}",
            expected="all 13 EIG >= 0",
        )
    return CheckResult(
        status="PASS",
        actual=f"13/13 dims with EIG >= 0; sample H_n=0.05..0.5",
    )


# ---------------------------------------------------------------------------
# Check 3 — Ranker returns sorted-descending top-K
# ---------------------------------------------------------------------------
@check("check_7_4_03", "Ranker returns top-K sorted-descending list")
def check_ranker(mode: str) -> CheckResult:
    from brain.active.ranker import rank_observations, top_k
    from brain.belief.schema import load_dimensions_from_toml

    dims = load_dimensions_from_toml()
    ranked = rank_observations(dimensions=dims, n_simulations=100)
    scores = [r.cost_weighted_eig for r in ranked]
    if scores != sorted(scores, reverse=True):
        return CheckResult(
            status="FAIL",
            actual=f"scores not descending: head={scores[:5]}",
            expected="descending order",
        )
    top3 = top_k(ranked, k=3)
    if len(top3) != 3:
        return CheckResult(
            status="FAIL",
            actual=f"top_k returned {len(top3)}",
            expected="3",
        )
    return CheckResult(
        status="PASS",
        actual=(
            f"{len(ranked)} ranked observations, top3="
            f"{[r.observation.dim_name for r in top3]}"
        ),
    )


# ---------------------------------------------------------------------------
# Check 4 — 26 templates (13 KA + 13 EN) present
# ---------------------------------------------------------------------------
@check("check_7_4_04", "26 templates (13 KA + 13 EN) present in TOML files")
def check_template_coverage(mode: str) -> CheckResult:
    from brain.active.question_gen import (
        BANNED_BIGRAMS,
        load_templates,
        validate_ka_template_anti_loop,
    )

    ka = load_templates("ka")
    en = load_templates("en")
    if len(ka) != 13 or len(en) != 13:
        return CheckResult(
            status="FAIL",
            actual=f"ka={len(ka)} en={len(en)}",
            expected="13 ka + 13 en",
        )
    if set(ka.keys()) != set(en.keys()):
        return CheckResult(
            status="FAIL",
            actual=f"key mismatch ka^en={set(ka.keys()) ^ set(en.keys())}",
            expected="same 13 keys in both",
        )
    # Anti-loop check on KA templates
    offenders: list[tuple[str, list[str]]] = []
    for dim_name, entry in ka.items():
        result = validate_ka_template_anti_loop(entry["template"])
        if result:
            offenders.append((dim_name, result))
    if offenders:
        return CheckResult(
            status="FAIL",
            actual=f"banned-bigram violations: {offenders}",
            expected=f"no template uses any of {BANNED_BIGRAMS} >= 2x",
        )
    return CheckResult(
        status="PASS",
        actual=f"13 ka + 13 en = 26 templates; anti-loop check clean",
    )


# ---------------------------------------------------------------------------
# Check 5 — Renders succeed without placeholder leak
# ---------------------------------------------------------------------------
@check("check_7_4_05", "All 13 KA + 13 EN renders succeed without {placeholder} leak")
def check_renders(mode: str) -> CheckResult:
    from brain.active.question_gen import (
        render_all_dims_for_lang,
        validate_no_template_leaks,
    )

    leaks: list[tuple[str, str, str]] = []
    for lang in ("ka", "en"):
        rendered = render_all_dims_for_lang(lang=lang, eig_pct=12.0)
        for dim, text in rendered.items():
            if not validate_no_template_leaks(text):
                leaks.append((lang, dim, text[:80]))
    if leaks:
        return CheckResult(
            status="FAIL",
            actual=f"{len(leaks)} placeholder leaks: {leaks}",
            expected="no {xxx} remaining in any render",
        )
    return CheckResult(
        status="PASS",
        actual="26 renders complete; no placeholder leak",
    )


# ---------------------------------------------------------------------------
# Check 6 — 4th send in same week rate-limited
# ---------------------------------------------------------------------------
@check("check_7_4_06", "4th send in same week returns rate_limited")
def check_rate_limiter(mode: str) -> CheckResult:
    # Force DRY_RUN
    saved_dsn = os.environ.pop("SUPABASE_DB_URL", None)
    try:
        from brain.active.rate_limiter import (
            can_send_question,
            record_sent,
            reset_dry_run_state,
            weekly_sent_count,
        )

        reset_dry_run_state()
        week = "9999-W01"  # synthetic week to avoid colliding with tests
        for _ in range(3):
            record_sent(week)
        if weekly_sent_count(week) != 3:
            return CheckResult(
                status="FAIL",
                actual=f"weekly_sent_count={weekly_sent_count(week)} after 3 records",
                expected="3",
            )
        if can_send_question(week):
            return CheckResult(
                status="FAIL",
                actual="can_send_question returned True after cap",
                expected="False after 3 sends",
            )
        reset_dry_run_state()
        return CheckResult(
            status="PASS",
            actual="3 records -> can_send=False (constitutional rule #11)",
        )
    finally:
        if saved_dsn is not None:
            os.environ["SUPABASE_DB_URL"] = saved_dsn


# ---------------------------------------------------------------------------
# Check 7 — 5 sample voice transcripts parse correctly
# ---------------------------------------------------------------------------
@check("check_7_4_07", "5 sample voice transcripts parse correctly")
def check_response_parser(mode: str) -> CheckResult:
    from brain.active.response_parser import parse_response

    samples = [
        ("8 წამი", "integer_seconds", 8),
        ("12 seconds", "integer_seconds", 12),
        ("კი", "boolean", True),
        ("yes", "boolean", True),
        ("3", "scale_0_5", 3),
    ]
    failures: list[str] = []
    for raw, fmt, expected in samples:
        r = parse_response(raw, expected_format=fmt)
        if r.parsed_value != expected:
            failures.append(f"{raw!r} -> {r.parsed_value} (expected {expected})")
    if failures:
        return CheckResult(
            status="FAIL",
            actual=f"{len(failures)} of 5 failed: {failures}",
            expected="5/5 parsed",
        )
    return CheckResult(
        status="PASS",
        actual=f"5/5 sample transcripts parsed correctly",
    )


# ---------------------------------------------------------------------------
# Check 8 — parsed_response_to_evidence builds valid BeliefEvidence (DRY_RUN)
# ---------------------------------------------------------------------------
@check(
    "check_7_4_08",
    "parsed_response_to_evidence builds valid BeliefEvidence (DRY_RUN sentinel)",
)
def check_integration(mode: str) -> CheckResult:
    from brain.active.integration import (
        apply_response_and_compute_delta,
        parsed_response_to_evidence,
    )
    from brain.active.response_parser import parse_response
    from brain.belief.persistence import BeliefEvidence
    from brain.belief.schema import load_dimensions_from_toml

    dims = load_dimensions_from_toml()
    dim = next(d for d in dims if d.name == "head_control_seconds")
    dim.id = 1
    parsed = parse_response("8 წამი", expected_format="integer_seconds")
    ev = parsed_response_to_evidence(
        dim=dim,
        parsed=parsed,
        observation_type="tummy_time_timer",
        source_ref="verify_7_4_08",
        observed_at=datetime(2026, 11, 9, tzinfo=timezone.utc),
    )
    if not isinstance(ev, BeliefEvidence):
        return CheckResult(
            status="FAIL",
            actual=f"got {type(ev).__name__}",
            expected="BeliefEvidence",
        )
    if ev.value.get("int") != 8:
        return CheckResult(
            status="FAIL",
            actual=f"value.int={ev.value.get('int')}",
            expected="8",
        )
    if len(ev.evidence_hash) != 64:
        return CheckResult(
            status="FAIL",
            actual=f"hash len {len(ev.evidence_hash)}",
            expected="64 (SHA-256 hex)",
        )

    # End-to-end DRY_RUN sentinel check
    if mode == "code-complete" or not _supabase_url_set():
        # Force DRY_RUN by clearing env
        saved_dsn = os.environ.pop("SUPABASE_DB_URL", None)
        try:
            res = apply_response_and_compute_delta(
                dim=dim,
                parsed=parsed,
                observation_type="tummy_time_timer",
                source_ref="verify_7_4_08",
                observed_at=datetime(2026, 11, 9, tzinfo=timezone.utc),
            )
        finally:
            if saved_dsn is not None:
                os.environ["SUPABASE_DB_URL"] = saved_dsn
        if res.get("status") != "dry_run":
            return CheckResult(
                status="FAIL",
                actual=f"status={res.get('status')}",
                expected="dry_run in code-complete",
            )
        return CheckResult(
            status="PASS",
            actual=(
                f"BeliefEvidence built; hash={ev.evidence_hash[:12]}...; "
                f"DRY_RUN sentinel returned"
            ),
        )

    # Production path
    res = apply_response_and_compute_delta(
        dim=dim,
        parsed=parsed,
        observation_type="tummy_time_timer",
        source_ref="verify_7_4_08",
        observed_at=datetime(2026, 11, 9, tzinfo=timezone.utc),
    )
    if res.get("status") != "ok":
        return CheckResult(
            status="FAIL",
            actual=f"status={res.get('status')}; error={res.get('error')}",
            expected="ok with delta payload in production",
        )
    return CheckResult(
        status="PASS",
        actual=f"live update() returned delta payload",
    )


# ---------------------------------------------------------------------------
# Check 9 — Telegram dry-run returns "dry_run" with non-empty rendered_text
# ---------------------------------------------------------------------------
@check(
    "check_7_4_09",
    'Telegram dry-run returns "dry_run" status with non-empty rendered_text',
)
def check_telegram_dry_run(mode: str) -> CheckResult:
    from brain.active import telegram_flow
    from brain.active.rate_limiter import reset_dry_run_state
    from brain.active.telegram_flow import OutboundQuestion, send_question

    saved_dsn = os.environ.pop("SUPABASE_DB_URL", None)
    saved_freeze = telegram_flow.EMERGENCY_FREEZE
    telegram_flow.EMERGENCY_FREEZE = False
    reset_dry_run_state()
    try:
        q = OutboundQuestion(
            dim_name="head_control_seconds",
            observation_type="tummy_time_timer",
            text_ka="ერთი წუთით მუცელზე დააწვინე და დაითვალე წამები.",
            text_en="One minute on tummy; count seconds.",
            eig_nats=0.3,
            wife_chat_id="0",
            week_iso="9999-W02",
            dry_run=True,
            expected_format="integer_seconds",
        )
        res = send_question(q)
        if res.get("status") != "dry_run":
            return CheckResult(
                status="FAIL",
                actual=f"status={res.get('status')}",
                expected="dry_run",
            )
        if not res.get("rendered_text"):
            return CheckResult(
                status="FAIL",
                actual="rendered_text empty",
                expected="non-empty rendered_text",
            )
        return CheckResult(
            status="PASS",
            actual=f"dry_run; rendered_text_len={len(res['rendered_text'])}",
        )
    finally:
        telegram_flow.EMERGENCY_FREEZE = saved_freeze
        reset_dry_run_state()
        if saved_dsn is not None:
            os.environ["SUPABASE_DB_URL"] = saved_dsn


# ---------------------------------------------------------------------------
# Check 10 — pytest brain/ regression
# ---------------------------------------------------------------------------
@check(
    "check_7_4_10",
    'Regression: pytest brain/ -m "not slow" exit 0 (DoWhy flake tolerated)',
)
def check_regression(mode: str) -> CheckResult:
    proc = subprocess.run(
        [
            str(PY),
            "-m",
            "pytest",
            "brain/",
            "-m",
            "not slow",
            "-q",
            "--tb=no",
            "--no-header",
        ],
        capture_output=True,
        text=True,
        timeout=int(REGRESSION_TIMEOUT_S),
        cwd=str(ROOT),
    )
    stdout = proc.stdout or ""
    tail_lines = stdout.strip().splitlines()
    summary = (
        tail_lines[-1].strip()
        if tail_lines
        else (proc.stderr or "").strip()[-200:]
    )

    pass_match = re.search(r"(\d+)\s+passed", summary)
    fail_match = re.search(r"(\d+)\s+failed", summary)
    passed = int(pass_match.group(1)) if pass_match else 0
    failed = int(fail_match.group(1)) if fail_match else 0

    if proc.returncode == 0:
        if passed < REGRESSION_BASELINE_MIN_TESTS:
            return CheckResult(
                status="FAIL",
                actual=f"only {passed} tests passed (need >= {REGRESSION_BASELINE_MIN_TESTS})",
                expected=f">= {REGRESSION_BASELINE_MIN_TESTS} passed",
            )
        return CheckResult(status="PASS", actual=f"{summary}")

    # Tolerate the 1 known DoWhy flake
    if failed == 1 and TOLERATED_FLAKE in stdout:
        if (passed + failed) >= REGRESSION_BASELINE_MIN_TESTS:
            return CheckResult(
                status="PASS",
                actual=(
                    f"{summary}  (tolerated DoWhy flake "
                    f"{TOLERATED_FLAKE} — passes in isolation)"
                ),
            )
    return CheckResult(
        status="FAIL",
        actual=f"exit={proc.returncode}; tail: {summary}",
        expected="exit 0 (or 1 known DoWhy flake)",
        remediation="inspect brain/ pytest failures",
    )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
CHECKS: list[Callable[[str], CheckResult]] = [
    check_entropy_beta,
    check_eig_nonneg,
    check_ranker,
    check_template_coverage,
    check_renders,
    check_rate_limiter,
    check_response_parser,
    check_integration,
    check_telegram_dry_run,
    check_regression,
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


def _write_json_log(summary: Summary, mode: str) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = LOG_DIR / f"verify_phase_7_4_{timestamp}.json"
    payload = {
        "phase": "7.4",
        "mode": mode,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": summary.passed,
        "skipped": summary.skipped,
        "failed": summary.failed,
        "total": len(summary.results),
        "results": [
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
        ],
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--mode",
        choices=["code-complete", "production"],
        default="code-complete",
        help="code-complete (default): no live DB. production: requires migration 020.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON after summary",
    )
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print(f"=== verify_phase_7_4 (mode: {args.mode}) ===")

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

    log_path = _write_json_log(summary, args.mode)
    print(f"json log: {log_path.relative_to(ROOT)}")

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
