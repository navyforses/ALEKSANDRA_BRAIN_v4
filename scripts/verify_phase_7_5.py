# -*- coding: utf-8 -*-
"""Phase 7.5 - Constitutional Code verifier.

14-item PASS/FAIL audit covering the 13 inviolable rules plus the
meta override-flow check.

  check_7_5_01  Rule #1 MRI client-only  (CSP + DICOM rejector in
                viewer/middleware.ts)
  check_7_5_02  Rule #2 Voice review     (DB trigger in migration 021)
  check_7_5_03  Rule #3 Citation required (Pydantic strict schema)
  check_7_5_04  Rule #4 CI required       (output formatter)
  check_7_5_05  Rule #5 Bilingual parity  (i18n guard)
  check_7_5_06  Rule #6 PHI filter        (pre-prompt regex)
  check_7_5_07  Rule #7 Budget hard stop  (LiteLLM gate)
  check_7_5_08  Rule #8 Belief evidence   (PyMC update guard)
  check_7_5_09  Rule #9 Hypothesis >=3     (Postgres CHECK in migration 022)
  check_7_5_10  Rule #10 Sim uncertainty  (pre-flight constitutional check)
  check_7_5_11  Rule #11 Question cap     (DB CHECK+trigger in migration 022b)
  check_7_5_12  Rule #12 PDF >=5 primary   (pdf_guard)
  check_7_5_13  Rule #13 Verifier CI gate (GH Actions YAML)
  check_7_5_14  Meta override flow        (constitutional_overrides table /
                                            DRY_RUN in code-complete)

Mode split:

  --mode code-complete (default)
      No live Supabase. Checks 2, 9, 11, 14 SKIP (DB migrations not yet
      applied); the other 10 run pure Python and PASS / FAIL.
      Target: 10 PASS / 4 SKIP / 0 FAIL -> GREEN exit 0.

  --mode production
      Requires SUPABASE_DB_URL + migrations 021/022/022b/023 applied.
      All 14 checks attempt live infra ops.

Usage:
    .venv-v7/Scripts/python.exe scripts/verify_phase_7_5.py
    .venv-v7/Scripts/python.exe scripts/verify_phase_7_5.py --mode production
    .venv-v7/Scripts/python.exe scripts/verify_phase_7_5.py --json

Exit code: 0 if every non-SKIP check is PASS, else 1.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

# Allow running both as a module and as a bare path.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Result + decorator scaffold (mirrors verify_phase_7_4)
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
                    remediation=skip_reason or "requires production mode",
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
# Check 1 - Rule #1 MRI client-only (structural)
# ---------------------------------------------------------------------------
@check(
    "check_7_5_01",
    "Rule #1 - viewer/middleware.ts ships CSP + DICOM POST rejector",
)
def check_rule_1_mri_client_only(mode: str) -> CheckResult:
    mw = ROOT / "viewer" / "middleware.ts"
    if not mw.exists():
        return CheckResult(
            status="FAIL",
            actual="viewer/middleware.ts missing",
            expected="present with CSP + DICOM-reject logic",
            remediation="re-run Phase 7.5 Day 1 - create viewer/middleware.ts",
        )
    src = mw.read_text(encoding="utf-8")
    missing = []
    if "Content-Security-Policy" not in src:
        missing.append("Content-Security-Policy header")
    if "application/dicom" not in src:
        missing.append("application/dicom MIME rejector")
    if "415" not in src:
        missing.append("HTTP 415 response code")
    if missing:
        return CheckResult(
            status="FAIL",
            actual=f"middleware.ts missing: {missing}",
            expected="CSP + DICOM-reject + 415 status present",
        )
    return CheckResult(
        status="PASS",
        actual=f"middleware.ts {len(src)} bytes - CSP, DICOM rejector, 415 all present",
    )


# ---------------------------------------------------------------------------
# Check 2 - Rule #2 Voice review required (DB trigger; SKIP in code-complete)
# ---------------------------------------------------------------------------
@check(
    "check_7_5_02",
    "Rule #2 - INSERT voice intake row -> trigger sets requires_review=true",
    skip_in_code_complete=True,
    skip_reason="DB migration 021 not yet applied (SUPABASE_DB_URL unset / no live DB)",
)
def check_rule_2_voice_review(mode: str) -> CheckResult:
    if not _supabase_url_set():
        return CheckResult(
            status="SKIP",
            remediation="set SUPABASE_DB_URL + apply migration 021",
        )
    try:
        import psycopg2  # type: ignore
    except Exception:
        return CheckResult(
            status="FAIL",
            actual="psycopg2 not importable",
            remediation="pip install psycopg2-binary",
        )
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO intake_drops (source, payload, requires_review)
                VALUES ('voice', '{"transcript":"verifier_smoke"}'::jsonb, false)
                RETURNING requires_review
                """
            )
            row = cur.fetchone()
            cur.execute(
                "DELETE FROM intake_drops "
                "WHERE payload @> '{\"transcript\":\"verifier_smoke\"}'::jsonb"
            )
        conn.commit()
    finally:
        conn.close()
    if not row or not bool(row[0]):
        return CheckResult(
            status="FAIL",
            actual=f"requires_review = {row[0] if row else None}",
            expected="true (trigger should have overridden)",
        )
    return CheckResult(
        status="PASS",
        actual="trigger fired: requires_review = true after INSERT(false)",
    )


