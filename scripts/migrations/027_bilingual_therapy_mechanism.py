"""scripts/migrations/027_bilingual_therapy_mechanism.py

Make therapies.mechanism_of_action bilingual JSONB {en, ka} so /ka shows the
mechanism in Georgian (it showed English — the column was TEXT). Mirrors the
Phase B / migration 026 pattern, scoped to one therapies column.

Three guarded steps, dry-run by default (pass --apply to write):

  1. backup   — REST GET every therapy's id + mechanism_of_action to OS temp.
  2. ddl      — run 027_bilingual_therapy_mechanism.sql via psycopg2
                (SUPABASE_DB_URL). Idempotent-by-guard: skipped when jsonb.
  3. backfill — translate the ka slot from en via the Gemini translator
                (budget-guarded, refusal-safe). en stays authoritative; ka is
                never written when en is empty; a good existing ka is left
                untouched; a messy/Cyrillic translation is refused (en fallback).

There are ~16 therapies, so the translation cost is a few cents at most.

Usage
-----
    python -m scripts.migrations.027_bilingual_therapy_mechanism            # dry run
    python -m scripts.migrations.027_bilingual_therapy_mechanism --apply
    python -m scripts.migrations.027_bilingual_therapy_mechanism --apply --skip-ddl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

from scripts.extraction.gemini_translator import (
    TranslationFailed,
    has_georgian,
    is_messy,
    translate_prose,
)
from scripts.ledger import ROOT, _supabase_creds, _supabase_headers, load_env

COLUMN = "mechanism_of_action"
SQL_FILE = ROOT / "scripts" / "migrations" / "027_bilingual_therapy_mechanism.sql"


def _en_ka(value: Any) -> tuple[str, str | None]:
    """(en, ka) from a JSONB dict / JSON-text string / plain text scalar."""
    if value is None:
        return "", None
    if isinstance(value, dict):
        en = value.get("en")
        ka = value.get("ka")
        return (str(en).strip() if en else ""), (str(ka) if ka else None)
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                d = json.loads(s)
                if isinstance(d, dict):
                    return _en_ka(d)
            except json.JSONDecodeError:
                pass
        return s, None
    return str(value).strip(), None


def _good_ka(ka: str | None) -> bool:
    return bool(ka and has_georgian(ka) and not is_messy(ka))


def _rest_get(params: dict) -> list[dict]:
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/therapies",
        params=params,
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def _rest_patch(tid: str, body: dict) -> bool:
    url, key = _supabase_creds()
    r = httpx.patch(
        f"{url}/rest/v1/therapies",
        params={"id": f"eq.{tid}"},
        json=body,
        headers={**_supabase_headers(key), "Prefer": "return=minimal"},
        timeout=30,
    )
    return 200 <= r.status_code < 300


def backup() -> Path:
    rows = _rest_get({"select": f"id,{COLUMN}", "limit": "1000"})
    dest = Path(os.environ.get("TEMP", "/tmp")) / "aleksandra_027_backup.json"
    dest.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    print(f"[027] backup: {len(rows)} therapies -> {dest}")
    return dest


def _column_type() -> str | None:
    import psycopg2

    dsn = os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        raise RuntimeError("SUPABASE_DB_URL missing — cannot run/verify DDL")
    conn = psycopg2.connect(dsn, connect_timeout=20)
    try:
        cur = conn.cursor()
        cur.execute(
            "select data_type from information_schema.columns "
            "where table_name='therapies' and column_name=%s",
            (COLUMN,),
        )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def ddl(apply_changes: bool) -> None:
    dtype = _column_type()
    print(f"[027] current {COLUMN} type: {dtype}")
    if dtype == "jsonb":
        print("[027] ddl: column already jsonb — skip (idempotent)")
        return
    if not apply_changes:
        print("[027] ddl: WOULD run 027_bilingual_therapy_mechanism.sql (dry run)")
        return

    import psycopg2

    sql = SQL_FILE.read_text(encoding="utf-8")
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], connect_timeout=20)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        print("[027] ddl: applied")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print(f"[027] ddl: verified type -> {_column_type()}")


def backfill(apply_changes: bool) -> dict[str, int]:
    rows = _rest_get({"select": f"id,{COLUMN}", "limit": "1000"})
    stats = {
        "therapies": len(rows),
        "translated": 0,
        "skipped_have_ka": 0,
        "skipped_no_en": 0,
        "failed": 0,
        "patched": 0,
    }
    from scripts.cognition.budget import BudgetExceeded

    for row in rows:
        tid = str(row["id"])
        en, ka_now = _en_ka(row.get(COLUMN))
        if not en:
            stats["skipped_no_en"] += 1
            continue
        if _good_ka(ka_now):
            stats["skipped_have_ka"] += 1
            continue
        try:
            ka_new = translate_prose(en)
        except BudgetExceeded:
            sys.stderr.write(
                f"[027] BUDGET EXCEEDED at {tid[:8]} — stop (resume-safe)\n"
            )
            break
        except TranslationFailed as e:
            stats["failed"] += 1
            sys.stderr.write(f"  [{tid[:8]}] {e}\n")
            continue
        if not _good_ka(ka_new):
            stats["failed"] += 1
            continue
        stats["translated"] += 1
        if not apply_changes:
            print(f"  DRY {tid[:8]}  -> {ka_new[:60]!r}")
            continue
        if _rest_patch(tid, {COLUMN: {"en": en, "ka": ka_new}}):
            stats["patched"] += 1
            print(f"  WROTE {tid[:8]}", flush=True)
    return stats


def verify() -> None:
    rows = _rest_get({"select": f"id,{COLUMN}", "limit": "1000"})
    en_n = sum(1 for r in rows if _en_ka(r.get(COLUMN))[0])
    ka_n = sum(1 for r in rows if _en_ka(r.get(COLUMN))[1])
    print(f"\n[027] verify (live): {COLUMN} en={en_n}  ka={ka_n}/{en_n}")
    sample = next((r for r in rows if _en_ka(r.get(COLUMN))[1]), None)
    if sample:
        en, ka = _en_ka(sample[COLUMN])
        print(f"  sample {str(sample['id'])[:8]}:")
        print(f"    en: {en[:80]!r}")
        print(f"    ka: {ka[:80]!r}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--apply", action="store_true", help="Write changes (default: dry run)."
    )
    ap.add_argument(
        "--skip-ddl", action="store_true", help="Do not run the TYPE migration."
    )
    ap.add_argument("--skip-backfill", action="store_true", help="Do not translate ka.")
    args = ap.parse_args()

    load_env()
    backup()
    if not args.skip_ddl:
        ddl(args.apply)
    if not args.skip_backfill:
        stats = backfill(args.apply)
        print("\n[027] backfill stats:")
        for k, v in stats.items():
            print(f"  {k:18} {v}")
    if args.apply:
        verify()
    print("\n[027] done." + ("" if args.apply else "  (DRY RUN — pass --apply)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
