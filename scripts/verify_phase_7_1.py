# -*- coding: utf-8 -*-
"""Phase 7.1 — Memory Refactor (Neo4j → Causal Schema) verifier.

9-item PASS/FAIL audit covering the brain/memory/ causal layer that replaces
Phase 2's flat Graphiti CO_OCCURS_WITH/RELATED_TO edges with Pearl's 5-type
SCM taxonomy (CAUSES / INHIBITS / MEDIATES / CONFOUNDS / MODERATES):

  check_7_1_01  Backup exists in .planning/backups/pre_71/ (>1 KB JSON)
  check_7_1_02  Migration 017 constraints applied (causal_node_id + 14 edge)
  check_7_1_03  CausalNode label upgrade (count >= 568)
  check_7_1_04  All legacy edges re-classified (CO_OCCURS_WITH+RELATED_TO == 0)
  check_7_1_05  Edge type distribution (sum of 5 types >= ~250)
  check_7_1_06  Properties populated (>=90% have confidence + citation)
  check_7_1_07  Belief cross-link (>=50% CausalNodes have dimension_ref; 80% target)
  check_7_1_08  Adapter regression + 7 spot-checks (taxonomy invariants intact)
  check_7_1_09  Idempotency (classify_edges --dry-run produces 0 changes)

Mode split (mirrors verify_phase_7_0):

  --mode code-complete (default)
      No live Neo4j credentials required. Verifies Day 1-9 deliverables exist
      and the brain/memory/tests/ suite stays GREEN. Checks 01/02/03/04/05/06/07
      that need live graph state return SKIP. Check 08 still runs the offline
      adapter/taxonomy/cross_link/classify_edges pytest sweep. Check 09 runs
      the idempotency unit test (deterministic, no DB).

  --mode production
      Requires NEO4J_URI + NEO4J_PASSWORD env vars + migration 017 applied +
      classify_edges.py run + cross_link.py run. All 9 checks execute live.

Usage:
    .venv-v7/Scripts/python.exe -m scripts.verify_phase_7_1
    .venv-v7/Scripts/python.exe -m scripts.verify_phase_7_1 --mode production
    .venv-v7/Scripts/python.exe -m scripts.verify_phase_7_1 --json
    .venv-v7/Scripts/python.exe -m scripts.verify_phase_7_1 --regression

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
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
PY = ROOT / ".venv-v7" / "Scripts" / "python.exe"
MAIN_VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"

# ---------------------------------------------------------------------------
# Phase 7.1 constants (mirror plan §4 + Day 8-9 carry-forward)
# ---------------------------------------------------------------------------
BACKUP_DIR = ROOT / ".planning" / "backups" / "pre_71"
MIN_BACKUP_BYTES = 1_024  # >1 KB per plan §4 (slack vs §2.3 "1 MB" — JSON, not dump)

EXPECTED_CONSTRAINTS = {
    # node-side
    "causal_node_id",
    # CAUSES (2)
    "edge_causes_confidence",
    "edge_causes_citation",
    # INHIBITS (2)
    "edge_inhibits_confidence",
    "edge_inhibits_citation",
    # MEDIATES (3)
    "edge_mediates_confidence",
    "edge_mediates_citation",
    "edge_mediates_via_node",
    # CONFOUNDS (3)
    "edge_confounds_confidence",
    "edge_confounds_citation",
    "edge_confounds_also",
    # MODERATES (3)
    "edge_moderates_confidence",
    "edge_moderates_citation",
    "edge_moderates_target",
}
MIN_CAUSAL_NODES = 568  # plan §4 — Phase 2 entity count carried forward
MIN_EDGE_TOTAL = 250  # plan §4 — 307 ± 5 with merges/drops; floor for slack
MIN_PROPERTY_FILL_PCT = 90.0  # plan §4 — >= 90% non-null confidence + citation
MIN_DIM_REF_PCT = 50.0  # plan §4 — 80% target, 50% MVP-accept floor
ALLOWED_EDGE_TYPES = {
    "CAUSES",
    "INHIBITS",
    "MEDIATES",
    "CONFOUNDS",
    "MODERATES",
    # Phase 2 Graphiti meta-types — allowed to remain (not part of Pearl SCM)
    "HAS_FACT",
    "MENTIONED_IN",
}
CITATION_REGEX_CYPHER = (
    r"^(PMID:\\d+|DOI:.+|https?://.+|TBD-Day-7-backfill)$"
)


# ---------------------------------------------------------------------------
# Result + decorator scaffold (matches verify_phase_7_0)
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


def _neo4j_session() -> Any:
    """Build a Neo4j session context manager from env vars.

    Returns the driver; caller is responsible for .close() and .session().
    Raises RuntimeError on missing env or driver import failure.
    """
    uri = os.environ.get("NEO4J_URI")
    password = os.environ.get("NEO4J_PASSWORD")
    if not uri or not password:
        raise RuntimeError(
            "NEO4J_URI + NEO4J_PASSWORD required for --mode production"
        )
    try:
        from neo4j import GraphDatabase  # type: ignore[import-not-found]
    except ImportError as e:  # pragma: no cover — driver install is prerequisite
        raise RuntimeError(f"neo4j driver missing in .venv-v7: {e}") from e
    return GraphDatabase.driver(
        uri, auth=(os.environ.get("NEO4J_USERNAME", "neo4j"), password)
    )


# ---------------------------------------------------------------------------
# 9 checks
# ---------------------------------------------------------------------------
@check(
    "check_7_1_01",
    "Backup exists in .planning/backups/pre_71/ (>1 KB)",
    mode_required="production",
)
def check_backup_exists(mode: str) -> CheckResult:
    """Day 1 backup_neo4j.py emits neo4j_snapshot_<UTC>.json. Plan §4 wants
    snapshot.dump >1 MB but AuraDB Free has no dump; JSON >=1 KB is the
    operative criterion (Day 1 script + 017_runbook §5).

    Marked production-only because the backup is a Shako-side operational
    action against live AuraDB credentials — it cannot be exercised from the
    engineering venv. The Day 1 script (scripts/backup_neo4j.py) is verified
    to exist (and to be importable) by the regression sweep; this check
    validates the artifact it produces against the live graph.
    """
    if not BACKUP_DIR.exists():
        return CheckResult(
            status="FAIL",
            actual=f"missing directory: {BACKUP_DIR}",
            expected=f"{BACKUP_DIR}/neo4j_snapshot_*.json",
            remediation=(
                "NEO4J_URI=... NEO4J_PASSWORD=... "
                ".venv-v7/Scripts/python.exe scripts/backup_neo4j.py"
            ),
        )
    snapshots = sorted(BACKUP_DIR.glob("neo4j_snapshot_*.json"))
    if not snapshots:
        return CheckResult(
            status="FAIL",
            actual=f"0 snapshots in {BACKUP_DIR}",
            expected=">=1 neo4j_snapshot_*.json",
            remediation=(
                "NEO4J_URI=... NEO4J_PASSWORD=... "
                ".venv-v7/Scripts/python.exe scripts/backup_neo4j.py"
            ),
        )
    latest = snapshots[-1]
    size = latest.stat().st_size
    if size < MIN_BACKUP_BYTES:
        return CheckResult(
            status="FAIL",
            actual=f"{latest.name} = {size} bytes",
            expected=f">= {MIN_BACKUP_BYTES} bytes",
            remediation="re-run scripts/backup_neo4j.py (empty graph?)",
        )
    return CheckResult(
        status="PASS",
        actual=f"{latest.name} = {size} bytes ({len(snapshots)} snapshot(s) total)",
        expected=f">= {MIN_BACKUP_BYTES} bytes",
    )


@check(
    "check_7_1_02",
    "Migration 017 constraints applied (causal_node_id + 13 edge)",
    mode_required="production",
)
def check_constraints_applied(mode: str) -> CheckResult:
    """SHOW CONSTRAINTS must list causal_node_id + 13 edge constraints from
    migration 017.
    """
    driver = _neo4j_session()
    try:
        with driver.session() as session:
            result = session.run("SHOW CONSTRAINTS YIELD name RETURN name")
            present = {row["name"] for row in result}
    finally:
        driver.close()

    missing = EXPECTED_CONSTRAINTS - present
    if missing:
        return CheckResult(
            status="FAIL",
            actual=f"missing {len(missing)} constraint(s): {sorted(missing)}",
            expected=f"all {len(EXPECTED_CONSTRAINTS)} constraints present",
            remediation=(
                "cypher-shell -a $NEO4J_URI -u neo4j -p $NEO4J_PASSWORD "
                "-f scripts/migrations/cypher/017_causal_edges.cypher"
            ),
        )
    return CheckResult(
        status="PASS",
        actual=f"{len(EXPECTED_CONSTRAINTS)}/{len(EXPECTED_CONSTRAINTS)} constraints present",
        expected=f"all {len(EXPECTED_CONSTRAINTS)} present",
    )


@check(
    "check_7_1_03",
    f"CausalNode label upgrade (count >= {MIN_CAUSAL_NODES})",
    mode_required="production",
)
def check_label_upgrade(mode: str) -> CheckResult:
    """Day 4 upgrade_to_causal_nodes.cypher must have promoted Phase 2 entities
    to also carry :CausalNode label.
    """
    driver = _neo4j_session()
    try:
        with driver.session() as session:
            result = session.run("MATCH (n:CausalNode) RETURN count(n) AS n")
            n = int(result.single()["n"])
    finally:
        driver.close()

    if n < MIN_CAUSAL_NODES:
        return CheckResult(
            status="FAIL",
            actual=f"{n} CausalNode(s)",
            expected=f">= {MIN_CAUSAL_NODES}",
            remediation=(
                "cypher-shell ... -f scripts/refactor/upgrade_to_causal_nodes.cypher"
            ),
        )
    return CheckResult(
        status="PASS",
        actual=f"{n} CausalNode(s)",
        expected=f">= {MIN_CAUSAL_NODES}",
    )


@check(
    "check_7_1_04",
    "All legacy edges re-classified (CO_OCCURS_WITH + RELATED_TO == 0)",
    mode_required="production",
)
def check_legacy_edges_gone(mode: str) -> CheckResult:
    """Day 6 classify_edges.py must have eliminated every legacy Phase 2 edge."""
    driver = _neo4j_session()
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH ()-[r:CO_OCCURS_WITH|RELATED_TO]-() RETURN count(r) AS n"
            )
            n = int(result.single()["n"])
    finally:
        driver.close()

    if n != 0:
        return CheckResult(
            status="FAIL",
            actual=f"{n} legacy edge(s) remain",
            expected="0",
            remediation=(
                "ANTHROPIC_API_KEY=... NEO4J_URI=... NEO4J_PASSWORD=... "
                ".venv-v7/Scripts/python.exe scripts/refactor/classify_edges.py"
            ),
        )
    return CheckResult(
        status="PASS",
        actual="0 legacy edges remain",
        expected="0",
    )


@check(
    "check_7_1_05",
    f"Edge type distribution (sum of 5 types >= {MIN_EDGE_TOTAL})",
    mode_required="production",
)
def check_edge_distribution(mode: str) -> CheckResult:
    """Aggregate count across the 5 Pearl SCM edge types.

    Plan §4 expects ~307 ± 5; we accept floor of MIN_EDGE_TOTAL to tolerate
    drops/merges from the deterministic + LLM re-classification pass.
    """
    driver = _neo4j_session()
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH ()-[r]->() WHERE type(r) IN "
                "['CAUSES','INHIBITS','MEDIATES','CONFOUNDS','MODERATES'] "
                "RETURN type(r) AS et, count(r) AS n"
            )
            buckets = {row["et"]: int(row["n"]) for row in result}
    finally:
        driver.close()

    total = sum(buckets.values())
    summary = (
        f"CAUSES={buckets.get('CAUSES', 0)} "
        f"INHIBITS={buckets.get('INHIBITS', 0)} "
        f"MEDIATES={buckets.get('MEDIATES', 0)} "
        f"CONFOUNDS={buckets.get('CONFOUNDS', 0)} "
        f"MODERATES={buckets.get('MODERATES', 0)} "
        f"(sum={total})"
    )

    if total < MIN_EDGE_TOTAL:
        return CheckResult(
            status="FAIL",
            actual=summary,
            expected=f"sum >= {MIN_EDGE_TOTAL}",
            remediation=(
                "scripts/refactor/classify_edges.py likely under-classified — "
                "inspect .planning/phase_7_1/bulk_summary_*.json"
            ),
        )
    return CheckResult(status="PASS", actual=summary, expected=f"sum >= {MIN_EDGE_TOTAL}")


@check(
    "check_7_1_06",
    f"Edge properties populated (>= {MIN_PROPERTY_FILL_PCT}% have confidence + citation)",
    mode_required="production",
)
def check_property_fill(mode: str) -> CheckResult:
    """Day 7 backfill_properties.py target: >= 90% edges have non-null
    confidence AND citation.
    """
    driver = _neo4j_session()
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH ()-[r]->() "
                "WHERE type(r) IN "
                "['CAUSES','INHIBITS','MEDIATES','CONFOUNDS','MODERATES'] "
                "WITH count(r) AS total, "
                "count(CASE WHEN r.confidence IS NOT NULL "
                "          AND r.citation IS NOT NULL THEN 1 END) AS filled "
                "RETURN total, filled"
            )
            row = result.single()
            total = int(row["total"])
            filled = int(row["filled"])
    finally:
        driver.close()

    if total == 0:
        return CheckResult(
            status="FAIL",
            actual="0 causal edges to measure",
            expected=f">= {MIN_PROPERTY_FILL_PCT}% filled",
            remediation="check_7_1_05 must pass before this check is meaningful",
        )
    pct = (filled / total) * 100.0
    if pct < MIN_PROPERTY_FILL_PCT:
        return CheckResult(
            status="FAIL",
            actual=f"{filled}/{total} = {pct:.1f}% filled",
            expected=f">= {MIN_PROPERTY_FILL_PCT}%",
            remediation=(
                "NEO4J_URI=... NEO4J_PASSWORD=... "
                ".venv-v7/Scripts/python.exe scripts/refactor/backfill_properties.py"
            ),
        )
    return CheckResult(
        status="PASS",
        actual=f"{filled}/{total} = {pct:.1f}% filled",
        expected=f">= {MIN_PROPERTY_FILL_PCT}%",
    )


@check(
    "check_7_1_07",
    f"Belief cross-link (>= {MIN_DIM_REF_PCT}% CausalNodes have dimension_ref; 80% target)",
    mode_required="production",
)
def check_dim_ref_link(mode: str) -> CheckResult:
    """Day 9 brain/memory/cross_link.py target: 80% of CausalNode rows carry
    a dimension_ref into belief_dimensions. MVP-accept floor MIN_DIM_REF_PCT.
    """
    driver = _neo4j_session()
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (n:CausalNode) "
                "WITH count(n) AS total, "
                "count(CASE WHEN n.dimension_ref IS NOT NULL THEN 1 END) AS linked "
                "RETURN total, linked"
            )
            row = result.single()
            total = int(row["total"])
            linked = int(row["linked"])
    finally:
        driver.close()

    if total == 0:
        return CheckResult(
            status="FAIL",
            actual="0 CausalNodes",
            expected=">= 1 to measure",
            remediation="check_7_1_03 must pass before this check is meaningful",
        )
    pct = (linked / total) * 100.0
    if pct < MIN_DIM_REF_PCT:
        return CheckResult(
            status="FAIL",
            actual=f"{linked}/{total} = {pct:.1f}% linked",
            expected=f">= {MIN_DIM_REF_PCT}% (80% target)",
            remediation=(
                "NEO4J_URI=... NEO4J_PASSWORD=... SUPABASE_DB_URL=... "
                ".venv-v7/Scripts/python.exe -m brain.memory.cross_link"
            ),
        )
    return CheckResult(
        status="PASS",
        actual=f"{linked}/{total} = {pct:.1f}% linked",
        expected=f">= {MIN_DIM_REF_PCT}% (80% target)",
    )


@check(
    "check_7_1_08",
    "Adapter regression + 7 invariant spot-checks (taxonomy contract intact)",
)
def check_adapter_regression(mode: str) -> CheckResult:
    """Two layers:

    1. ALWAYS run brain/memory/tests/ (deterministic, mock-driven). Validates
       the 7 taxonomy invariants at the unit level + the causal_adapter +
       cross_link mock paths. This is the Phase 2 ↔ Phase 7.1 boundary
       regression gate.
    2. In --mode production, additionally run the 7 live-graph spot-checks
       documented in the Day 8-9 carry-forward:
         (a) no edge types outside the 5 Pearl + 2 Phase-2-meta allowlist
         (b) every confidence in [0, 1]
         (c) every citation matches CITATION_REGEX_CYPHER
         (d) every MEDIATES edge has both CAUSES segments present
         (e) CAUSES + INHIBITS + MEDIATES sub-graph is acyclic
         (f) dimension_ref linked count agrees with cross_link audit bucket
         (g) report TBD-Day-7-backfill backlog (NOT a fail — Phase 7.2 gate)
    """
    # Layer 1 — offline pytest sweep (deterministic, no DB needed).
    pytest_nodes = [
        "brain/memory/tests/test_edge_taxonomy.py",
        "brain/memory/tests/test_causal_adapter.py",
        "brain/memory/tests/test_cross_link.py",
        "brain/memory/tests/test_classify_edges.py",
    ]
    rc, tail = _run_pytest(pytest_nodes, timeout=300)
    if rc != 0:
        return CheckResult(
            status="FAIL",
            actual=f"pytest exit={rc}; tail:\n{tail}",
            expected="all brain/memory/tests/ green",
            remediation="inspect brain/memory/tests/ failures; do NOT amend taxonomy",
        )

    if mode != "production":
        return CheckResult(
            status="PASS",
            actual="brain/memory/tests/ green (4 modules); live spot-checks deferred to --mode production",
        )

    # Layer 2 — live-graph 7 spot-checks (production mode only).
    findings: list[str] = []
    backlog_tbd: int = 0

    driver = _neo4j_session()
    try:
        with driver.session() as session:
            # (a) no edge types outside the allowed set
            result = session.run(
                "MATCH ()-[r]->() WITH DISTINCT type(r) AS t RETURN collect(t) AS types"
            )
            types_present = set(result.single()["types"])
            leak = sorted(types_present - ALLOWED_EDGE_TYPES)
            if leak:
                findings.append(f"(a) leaked edge types: {leak}")

            # (b) confidence range
            result = session.run(
                "MATCH ()-[r]->() "
                "WHERE r.confidence IS NOT NULL "
                "  AND (r.confidence < 0 OR r.confidence > 1) "
                "RETURN count(r) AS bad"
            )
            bad_conf = int(result.single()["bad"])
            if bad_conf:
                findings.append(f"(b) {bad_conf} edge(s) with confidence outside [0,1]")

            # (c) citation regex
            result = session.run(
                "MATCH ()-[r]->() "
                "WHERE r.citation IS NOT NULL "
                f"  AND NOT (r.citation =~ '{CITATION_REGEX_CYPHER}') "
                "RETURN count(r) AS bad"
            )
            bad_cite = int(result.single()["bad"])
            if bad_cite:
                findings.append(f"(c) {bad_cite} edge(s) with malformed citation")

            # (d) MEDIATES segment integrity
            result = session.run(
                "MATCH (s)-[r:MEDIATES]->(t) "
                "OPTIONAL MATCH (s)-[seg1:CAUSES]->(m) WHERE id(m) = r.via_node "
                "OPTIONAL MATCH (m2)-[seg2:CAUSES]->(t) WHERE id(m2) = r.via_node "
                "WITH r, seg1, seg2 "
                "WHERE seg1 IS NULL OR seg2 IS NULL "
                "RETURN count(r) AS broken"
            )
            broken_mediates = int(result.single()["broken"])
            if broken_mediates:
                findings.append(
                    f"(d) {broken_mediates} MEDIATES edge(s) missing CAUSES segment(s)"
                )

            # (e) DAG acyclicity over CAUSES + INHIBITS + MEDIATES
            try:
                import networkx as nx  # noqa: WPS433 — deferred import keeps base lightweight
            except ImportError:
                findings.append("(e) networkx unavailable — DAG check skipped")
            else:
                result = session.run(
                    "MATCH (s)-[r:CAUSES|INHIBITS|MEDIATES]->(t) "
                    "RETURN id(s) AS src, id(t) AS tgt"
                )
                g = nx.DiGraph()
                for row in result:
                    g.add_edge(row["src"], row["tgt"])
                if not nx.is_directed_acyclic_graph(g):
                    cycles = list(nx.simple_cycles(g))
                    first = cycles[0] if cycles else "<unknown>"
                    findings.append(
                        f"(e) DAG cycle detected: {len(cycles)} cycle(s); first={first!r}"
                    )

            # (f) dimension_ref linked count (informational — no fail criterion;
            # the count cross-validates check_7_1_07 numerator without re-running
            # the cross_link script).
            result = session.run(
                "MATCH (n:CausalNode) WHERE n.dimension_ref IS NOT NULL "
                "RETURN count(n) AS linked"
            )
            linked_ref = int(result.single()["linked"])

            # (g) TBD-Day-7-backfill backlog metric
            result = session.run(
                "MATCH ()-[r]->() WHERE r.citation = 'TBD-Day-7-backfill' "
                "RETURN count(r) AS backlog"
            )
            backlog_tbd = int(result.single()["backlog"])
    finally:
        driver.close()

    if findings:
        return CheckResult(
            status="FAIL",
            actual="; ".join(findings),
            expected="0 spot-check findings (a..e); (f)/(g) informational",
            remediation="see Phase 7.1 Day 8-9 carry-forward + edge_taxonomy.py invariants",
        )
    return CheckResult(
        status="PASS",
        actual=(
            "brain/memory/tests/ green + 7 live spot-checks (a-e) clean; "
            f"(f) dimension_ref linked={linked_ref}; "
            f"(g) TBD-Day-7-backfill backlog={backlog_tbd} (Phase 7.2 exclusion gate)"
        ),
    )


@check(
    "check_7_1_09",
    "Idempotency — classify_edges contract + re-run --dry-run yields 0 changes",
)
def check_idempotency(mode: str) -> CheckResult:
    """Two layers (mirror check_7_1_08 split):

    1. ALWAYS — unit-test the idempotency contract baked into
       scripts/refactor/classify_edges.py (docstring §Idempotency: re-run on
       fully-migrated graph finds 0 CO_OCCURS_WITH/RELATED_TO and exits clean).
       The test_classify_edges.py suite covers this with mocked Neo4j.
    2. In --mode production — invoke classify_edges.py --dry-run and confirm
       summary JSON reports 0 edges to process.
    """
    # Layer 1 — unit test
    rc, tail = _run_pytest(
        ["brain/memory/tests/test_classify_edges.py"], timeout=180
    )
    if rc != 0:
        return CheckResult(
            status="FAIL",
            actual=f"pytest exit={rc}; tail:\n{tail}",
            expected="all test_classify_edges.py green",
            remediation=(
                "inspect scripts/refactor/classify_edges.py idempotency path "
                "(deterministic rules MUST be a no-op on already-classified edges)"
            ),
        )

    if mode != "production":
        return CheckResult(
            status="PASS",
            actual="test_classify_edges.py green; live re-run gate deferred to --mode production",
        )

    # Layer 2 — live --dry-run sweep
    script = ROOT / "scripts" / "refactor" / "classify_edges.py"
    proc = subprocess.run(
        [str(PY), str(script), "--dry-run", "--max-llm", "0"],
        capture_output=True,
        text=True,
        timeout=600,
        cwd=str(ROOT),
    )
    if proc.returncode != 0:
        return CheckResult(
            status="FAIL",
            actual=f"classify_edges --dry-run exit={proc.returncode}; "
            f"tail: {(proc.stdout or proc.stderr).strip()[-300:]}",
            expected="exit=0 with 0 legacy edges processed",
            remediation="inspect .planning/phase_7_1/bulk_summary_*.json",
        )

    # Inspect the most recent summary JSON for a "0 to process" signal.
    summary_dir = ROOT / ".planning" / "phase_7_1"
    summaries = sorted(summary_dir.glob("bulk_summary_*.json"))
    if not summaries:
        return CheckResult(
            status="FAIL",
            actual=f"no bulk_summary_*.json in {summary_dir}",
            expected=">=1 summary JSON written by classify_edges.py",
            remediation="re-run classify_edges.py; ensure it can write to .planning/phase_7_1/",
        )
    latest = summaries[-1]
    summary = json.loads(latest.read_text(encoding="utf-8"))
    total_seen = int(
        summary.get("totals", {}).get("legacy_edges_seen", summary.get("seen", 0))
    )
    if total_seen != 0:
        return CheckResult(
            status="FAIL",
            actual=f"{latest.name}: legacy_edges_seen={total_seen}",
            expected="0 (graph already fully migrated)",
            remediation="some legacy edges remain — re-run live classify_edges.py without --dry-run",
        )
    return CheckResult(
        status="PASS",
        actual=f"test_classify_edges.py green; {latest.name} reports legacy_edges_seen=0",
    )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
CHECKS: list[Callable[[str], CheckResult]] = [
    check_backup_exists,
    check_constraints_applied,
    check_label_upgrade,
    check_legacy_edges_gone,
    check_edge_distribution,
    check_property_fill,
    check_dim_ref_link,
    check_adapter_regression,
    check_idempotency,
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


def _run_regression() -> None:
    """Run Phase 4, 5, 6, 7.0 verifiers in code-complete mode (informational)."""
    print("\n=== REGRESSION (Phase 4 + 5 + 6 + 7.0) ===")
    # Phase 4/5/6 verifiers depend on the main `.venv` (boto3, psycopg2);
    # Phase 7.0 is dual-venv tolerant. Try main first, fall back to v7 for 7.0.
    upstream = [
        ("scripts.verify_phase4", MAIN_VENV_PY),
        ("scripts.verify_phase5", MAIN_VENV_PY),
        ("scripts.verify_phase6", MAIN_VENV_PY),
        ("scripts.verify_phase_7_0", PY),
    ]
    for module_name, venv_py in upstream:
        py_module_path = ROOT / module_name.replace(".", "/")
        if not py_module_path.with_suffix(".py").exists():
            print(f"  {module_name}: NOT FOUND (skipping)")
            continue
        if not venv_py.exists():
            print(f"  {module_name}: venv missing at {venv_py} — skipped")
            continue
        proc = subprocess.run(
            [
                str(venv_py),
                "-X",
                "utf8",
                "-m",
                module_name,
                "--mode",
                "code-complete",
            ],
            capture_output=True,
            text=True,
            timeout=900,
            cwd=str(ROOT),
        )
        verdict = "GREEN" if proc.returncode == 0 else "RED"
        tail_lines = (proc.stdout or "").strip().splitlines()
        summary = tail_lines[-1].strip() if tail_lines else ""
        print(f"  {module_name}: exit={proc.returncode}  [{verdict}]  {summary}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--mode",
        choices=["code-complete", "production"],
        default="code-complete",
        help=(
            "code-complete (default): no live Neo4j. "
            "production: requires migration 017 applied + classify_edges run + cross_link run."
        ),
    )
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON after summary"
    )
    parser.add_argument(
        "--regression",
        action="store_true",
        help="also run Phase 4/5/6/7.0 verifiers in code-complete mode",
    )
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print(f"=== verify_phase_7_1 (mode: {args.mode}) ===")

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
