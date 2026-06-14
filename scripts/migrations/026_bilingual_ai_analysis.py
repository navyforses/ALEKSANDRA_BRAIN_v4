"""scripts/migrations/026_bilingual_ai_analysis.py — Phase B orchestrator.

Make papers.ai_summary + papers.ai_aleksandra_implications bilingual JSONB
{en, ka} so the /ka/research surface shows the per-paper analysis in Georgian
(it shows English today). Mirrors the JSONB shape title/abstract already use.

Three guarded steps, dry-run by default (pass --apply to write):

  1. backup   — REST GET every paper's id + ai_summary + ai_aleksandra_implications
                + ai_key_findings to OS temp. ALWAYS runs (even dry-run); the DB
                is the source of truth but this is a cheap safety net before DDL.
  2. ddl      — run 026_bilingual_ai_analysis.sql via psycopg2 (SUPABASE_DB_URL).
                Idempotent-by-guard: skipped when the columns are already jsonb.
  3. backfill — fill the ka slot for the relevant, analysed papers. FREE for the
                158 already in the KA digest cache (reuse, no API). Any paper not
                in the cache with non-empty en is translated via the Gemini
                translator (budget-guarded, refusal-safe). en stays authoritative;
                ka is never written when en is empty, and an existing good ka is
                left untouched (idempotent).

Cache: C:/Users/.../Temp/aleksandra_ka_digest_cache.json — built by the family
digest generator, keyed by paper id, each value {title, summary, implications}
in Georgian, where `summary` is the translation of ai_summary and `implications`
of ai_aleksandra_implications (verified against the generator).

Usage
-----
    python -m scripts.migrations.026_bilingual_ai_analysis                 # dry run
    python -m scripts.migrations.026_bilingual_ai_analysis --apply
    python -m scripts.migrations.026_bilingual_ai_analysis --apply --skip-ddl
    python -m scripts.migrations.026_bilingual_ai_analysis --apply --limit 5
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

MIN_RELEVANCE = 0.5
SQL_FILE = ROOT / "scripts" / "migrations" / "026_bilingual_ai_analysis.sql"
COLUMNS = ("ai_summary", "ai_aleksandra_implications")
# cache field name -> target column
CACHE_FIELD = {"ai_summary": "summary", "ai_aleksandra_implications": "implications"}


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _cache_path() -> Path:
    for p in (
        Path(os.environ.get("TEMP", "")) / "aleksandra_ka_digest_cache.json",
        Path("C:/Users/jinch/AppData/Local/Temp/aleksandra_ka_digest_cache.json"),
    ):
        if p.exists():
            return p
    return Path(os.environ.get("TEMP", "/tmp")) / "aleksandra_ka_digest_cache.json"


def _load_cache() -> dict[str, dict]:
    p = _cache_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


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


def _rest_get(path: str, params: dict) -> list[dict]:
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/{path}",
        params=params,
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def _rest_patch(path: str, params: dict, body: dict) -> bool:
    url, key = _supabase_creds()
    r = httpx.patch(
        f"{url}/rest/v1/{path}",
        params=params,
        json=body,
        headers={**_supabase_headers(key), "Prefer": "return=minimal"},
        timeout=30,
    )
    return 200 <= r.status_code < 300


def _fetch_all_papers(select: str) -> list[dict]:
    """Paginated GET so we are never silently truncated by the PostgREST cap."""
    out: list[dict] = []
    page = 0
    while True:
        rows = _rest_get(
            "papers",
            {
                "select": select,
                "order": "id.asc",
                "limit": "1000",
                "offset": str(page * 1000),
            },
        )
        out.extend(rows)
        if len(rows) < 1000:
            break
        page += 1
    return out


# --------------------------------------------------------------------------- #
# 1. backup
# --------------------------------------------------------------------------- #
def backup() -> Path:
    rows = _fetch_all_papers("id,ai_summary,ai_aleksandra_implications,ai_key_findings")
    dest = Path(os.environ.get("TEMP", "/tmp")) / "aleksandra_026_backup.json"
    dest.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    analysed = sum(1 for r in rows if r.get("ai_summary"))
    print(f"[026] backup: {len(rows)} papers ({analysed} analysed) -> {dest}")
    return dest


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
            "where table_name='papers' and column_name = any(%s)",
            (list(COLUMNS),),
        )
        return {name: dtype for name, dtype in cur.fetchall()}
    finally:
        conn.close()


def ddl(apply_changes: bool) -> None:
    types = _column_types()
    print(f"[026] current column types: {types}")
    if all(types.get(c) == "jsonb" for c in COLUMNS):
        print("[026] ddl: columns already jsonb — skip (idempotent)")
        return
    if not apply_changes:
        print("[026] ddl: WOULD run 026_bilingual_ai_analysis.sql (dry run)")
        return

    import psycopg2

    sql = SQL_FILE.read_text(encoding="utf-8")
    conn = psycopg2.connect(os.environ["SUPABASE_DB_URL"], connect_timeout=20)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        print("[026] ddl: applied")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print(f"[026] ddl: verified types -> {_column_types()}")


# --------------------------------------------------------------------------- #
# 3. backfill ka
# --------------------------------------------------------------------------- #
def _good_ka(ka: str | None) -> bool:
    return bool(ka and has_georgian(ka) and not is_messy(ka))


def backfill(apply_changes: bool, limit: int | None) -> dict[str, int]:
    cache = _load_cache()
    print(f"[026] cache entries: {len(cache)}")
    rows = _rest_get(
        "papers",
        {
            "select": "id,ai_summary,ai_aleksandra_implications",
            "relevance_score": f"gte.{MIN_RELEVANCE}",
            "ai_summary": "not.is.null",
            "order": "relevance_score.desc",
            "limit": "1000",
        },
    )
    stats = {
        "papers": len(rows),
        "from_cache": 0,
        "translated": 0,
        "skipped_have_ka": 0,
        "skipped_no_en": 0,
        "failed": 0,
        "patched": 0,
    }
    from scripts.cognition.budget import BudgetExceeded

    count = 0
    for row in rows:
        if limit and count >= limit:
            break
        pid = str(row["id"])
        cached = cache.get(pid, {})
        patch: dict[str, Any] = {}
        for col in COLUMNS:
            en, ka_now = _en_ka(row.get(col))
            if not en:
                stats["skipped_no_en"] += 1
                continue
            if _good_ka(ka_now):
                stats["skipped_have_ka"] += 1
                continue
            ka_cache = (cached.get(CACHE_FIELD[col]) or "").strip()
            if _good_ka(ka_cache):
                patch[col] = {"en": en, "ka": ka_cache}
                stats["from_cache"] += 1
                continue
            # not in cache (or cache ka unusable) -> translate, budget-guarded
            try:
                ka_new = translate_prose(en)
            except BudgetExceeded:
                sys.stderr.write(
                    f"[026] BUDGET EXCEEDED at {pid[:8]} — stop (resume-safe)\n"
                )
                break
            except TranslationFailed as e:
                stats["failed"] += 1
                sys.stderr.write(f"  [{pid[:8]}] {col}: {e}\n")
                continue
            if _good_ka(ka_new):
                patch[col] = {"en": en, "ka": ka_new}
                stats["translated"] += 1

        if not patch:
            continue
        count += 1
        if not apply_changes:
            tag = ",".join(
                f"{c}:{'cache' if patch[c]['ka']==(cache.get(pid,{}).get(CACHE_FIELD[c]) or '').strip() else 'xlate'}"
                for c in patch
            )
            print(f"  DRY {pid[:8]}  {tag}")
            continue
        if _rest_patch("papers", {"id": f"eq.{pid}"}, patch):
            stats["patched"] += 1
            print(f"  WROTE {pid[:8]}  fields={list(patch)}", flush=True)
    return stats


# --------------------------------------------------------------------------- #
# 4. verify
# --------------------------------------------------------------------------- #
def verify() -> None:
    rows = _rest_get(
        "papers",
        {
            "select": "id,ai_summary,ai_aleksandra_implications",
            "relevance_score": f"gte.{MIN_RELEVANCE}",
            "ai_summary": "not.is.null",
            "limit": "1000",
        },
    )
    with_ka = sum(1 for r in rows if _en_ka(r.get("ai_summary"))[1])
    impl_total = sum(1 for r in rows if _en_ka(r.get("ai_aleksandra_implications"))[0])
    impl_ka = sum(1 for r in rows if _en_ka(r.get("ai_aleksandra_implications"))[1])
    print("\n[026] verify (live):")
    print(f"  analysed papers:            {len(rows)}")
    print(f"  ai_summary with ka:         {with_ka}/{len(rows)}")
    print(f"  implications with en:       {impl_total}")
    print(f"  implications with ka:       {impl_ka}/{impl_total}")
    sample = next((r for r in rows if _en_ka(r.get("ai_summary"))[1]), None)
    if sample:
        en, ka = _en_ka(sample["ai_summary"])
        print(f"\n  sample {str(sample['id'])[:8]}:")
        print(f"    en: {en[:90]!r}")
        print(f"    ka: {ka[:90]!r}")


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
        "--skip-ddl", action="store_true", help="Do not run the TYPE migration."
    )
    ap.add_argument("--skip-backfill", action="store_true", help="Do not backfill ka.")
    ap.add_argument(
        "--limit", type=int, default=None, help="Backfill at most N papers."
    )
    args = ap.parse_args()

    load_env()
    backup()

    if not args.skip_ddl:
        ddl(args.apply)

    if not args.skip_backfill:
        # backfill needs the columns to be jsonb; in dry run before DDL the
        # columns may still be text — _en_ka handles both shapes, so dry run is safe.
        stats = backfill(args.apply, args.limit)
        print("\n[026] backfill stats:")
        for k, v in stats.items():
            print(f"  {k:20} {v}")

    if args.apply:
        verify()

    print("\n[026] done." + ("" if args.apply else "  (DRY RUN — pass --apply)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
