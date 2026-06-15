"""scripts/migrations/028_trials_bilingual_fulltext.py — Phase C wave 1 DDL.

Make clinical_trials store FULL ClinicalTrials.gov data, bilingual JSONB {en, ka}
for the family-facing fields — exactly like papers (migrations 017 / 026 / 027).

Two guarded steps, dry-run by default (pass --apply to write):

  1. backup — REST GET every clinical_trials row (all columns) to
              scripts/migrations/028_trials_backup.json. ALWAYS runs (even in dry
              run). clinical_trials is fully reconstructable from evidence_ledger +
              R2 by re-running the matcher, so this is a *belt-and-suspenders*
              snapshot taken BEFORE any DDL, not the only recovery path.
  2. ddl    — run 028_trials_bilingual_fulltext.sql via psycopg2 (SUPABASE_DB_URL).
              Idempotent-by-guard: the three ALTER COLUMN TYPE statements are
              skipped (the SQL is not executed) when title/brief_summary/
              eligibility_criteria are ALREADY jsonb. The two ADD COLUMN
              statements use IF NOT EXISTS, so they are always safe.

The ka *translation backfill* deliberately lives in the matcher
(scripts/trials/eligibility_matcher.py), not here — the matcher reads the FULL
study JSON from R2, extracts the rich fields, and wraps the family-facing ones
with build_bilingual() (budget-gated, self-healing). This orchestrator only
performs the schema change so the matcher has somewhere to write JSONB.

Usage
-----
    PYTHONUTF8=1 .venv/Scripts/python.exe \
        -m scripts.migrations.028_trials_bilingual_fulltext            # dry run
    PYTHONUTF8=1 .venv/Scripts/python.exe \
        -m scripts.migrations.028_trials_bilingual_fulltext --apply
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx

from scripts.ledger import ROOT, _supabase_creds, _supabase_headers, load_env

SQL_FILE = ROOT / "scripts" / "migrations" / "028_trials_bilingual_fulltext.sql"
BACKUP_FILE = ROOT / "scripts" / "migrations" / "028_trials_backup.json"

# The three TEXT columns this migration converts to jsonb. The two ADD COLUMN
# columns (detailed_description, conditions) are handled idempotently by the SQL
# itself (IF NOT EXISTS), so they are not part of the skip guard.
CONVERT_COLUMNS = ("title", "brief_summary", "eligibility_criteria")
ADD_COLUMNS = ("detailed_description", "conditions")
ALL_TRACKED = CONVERT_COLUMNS + ADD_COLUMNS


# --------------------------------------------------------------------------- #
# 1. backup
# --------------------------------------------------------------------------- #
def _fetch_all_trials() -> list[dict]:
    """Paginated GET of every clinical_trials row so we are never silently
    truncated by the PostgREST row cap."""
    url, key = _supabase_creds()
    out: list[dict] = []
    page = 0
    while True:
        r = httpx.get(
            f"{url}/rest/v1/clinical_trials",
            params={
                "select": "*",
                "order": "nct_id.asc",
                "limit": "1000",
                "offset": str(page * 1000),
            },
            headers=_supabase_headers(key, prefer="count=none"),
            timeout=60,
        )
        r.raise_for_status()
        rows = r.json()
        out.extend(rows)
        if len(rows) < 1000:
            break
        page += 1
    return out


def backup() -> Path:
    rows = _fetch_all_trials()
    BACKUP_FILE.write_text(json.dumps(rows, ensure_ascii=False, indent=2), "utf-8")
    by_status: dict[str, int] = {}
    for r in rows:
        st = r.get("aleksandra_status") or "?"
        by_status[st] = by_status.get(st, 0) + 1
    print(f"[028] backup: {len(rows)} trials {by_status} -> {BACKUP_FILE}")
    return BACKUP_FILE


# --------------------------------------------------------------------------- #
# 2. ddl
# --------------------------------------------------------------------------- #
def _column_types() -> dict[str, str]:
    import psycopg2

    dsn = os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        raise RuntimeError("SUPABASE_DB_URL missing — cannot run/verify DDL")
    conn = psycopg2.connect(dsn, connect_timeout=20)
    try:
        cur = conn.cursor()
        cur.execute(
            "select column_name, data_type from information_schema.columns "
            "where table_name='clinical_trials' and column_name = any(%s)",
            (list(ALL_TRACKED),),
        )
        return {name: dtype for name, dtype in cur.fetchall()}
    finally:
        conn.close()


def ddl(apply_changes: bool) -> None:
    types = _column_types()
    print(f"[028] current column types: {types}")

    convert_done = all(types.get(c) == "jsonb" for c in CONVERT_COLUMNS)
    add_done = all(types.get(c) == "jsonb" for c in ADD_COLUMNS)
    if convert_done and add_done:
        print("[028] ddl: all columns already jsonb — skip (idempotent)")
        return
    if not apply_changes:
        print("[028] ddl: WOULD run 028_trials_bilingual_fulltext.sql (dry run)")
        return

    import psycopg2

    sql = SQL_FILE.read_text(encoding="utf-8")
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], connect_timeout=20)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        print("[028] ddl: applied")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print(f"[028] ddl: verified types -> {_column_types()}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--apply", action="store_true", help="Write changes (default: dry run)."
    )
    ap.add_argument(
        "--skip-ddl", action="store_true", help="Backup only; do not run the DDL."
    )
    args = ap.parse_args()

    load_env()

    print("[028] types BEFORE:", _column_types())
    backup()

    if not args.skip_ddl:
        ddl(args.apply)

    print(
        "\n[028] done." + ("" if args.apply else "  (DRY RUN — pass --apply to write)")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