# ---------------------------------------------------------------------------
# Check 3 - Rule #3 Citation mandatory
# ---------------------------------------------------------------------------
@check("check_7_5_03", "Rule #3 - Recommendation without citation raises ValidationError")
def check_rule_3_citation(mode: str) -> CheckResult:
    from pydantic import ValidationError

    from brain.common.guards import Recommendation

    try:
        Recommendation(
            subject="bogus",
            expected_value=0.5,
            ci_low=0.4,
            ci_high=0.6,
            language="en",
        )  # type: ignore[call-arg]
    except ValidationError:
        # Also confirm a valid one passes.
        ok = Recommendation(
            subject="vigabatrin",
            expected_value=0.5,
            ci_low=0.4,
            ci_high=0.6,
            citation="PMID:7686614 valid",
            language="en",
        )
        return CheckResult(
            status="PASS",
            actual=f"no-citation rejected; valid {ok.subject!r} accepted",
        )
    return CheckResult(
        status="FAIL",
        actual="Recommendation(no citation) did NOT raise",
        expected="ValidationError",
    )


# ---------------------------------------------------------------------------
# Check 4 - Rule #4 CI required
# ---------------------------------------------------------------------------
@check("check_7_5_04", "Rule #4 - payload with expected_value but no ci_low/ci_high rejected")
def check_rule_4_ci(mode: str) -> CheckResult:
    from brain.common.guards import MissingCIError, reject_output_without_ci

    try:
        reject_output_without_ci({"expected_value": 0.7})
    except MissingCIError:
        # Full payload must pass.
        reject_output_without_ci(
            {"expected_value": 0.7, "ci_low": 0.5, "ci_high": 0.9}
        )
        return CheckResult(
            status="PASS",
            actual="naked expected_value rejected; full payload accepted",
        )
    return CheckResult(
        status="FAIL",
        actual="reject_output_without_ci did NOT raise on naked payload",
        expected="MissingCIError",
    )


# ---------------------------------------------------------------------------
# Check 5 - Rule #5 Bilingual parity
# ---------------------------------------------------------------------------
@check("check_7_5_05", "Rule #5 - en-only payload rejected; {en,ka} JSONB accepted")
def check_rule_5_parity(mode: str) -> CheckResult:
    from brain.common.guards import BilingualParityError, require_bilingual_parity

    try:
        require_bilingual_parity({"title": {"en": "x"}})
    except BilingualParityError:
        require_bilingual_parity({"title": {"en": "x", "ka": "ჯ"}})
        return CheckResult(
            status="PASS",
            actual="en-only payload rejected; {en,ka} accepted",
        )
    return CheckResult(
        status="FAIL",
        actual="require_bilingual_parity did NOT raise on en-only",
        expected="BilingualParityError",
    )


# ---------------------------------------------------------------------------
# Check 6 - Rule #6 PHI filter
# ---------------------------------------------------------------------------
@check("check_7_5_06", "Rule #6 - MRN + doctor name redacted before send")
def check_rule_6_phi(mode: str) -> CheckResult:
    from brain.common.guards import redact_phi

    text = "MRN: 7616818 - followup with Dr. Hien on Friday"
    redacted, matches = redact_phi(text)
    if "7616818" in redacted or "Hien" in redacted:
        return CheckResult(
            status="FAIL",
            actual=f"redaction leaked - len(matches)={len(matches)}",
            expected="MRN + name redacted",
        )
    if len(matches) < 2:
        return CheckResult(
            status="FAIL",
            actual=f"only {len(matches)} match(es); expected >= 2",
            expected="MRN match + doctor_name match",
        )
    return CheckResult(
        status="PASS",
        actual=f"{len(matches)} PHI matches redacted",
    )


