"""Phase 7.0 closure helper — UPSERT the 13 dimensions from dimensions.toml
into the live belief_dimensions table.

Run AFTER scripts/migrations/016_belief_tables.sql is applied to Supabase.

Usage:
  SUPABASE_DB_URL='postgres://service_role:...' \\
    .venv-v7/Scripts/python.exe -m brain.belief.bootstrap

Outputs:
  - per-dim status (INSERT new / UPDATE existing / UNCHANGED if name+params match)
  - final summary: 13/13 dimensions present in belief_dimensions

Exit code: 0 if all 13 land successfully, 1 on any failure.

Idempotent: re-running gives identical output (modulo timestamps). Service-role
connection required because writes go through RLS-enabled tables.

Design notes (carry-forward from .claude/agents/v7-bayes.md):
  - No PHI — operates on synthetic-prior catalog only.
  - Per-dim UPSERT (not single transaction) so a mid-batch failure leaves
    partial progress on disk; re-run picks up where it left off.
  - --dry-run is the explicit safe mode; default is live APPLY.
  - Citation enforcement is delegated to upsert_dimension (refuses empty).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from brain.belief.persistence import (
    BeliefDimension,
    list_dimensions,
    upsert_dimension,
)
from brain.belief.schema import (
    load_dimensions_from_toml,
    validate_dimension_catalog,
)


def _utf8_stdout() -> None:
    """Re-encode stdout as UTF-8 so Windows consoles don't choke on Mkhedruli."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _classify_change(
    existing: BeliefDimension | None,
    new: BeliefDimension,
) -> str:
    """Return 'INSERT' if no existing row, 'UPDATE' if differs, 'UNCHANGED' if identical."""
    if existing is None:
        return "INSERT"
    fields_to_compare = (
        "distribution",
        "prior_params",
        "units",
        "valid_min",
        "valid_max",
        "citation",
    )
    for field in fields_to_compare:
        if getattr(existing, field) != getattr(new, field):
            return "UPDATE"
    return "UNCHANGED"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap 13 belief dimensions into Supabase",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="parse TOML + classify changes but do NOT write to DB",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="machine-readable output appended after summary",
    )
    args = parser.parse_args()

    _utf8_stdout()
    print(f"=== brain.belief.bootstrap ({datetime.now(timezone.utc).isoformat()}) ===")
    print(f"Mode: {'dry-run' if args.dry_run else 'live UPSERT'}")

    # 1. Load + validate TOML
    try:
        dims = load_dimensions_from_toml()
    except Exception as e:
        print(f"[FAIL] could not load dimensions.toml: {e}")
        return 1

    report = validate_dimension_catalog(dims)
    print(
        f"[ok] dimensions.toml loaded: {report.total} total, {report.valid} valid, "
        f"{len(report.stubs_pending_citation)} stubs"
    )
    if report.stubs_pending_citation:
        print(
            f"[FAIL] {len(report.stubs_pending_citation)} stub citations remain: "
            f"{report.stubs_pending_citation}"
        )
        print("[fix] populate priors.toml via librarians (Days 7-9)")
        return 1
    if report.invalid:
        print(f"[FAIL] {len(report.invalid)} invalid rows: {report.invalid}")
        return 1
    if report.total != 13:
        print(f"[FAIL] expected 13 dimensions, found {report.total}")
        return 1

    if args.dry_run:
        # Don't touch DB — just preview classifications using empty existing-set
        print(
            "\n[dry-run] would UPSERT 13 dimensions; skipping classification (no DB read)"
        )
        for d in dims:
            cite_preview = (
                (d.citation[:50] + "...") if len(d.citation) > 50 else d.citation
            )
            print(
                f"  {d.name:30s} {d.distribution:12s} cite_len={len(d.citation)} preview={cite_preview!r}"
            )
        return 0

    # 2. Snapshot existing state (for change classification)
    try:
        existing_by_name = {d.name: d for d in list_dimensions()}
    except Exception as e:
        print(f"[FAIL] could not read belief_dimensions: {e}")
        print("[fix] is migration 016 applied? is SUPABASE_DB_URL set to service-role?")
        return 1

    # 3. UPSERT each dim + classify
    counts = {"INSERT": 0, "UPDATE": 0, "UNCHANGED": 0, "FAIL": 0}
    results: list[dict[str, object]] = []
    for d in dims:
        existing = existing_by_name.get(d.name)
        change = _classify_change(existing, d)
        try:
            dim_id = upsert_dimension(d)
            status = f"{change} (id={dim_id})"
            counts[change] += 1
        except Exception as e:
            status = f"FAIL: {e}"
            counts["FAIL"] += 1
            change = "FAIL"
        print(f"  {d.name:30s} {d.distribution:12s} {status}")
        results.append({"name": d.name, "change": change, "status": status})

    # 4. Final verification — re-read the table and confirm 13 named rows
    try:
        final = {d.name: d for d in list_dimensions()}
    except Exception as e:
        print(f"[FAIL] post-write verification read failed: {e}")
        return 1

    final_count = len(final)
    expected_names = {d.name for d in dims}
    missing = expected_names - set(final.keys())

    print("\n=== Summary ===")
    print(f"INSERT:    {counts['INSERT']}")
    print(f"UPDATE:    {counts['UPDATE']}")
    print(f"UNCHANGED: {counts['UNCHANGED']}")
    print(f"FAIL:      {counts['FAIL']}")
    print(f"belief_dimensions table: {final_count} rows")

    if args.json:
        print(
            json.dumps(
                {
                    "counts": counts,
                    "final_row_count": final_count,
                    "missing": sorted(missing),
                    "results": results,
                },
                indent=2,
            )
        )

    if missing:
        print(
            f"[FAIL] {len(missing)} dimensions missing from DB after UPSERT: {sorted(missing)}"
        )
        return 1
    if final_count != 13:
        print(f"[FAIL] expected 13 rows in belief_dimensions, found {final_count}")
        return 1
    if counts["FAIL"] > 0:
        return 1

    print(
        "\n=== 13/13 dimensions present in belief_dimensions — Phase 7.0 production-ready ==="
    )
    print(
        "Next: .venv-v7/Scripts/python.exe -m scripts.verify_phase_7_0 --mode production"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
