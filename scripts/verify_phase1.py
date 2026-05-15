"""
verify_phase1.py — Phase 1 exit-gate acceptance checks.

Runs the 10-criterion verification matrix from the Phase 1 plan against
the live Supabase + R2 state. Exits 0 iff every criterion passes.

Criteria:
  1. Ledger >= 20 rows
  2. >= 3 distinct source_types
  3. All 5 PRC-07 provenance fields NOT NULL on every row
  4. >= 1 mode='negative' row
  5. R2 artifact count >= ledger row count
  6. Random sample of 3 rows: content_hash matches re-downloaded payload
  7. NCBI compliance: NCBI_EMAIL set, NCBI_TOOL set (api_key optional but flagged)
  8. Firecrawl spend < cap (kv_state.firecrawl_spend:<YYYY-MM> < FIRECRAWL_MONTHLY_CAP_USD)
  9. n8n perception_6h workflow file present at workflows/perception_6h.json
 10. Phase 0 regression: scripts/check-no-remote-fetch.sh exits 0

Usage:
    .venv/Scripts/python.exe -m scripts.verify_phase1
"""

from __future__ import annotations

import os
import random
import sys
from pathlib import Path

import httpx

from scripts.ledger import (
    _get_r2_client,
    _r2_bucket,
    _supabase_creds,
    _supabase_headers,
    compute_hash,
    get_state,
    load_env,
)

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Result accumulator
# ---------------------------------------------------------------------------
class Verdict:
    def __init__(self) -> None:
        self.items: list[tuple[str, bool, str]] = []

    def add(self, label: str, passed: bool, detail: str = "") -> None:
        self.items.append((label, passed, detail))
        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] {label:<48} {detail}")

    def all_passed(self) -> bool:
        return all(p for _, p, _ in self.items)

    def summary(self) -> str:
        passed = sum(1 for _, p, _ in self.items if p)
        return f"{passed}/{len(self.items)} PASS"


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------
def _supabase_rest(query_path: str, params: dict[str, str]) -> list[dict]:
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/{query_path}",
        params=params,
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=15,
    )
    if r.status_code != 200:
        raise RuntimeError(f"REST {query_path} HTTP {r.status_code}: {r.text[:200]}")
    return r.json()


def check_min_rows(v: Verdict, *, threshold: int = 20) -> None:
    rows = _supabase_rest(
        "evidence_ledger",
        {"select": "id"},
    )
    n = len(rows)
    v.add(
        f"1. ledger rows >= {threshold}",
        n >= threshold,
        f"actual={n}",
    )


def check_source_diversity(v: Verdict, *, threshold: int = 3) -> None:
    rows = _supabase_rest(
        "evidence_ledger",
        {"select": "source_type"},
    )
    distinct = {row["source_type"] for row in rows}
    v.add(
        f"2. distinct source_types >= {threshold}",
        len(distinct) >= threshold,
        f"actual={len(distinct)} ({','.join(sorted(distinct))})",
    )


def check_provenance_complete(v: Verdict) -> None:
    """All 5 PRC-07 fields must be NOT NULL on every row."""
    nulls = _supabase_rest(
        "evidence_ledger",
        {
            "select": "id",
            "or": (
                "(source_id.is.null,retrieval_method.is.null,"
                "content_hash.is.null,raw_artifact_url.is.null,"
                "retrieval_timestamp.is.null)"
            ),
        },
    )
    v.add(
        "3. all 5 provenance fields non-null",
        len(nulls) == 0,
        f"null_rows={len(nulls)}",
    )


def check_negative_branch(v: Verdict) -> None:
    rows = _supabase_rest(
        "evidence_ledger",
        {"select": "id", "mode": "eq.negative"},
    )
    v.add(
        "4. >= 1 mode='negative' row",
        len(rows) >= 1,
        f"negative_rows={len(rows)}",
    )


def check_r2_artifact_count(v: Verdict) -> None:
    rows = _supabase_rest(
        "evidence_ledger",
        {"select": "raw_artifact_url"},
    )
    ledger_count = len(rows)

    client = _get_r2_client()
    bucket = _r2_bucket()
    total_objs = 0
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        total_objs += len(page.get("Contents", []))

    v.add(
        "5. R2 artifact count >= ledger rows",
        total_objs >= ledger_count,
        f"R2={total_objs}  ledger={ledger_count}",
    )