# ---------------------------------------------------------------------------
# Check 7 - Rule #7 Budget hard stop
# ---------------------------------------------------------------------------
@check("check_7_5_07", "Rule #7 - daily-cap breach raises BudgetError")
def check_rule_7_budget(mode: str) -> CheckResult:
    from brain.common.guards import (
        BudgetError,
        DAILY_BUDGET_USD,
        check_budget_before_call,
    )

    try:
        check_budget_before_call(
            daily_spend=DAILY_BUDGET_USD - 0.01,
            monthly_spend=10.0,
            estimated_call_cost=0.10,
        )
    except BudgetError:
        # In-budget call must pass.
        check_budget_before_call(
            daily_spend=1.0,
            monthly_spend=10.0,
            estimated_call_cost=0.05,
        )
        return CheckResult(
            status="PASS",
            actual=f"daily-cap breach raised; daily cap = ${DAILY_BUDGET_USD:.2f}",
        )
    return CheckResult(
        status="FAIL",
        actual="check_budget_before_call did NOT raise on cap breach",
        expected="BudgetError",
    )


# ---------------------------------------------------------------------------
# Check 8 - Rule #8 Belief requires evidence
# ---------------------------------------------------------------------------
@check("check_7_5_08", "Rule #8 - update(evidence=None) raises BeliefWithoutEvidenceError")
def check_rule_8_belief_evidence(mode: str) -> CheckResult:
    from brain.belief.update import update
    from brain.common.guards import BeliefWithoutEvidenceError

    try:
        update(evidence=None)  # type: ignore[arg-type]
    except BeliefWithoutEvidenceError:
        return CheckResult(
            status="PASS",
            actual="update(None) raised BeliefWithoutEvidenceError as expected",
        )
    return CheckResult(
        status="FAIL",
        actual="update(None) did NOT raise",
        expected="BeliefWithoutEvidenceError",
    )


