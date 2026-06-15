"""scripts/migrations/029_trials_registry_columns.py — Phase E wave 1 DDL.

Make clinical_trials registry-aware so EU CTIS + UK ISRCTN trials (no NCT id) can
live alongside ClinicalTrials.gov rows — see the research doc
(docs/CLINICAL_TRIALS_SOURCES_RESEARCH.md, "Schema change → Option A").

Two guarded steps, dry-run by default (pass --apply to write), mirroring
028_trials_bilingual_fulltext.py exactly:

  1. backup — REST GET every clinical_trials row (all columns) to
              scripts/migrations/029_trials_backup.json. ALWAYS runs (even in dry
              run). clinical_trials is fully reconstructable from evidence_ledger +
              R2 by re-running the matcher, so this is a *belt-and-suspenders*
              snapshot taken BEFORE any DDL, not the only recovery path.
  2. ddl    — run 029_trials_registry_columns.sql via psycopg2 (SUPABASE_DB_URL).
              Idempotent-by-guard: every statement is IF NOT EXISTS (the three
              ADD COLUMN + the partial UNIQUE INDEX) and the backfill UPDATE is
              naturally idempotent (WHERE registry IS NULL). The orchestrator
              SKIPS the SQL only when ALL three columns already exist AND the
              ux_trials_registry index is present (fully migrated), and otherwise
              runs the SQL (which is itself safe to re-run).

This migration is ADDITIVE — no column is dropped or retyped — so RLS policies
survive untouched (same reasoning as 012 / 017 / 028).

Usage
-----
    PYTHONUTF8=1 .venv/Scripts/python.exe \
        -m scripts.migrations.029_trials_registry_columns            # dry run
    PYTHONUTF8=1 .venv/Scripts/python.exe \
        -m scripts.migrations.029_trials_registry_columns --apply
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx

from scripts.ledger import ROOT, _supabase_creds, _supabase_headers, load_env

SQL_FILE = ROOT / "scripts" / "migrations" / "029_trials_registry_columns.sql"
BACKUP_FILE = ROOT / "scripts" / "migrations" / "029_trials_backup.json"

# The three columns this migration adds. All ADDITIVE (ADD COLUMN IF NOT EXISTS).
NEW_COLUMNS = ("registry", "registry_id", "secondary_ids")
REGISTRY_INDEX = "ux_trials_registry"


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
    print(f"[029] backup: {len(rows)} trials {by_status} -> {BACKUP_FILE}")
    return BACKUP_FILE


# --------------------------------------------------------------------------- #
# 2. ddl
# --------------------------------------------------------------------------- #
def _existing_columns() -> set[str]:
    import psycopg2

    dsn = os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        raise RuntimeError("SUPABASE_DB_URL missing — cannot run/verify DDL")
    conn = psycopg2.connect(dsn, connect_timeout=20)
    try:
        cur = conn.cursor()
        cur.execute(
            "select column_name from information_schema.columns "
            "where table_name='clinical_trials' and column_name = any(%s)",
            (list(NEW_COLUMNS),),
        )
        return {name for (name,) in cur.fetchall()}
    finally:
        conn.close()


def _index_exists() -> bool:
    import psycopg2

    dsn = os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        raise RuntimeError("SUPABASE_DB_URL missing — cannot run/verify DDL")
    conn = psycopg2.connect(dsn, connect_timeout=20)
    try:
        cur = conn.cursor()
        cur.execute(
            "select 1 from pg_indexes "
            "where tablename='clinical_trials' and indexname=%s",
            (REGISTRY_INDEX,),
        )
        return cur.fetchone() is not None
    finally:
        conn.close()


def _ledger_constraints_widened() -> bool:
    """True iff evidence_ledger's source_type + retrieval_method CHECK constraints
    already allow the new registry values ('ctis'/'isrctn', 'ctis_public_api'/
    'isrctn_query_api'). Lets the orchestrator detect a partially-applied state
    (columns added on a prior run but constraints not yet widened) and re-run."""
    import psycopg2

    dsn = os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        raise RuntimeError("SUPABASE_DB_URL missing — cannot run/verify DDL")
    conn = psycopg2.connect(dsn, connect_timeout=20)
    try:
        cur = conn.cursor()
        cur.execute(
            "select con.conname, pg_get_constraintdef(con.oid) "
            "from pg_constraint con join pg_class rel on rel.oid = con.conrelid "
            "where rel.relname='evidence_ledger' and con.contype='c'"
        )
        defs = {name: defn for name, defn in cur.fetchall()}
        src = defs.get("evidence_ledger_source_type_chk", "")
        meth = defs.get("evidence_ledger_retrieval_method_chk", "")
        return (
            "ctis" in src
            and "isrctn" in src
            and "ctis_public_api" in meth
            and "isrctn_query_api" in meth
        )
    finally:
        conn.close()


def _registry_breakdown() -> dict[str, int]:
    """Live registry counts (before/after backfill) straight from the DB."""
    import psycopg2

    dsn = os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        return {}
    conn = psycopg2.connect(dsn, connect_timeout=20)
    try:
        cur = conn.cursor()
        cur.execute(
            "select coalesce(registry, '(null)'), count(*) "
            "from clinical_trials group by registry order by 1"
        )
        return {name: int(n) for name, n in cur.fetchall()}
    except Exception:
        # registry column may not exist yet (pre-migration) — that's expected.
        conn.rollback()
        return {}
    finally:
        conn.close()


def ddl(apply_changes: bool) -> None:
    cols = _existing_columns()
    idx = _index_exists()
    chk = _ledger_constraints_widened()
    print(
        f"[029] existing registry columns: {sorted(cols)}  index={idx}  "
        f"ledger_constraints_widened={chk}"
    )

    fully_migrated = set(NEW_COLUMNS).issubset(cols) and idx and chk
    if fully_migrated:
        print(
            "[029] ddl: columns + ux_trials_registry + widened ledger constraints "
            "already present — skip (idempotent)"
        )
        return
    if not apply_changes:
        print("[029] ddl: WOULD run 029_trials_registry_columns.sql (dry run)")
        return

    import psycopg2

    sql = SQL_FILE.read_text(encoding="utf-8")
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], connect_timeout=20)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        print("[029] ddl: applied")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print(
        f"[029] ddl: verified columns -> {sorted(_existing_columns())}  "
        f"index={_index_exists()}  "
        f"ledger_constraints_widened={_ledger_constraints_widened()}"
    )


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

    print("[029] registry breakdown BEFORE:", _registry_breakdown())
    backup()

    if not args.skip_ddl:
        ddl(args.apply)

    print("[029] registry breakdown AFTER:", _registry_breakdown())
    print(
        "\n[029] done." + ("" if args.apply else "  (DRY RUN — pass --apply to write)")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