def check_hash_integrity(v: Verdict, sample_size: int = 3) -> None:
    rows = _supabase_rest(
        "evidence_ledger",
        {"select": "source_id,source_type,content_hash,raw_artifact_url"},
    )
    if not rows:
        v.add("6. content_hash integrity (sample)", False, "no rows to sample")
        return

    sample = random.sample(rows, min(sample_size, len(rows)))
    client = _get_r2_client()
    matches = 0
    detail_lines = []
    for row in sample:
        url = row["raw_artifact_url"]
        if not url.startswith("s3://"):
            detail_lines.append(f"  bad URL: {url}")
            continue
        # s3://bucket/key...
        _, _, rest = url[len("s3://") :].partition("/")
        bucket, key = url[len("s3://") :].split("/", 1)
        try:
            obj = client.get_object(Bucket=bucket, Key=key)
            body = obj["Body"].read()
            h = compute_hash(body)
            if h == row["content_hash"]:
                matches += 1
                detail_lines.append(
                    f"  ok {row['source_type']}/{row['source_id'][:20]}"
                )
            else:
                detail_lines.append(
                    f"  MISMATCH {row['source_type']}/{row['source_id'][:16]} "
                    f"ledger={row['content_hash'][:8]} actual={h[:8]}"
                )
        except Exception as e:
            detail_lines.append(f"  fetch error: {type(e).__name__}: {e}")

    detail = f"{matches}/{len(sample)} match\n" + "\n".join(detail_lines)
    v.add(
        "6. content_hash integrity (sample 3)",
        matches == len(sample),
        detail,
    )


def check_ncbi_compliance(v: Verdict) -> None:
    load_env()
    email = os.environ.get("NCBI_EMAIL", "").strip()
    tool = os.environ.get("NCBI_TOOL", "").strip()
    api_key = os.environ.get("NCBI_API_KEY", "").strip()

    ok = bool(email) and "@example.com" not in email and bool(tool)
    detail = (
        f"email={'set' if email else 'MISSING'}  "
        f"tool={tool or 'MISSING'}  "
        f"api_key={'set' if api_key else 'unset (warning, allowed)'}"
    )
    v.add(
        "7. NCBI compliance (email+tool, key optional)",
        ok,
        detail,
    )


def check_firecrawl_cap(v: Verdict) -> None:
    load_env()
    from datetime import datetime as _dt
    from datetime import timezone as _tz

    month = _dt.now(_tz.utc).strftime("%Y-%m")
    state = get_state(f"firecrawl_spend:{month}") or {"usd": 0.0, "calls": 0}
    spend = float(state.get("usd", 0.0))
    cap = float(os.environ.get("FIRECRAWL_MONTHLY_CAP_USD", "10"))
    v.add(
        "8. firecrawl spend < cap",
        spend < cap,
        f"spend=${spend:.2f}  cap=${cap:.2f}  calls={state.get('calls', 0)}",
    )


def check_n8n_workflow_present(v: Verdict) -> None:
    path = ROOT / "workflows" / "perception_6h.json"
    v.add(
        "9. workflows/perception_6h.json present",
        path.is_file(),
        f"path={path.relative_to(ROOT)}",
    )


def check_phase0_regression(v: Verdict) -> None:
    """
    Phase 0 gate FND-02 still green: trust-boundary lint passes.

    Avoids bash subprocess on Windows (the project path contains Georgian
    characters and bash via Git-for-Windows refuses to chdir into them),
    and re-implements the same regex grep in Python directly. The bash
    version is still authoritative via pre-commit + GitHub Actions CI.
    """
    import re as _re

    viewer = ROOT / "viewer"
    if not viewer.is_dir():
        v.add(
            "10. Phase 0 fetch-lint regression",
            True,
            "viewer/ absent — nothing to check",
        )
        return

    ban = _re.compile(
        r"(fetch\(|axios\.(get|post|put|delete|patch|head)|axios\(|"
        r"new\s+XMLHttpRequest|navigator\.sendBeacon|EventSource\()"
    )
    allow = _re.compile(
        r"(['\"]/api/|['\"]/[a-zA-Z]|['\"]\.\./|localhost|"
        r"127\.0\.0\.1|blob:|data:|/\* allow-remote \*/)"
    )

    skip_dirs = {"node_modules", ".next", "dist"}
    extensions = {".ts", ".tsx", ".js", ".jsx"}
    violations: list[str] = []
    for path in viewer.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in extensions:
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        try:
            for i, line in enumerate(
                path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
            ):
                if ban.search(line) and not allow.search(line):
                    rel = path.relative_to(ROOT)
                    violations.append(f"{rel}:{i}: {line.strip()[:80]}")
        except Exception:
            continue

    v.add(
        "10. Phase 0 fetch-lint regression",
        len(violations) == 0,
        f"violations={len(violations)}"
        + (f" first={violations[0]}" if violations else ""),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> int:
    print("Phase 1 exit-gate verification")
    print("=" * 60)
    v = Verdict()
    check_min_rows(v)
    check_source_diversity(v)
    check_provenance_complete(v)
    check_negative_branch(v)
    check_r2_artifact_count(v)
    check_hash_integrity(v)
    check_ncbi_compliance(v)
    check_firecrawl_cap(v)
    check_n8n_workflow_present(v)
    check_phase0_regression(v)
    print("=" * 60)
    print(f"RESULT: {v.summary()}")
    return 0 if v.all_passed() else 1


if __name__ == "__main__":
    sys.exit(main())