# ---------------------------------------------------------------------------
# Check 9 - Rule #9 Hypothesis constraint (DB CHECK; SKIP in code-complete)
# ---------------------------------------------------------------------------
@check(
    "check_7_5_09",
    "Rule #9 - UPDATE hypotheses status=confirmed with <3 supporting_papers rejected",
    skip_in_code_complete=True,
    skip_reason="DB migration 022 not yet applied",
)
def check_rule_9_hypothesis(mode: str) -> CheckResult:
    if not _supabase_url_set():
        return CheckResult(
            status="SKIP",
            remediation="set SUPABASE_DB_URL + apply migration 022",
        )
    import psycopg2  # type: ignore

    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO hypotheses (title, status, supporting_papers)
                    VALUES ('verifier_smoke',
                            'confirmed',
                            '["PMID:1","PMID:2"]'::jsonb)
                    """
                )
                conn.rollback()
                return CheckResult(
                    status="FAIL",
                    actual="INSERT confirmed + 2 papers SUCCEEDED",
                    expected="violates min_sources_when_confirmed",
                )
            except psycopg2.errors.CheckViolation:
                conn.rollback()
                return CheckResult(
                    status="PASS",
                    actual="confirmed + 2 papers rejected by constraint",
                )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Check 10 - Rule #10 Simulation uncertainty
# ---------------------------------------------------------------------------
@check(
    "check_7_5_10",
    "Rule #10 - synthetic catalog with sd/mean=1.0 raises BudgetGuardError",
)
def check_rule_10_sim_uncertainty(mode: str) -> CheckResult:
    from brain.belief.persistence import BeliefDimension
    from brain.belief.schema import load_dimensions_from_toml
    from brain.sim.api import (
        BudgetGuardError,
        check_simulation_uncertainty_constitutional,
    )
    from brain.sim.scenario import Scenario

    synthetic_dims = [
        BeliefDimension(
            id=i,
            name=f"synthetic_{i}",
            distribution="normal",
            prior_params={"mu": 0.001, "sigma": 1.0},
            valid_min=None,
            valid_max=None,
            citation="PMID:7686614 synthetic test dimension",
        )
        for i in range(1, 14)
    ]
    real_dims = load_dimensions_from_toml()
    scenario = Scenario(
        name="verifier_smoke_rule10",
        description="Phase 7.5 verifier check 10",
        interventions=[],
        horizon_days=30,
        n_samples=100,
        outcomes=[real_dims[0].name],
    )
    try:
        check_simulation_uncertainty_constitutional(
            scenario, dims=synthetic_dims
        )
    except BudgetGuardError:
        return CheckResult(
            status="PASS",
            actual="synthetic high-uncertainty catalog rejected",
        )
    return CheckResult(
        status="FAIL",
        actual="check_simulation_uncertainty_constitutional did NOT raise",
        expected="BudgetGuardError",
    )


# ---------------------------------------------------------------------------
# Check 11 - Rule #11 Question rate cap (DB; SKIP in code-complete)
# ---------------------------------------------------------------------------
@check(
    "check_7_5_11",
    "Rule #11 - 4th INSERT/UPDATE in same week triggers cap rejection",
    skip_in_code_complete=True,
    skip_reason="DB migration 022b not yet applied",
)
def check_rule_11_rate_cap(mode: str) -> CheckResult:
    if not _supabase_url_set():
        return CheckResult(
            status="SKIP",
            remediation="set SUPABASE_DB_URL + apply migration 022b",
        )
    import psycopg2  # type: ignore

    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], sslmode="require")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO active_rate_log (week_iso, questions_sent, cap) "
                "VALUES ('verifier_W99', 0, 3) "
                "ON CONFLICT (week_iso) DO UPDATE SET questions_sent = 0"
            )
            try:
                cur.execute(
                    "UPDATE active_rate_log SET questions_sent = 4 "
                    "WHERE week_iso = 'verifier_W99'"
                )
                cur.execute(
                    "DELETE FROM active_rate_log WHERE week_iso='verifier_W99'"
                )
                conn.commit()
                return CheckResult(
                    status="FAIL",
                    actual="UPDATE to questions_sent=4 SUCCEEDED",
                    expected="trigger raises Rule #11 errcode 23514",
                )
            except (psycopg2.errors.CheckViolation, psycopg2.errors.RaiseException):
                conn.rollback()
                cur.execute(
                    "DELETE FROM active_rate_log WHERE week_iso='verifier_W99'"
                )
                conn.commit()
                return CheckResult(
                    status="PASS",
                    actual="UPDATE 4 rejected (CHECK + trigger fired)",
                )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Check 12 - Rule #12 PDF >=5 primary sources
# ---------------------------------------------------------------------------
@check(
    "check_7_5_12",
    "Rule #12 - assert_min_primary_sources rejects 4-source payload",
)
def check_rule_12_pdf(mode: str) -> CheckResult:
    from brain.common.guards import (
        InsufficientSourcesError,
        assert_min_primary_sources,
    )

    bad_cites = ["note A", "note B", "note C", "note D",
                 "https://pubmed.ncbi.nlm.nih.gov/7686614/"]
    try:
        assert_min_primary_sources(bad_cites)
    except InsufficientSourcesError:
        good_cites = [
            f"https://pubmed.ncbi.nlm.nih.gov/{i}/" for i in range(1, 6)
        ]
        assert_min_primary_sources(good_cites)
        return CheckResult(
            status="PASS",
            actual="4 mixed rejected; 5 PubMed accepted",
        )
    return CheckResult(
        status="FAIL",
        actual="assert_min_primary_sources did NOT raise on 4 cites",
        expected="InsufficientSourcesError",
    )


# ---------------------------------------------------------------------------
# Check 13 - Rule #13 Verifier CI gate (structural)
# ---------------------------------------------------------------------------
@check("check_7_5_13", "Rule #13 - verify_all.yml runs all 6 phase verifiers")
def check_rule_13_ci_gate(mode: str) -> CheckResult:
    yml = ROOT / ".github" / "workflows" / "verify_all.yml"
    if not yml.exists():
        return CheckResult(
            status="FAIL",
            actual="verify_all.yml missing",
            expected=".github/workflows/verify_all.yml with 6 verifier invocations",
        )
    src = yml.read_text(encoding="utf-8")
    needed = [
        "verify_phase_7_0.py",
        "verify_phase_7_1.py",
        "verify_phase_7_2.py",
        "verify_phase_7_3.py",
        "verify_phase_7_4.py",
        "verify_phase_7_5.py",
    ]
    missing = [v for v in needed if v not in src]
    if missing:
        return CheckResult(
            status="FAIL",
            actual=f"workflow missing: {missing}",
            expected="all 6 verifier scripts in run command",
        )
    return CheckResult(
        status="PASS",
        actual="verify_all.yml references all 6 phase verifiers",
    )


# ---------------------------------------------------------------------------
# Check 14 - Meta: override audit flow
# ---------------------------------------------------------------------------
@check(
    "check_7_5_14",
    "Meta - issue_override returns DRY_RUN sentinel; reason-length enforced",
)
def check_rule_meta_override(mode: str) -> CheckResult:
    from pydantic import ValidationError

    from brain.common.guards import (
        is_rule_currently_overridden,
        issue_override,
        list_active_overrides,
    )

    os.environ.pop("SUPABASE_DB_URL", None) if mode == "code-complete" else None

    sentinel = issue_override(
        rule_number=9,
        reason="verifier smoke - backfill window for confirmed hypotheses",
        overridden_by="verifier",
        notify_wife=False,
    )
    if mode == "code-complete":
        if not sentinel.startswith("DRY_RUN:"):
            return CheckResult(
                status="FAIL",
                actual=f"got {sentinel!r}",
                expected="DRY_RUN sentinel",
            )

    # Short reason must reject.
    try:
        issue_override(
            rule_number=9,
            reason="short",
            overridden_by="verifier",
            notify_wife=False,
        )
        return CheckResult(
            status="FAIL",
            actual="short reason did NOT raise",
            expected="ValidationError",
        )
    except ValidationError:
        pass

    if mode == "code-complete":
        if list_active_overrides() != []:
            return CheckResult(
                status="FAIL",
                actual="DRY_RUN list_active_overrides not empty",
                expected="[]",
            )
        if is_rule_currently_overridden(9) is not False:
            return CheckResult(
                status="FAIL",
                actual="DRY_RUN is_rule_currently_overridden(9) not False",
                expected="False",
            )

    return CheckResult(
        status="PASS",
        actual=(
            f"sentinel={sentinel} (DRY_RUN)" if mode == "code-complete"
            else f"row={sentinel}; reason-length enforced"
        ),
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
ALL_CHECKS: list[Callable[[str], CheckResult]] = [
    check_rule_1_mri_client_only,
    check_rule_2_voice_review,
    check_rule_3_citation,
    check_rule_4_ci,
    check_rule_5_parity,
    check_rule_6_phi,
    check_rule_7_budget,
    check_rule_8_belief_evidence,
    check_rule_9_hypothesis,
    check_rule_10_sim_uncertainty,
    check_rule_11_rate_cap,
    check_rule_12_pdf,
    check_rule_13_ci_gate,
    check_rule_meta_override,
]


def run_all(mode: str) -> list[CheckResult]:
    results: list[CheckResult] = []
    for fn in ALL_CHECKS:
        results.append(fn(mode))
    return results


def emit_human(results: list[CheckResult], mode: str) -> None:
    print(f"\nPhase 7.5 Constitutional Code verifier - mode={mode}")
    print("=" * 80)
    for r in results:
        marker = {"PASS": "[PASS]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}.get(
            r.status, "[????]"
        )
        print(f"{marker} {r.id} ({r.elapsed_s:5.2f}s)  {r.description}")
        if r.actual:
            print(f"           actual:      {r.actual}")
        if r.expected:
            print(f"           expected:    {r.expected}")
        if r.remediation:
            print(f"           remediation: {r.remediation}")
    n_pass = sum(1 for r in results if r.status == "PASS")
    n_fail = sum(1 for r in results if r.status == "FAIL")
    n_skip = sum(1 for r in results if r.status == "SKIP")
    print("=" * 80)
    print(
        f"Summary: {n_pass} PASS / {n_skip} SKIP / {n_fail} FAIL "
        f"(total {len(results)})"
    )


def emit_json(results: list[CheckResult], mode: str) -> None:
    payload = {
        "phase": "7.5",
        "mode": mode,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": [r.__dict__ for r in results],
        "summary": {
            "pass": sum(1 for r in results if r.status == "PASS"),
            "fail": sum(1 for r in results if r.status == "FAIL"),
            "skip": sum(1 for r in results if r.status == "SKIP"),
            "total": len(results),
        },
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 7.5 verifier")
    parser.add_argument(
        "--mode",
        choices=("code-complete", "production"),
        default="code-complete",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    results = run_all(args.mode)
    if args.json:
        emit_json(results, args.mode)
    else:
        emit_human(results, args.mode)

    # Exit 0 if every non-SKIP check is PASS; else 1.
    n_fail = sum(1 for r in results if r.status == "FAIL")
    return 1 if n_fail > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
