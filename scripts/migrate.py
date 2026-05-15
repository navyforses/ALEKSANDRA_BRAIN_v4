"""
migrate.py — Python-based Supabase migration runner.

Equivalent to scripts/migrate.sh but uses psycopg2 instead of the psql
binary. Phase 0 — works on Windows out of the box without installing
PostgreSQL client tools.

Usage:
    python -m scripts.migrate                 # apply all migrations
    python -m scripts.migrate --dry-run       # list files only
    python -m scripts.migrate --only NNN_name # apply only one migration file

Reads SUPABASE_DB_URL from .env (utf-8). Loads:
    1. scripts/schema.sql                    (baseline 10 tables)
    2. scripts/migrations/*.sql              (applied in alphabetical order)

--only takes a filename stem (or full filename) and applies just that
single migration. Useful when schema.sql is already deployed and you
only need to add a new migration on top.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = ROOT / ".env"
    if not env_path.exists():
        print(f"ERROR: {env_path} not found. Copy .env.example to .env first.")
        sys.exit(1)
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        env[k.strip()] = v.strip()
    return env


def split_statements(sql: str) -> list[str]:
    """
    Split SQL into top-level statements respecting:
      - $$-quoted dollar bodies (used by plpgsql functions)
      - single-quoted string literals
      - line comments (--)
    Returns each statement WITHOUT the trailing semicolon.
    """
    out: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(sql)
    in_dollar: str | None = None  # the dollar tag string, e.g. "$$"
    in_single = False
    in_line_comment = False

    while i < n:
        c = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""

        if in_line_comment:
            buf.append(c)
            if c == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_dollar is not None:
            buf.append(c)
            if sql.startswith(in_dollar, i):
                buf.extend(in_dollar[1:])  # already added c
                i += len(in_dollar)
                in_dollar = None
                continue
            i += 1
            continue

        if in_single:
            buf.append(c)
            if c == "'" and nxt != "'":
                in_single = False
            elif c == "'" and nxt == "'":
                buf.append(nxt)
                i += 1
            i += 1
            continue

        # Detect openings
        if c == "-" and nxt == "-":
            buf.append(c)
            in_line_comment = True
            i += 1
            continue
        if c == "'":
            buf.append(c)
            in_single = True
            i += 1
            continue
        if c == "$":
            # dollar tag: $$ or $tag$
            j = i + 1
            while j < n and (sql[j].isalnum() or sql[j] == "_"):
                j += 1
            if j < n and sql[j] == "$":
                in_dollar = sql[i : j + 1]
                buf.append(in_dollar)
                i = j + 1
                continue
        if c == ";":
            stmt = "".join(buf).strip()
            if stmt:
                out.append(stmt)
            buf = []
            i += 1
            continue

        buf.append(c)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out


def apply_file(cur, path: Path, *, dry_run: bool) -> int:
    sql = path.read_text(encoding="utf-8")
    statements = split_statements(sql)
    if dry_run:
        print(
            f"  [dry-run] would execute {len(statements)} statements from {path.name}"
        )
        return len(statements)
    executed = 0
    for stmt in statements:
        # Skip pure comments
        cleaned = "\n".join(
            line
            for line in stmt.splitlines()
            if line.strip() and not line.strip().startswith("--")
        ).strip()
        if not cleaned:
            continue
        try:
            cur.execute(stmt + ";")
            executed += 1
        except psycopg2.Error as e:
            short = (stmt[:120] + "...") if len(stmt) > 120 else stmt
            print(f"  [FAIL] FAILED: {short.splitlines()[0][:100]}")
            print(f"    {type(e).__name__}: {e}")
            raise
    return executed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--only",
        type=str,
        default=None,
        help="Apply only one migration file (stem or full filename, no path).",
    )
    args = ap.parse_args()

    env = load_env()
    db_url = env.get("SUPABASE_DB_URL", "")
    if not db_url or "xxxx" in db_url or "[" in db_url:
        print("ERROR: SUPABASE_DB_URL not configured in .env")
        return 1

    if args.only:
        stem = args.only
        if not stem.endswith(".sql"):
            stem += ".sql"
        target = ROOT / "scripts" / "migrations" / stem
        if not target.exists():
            print(f"ERROR: migration not found: {target}")
            return 1
        files: list[Path] = [target]
    else:
        files = [ROOT / "scripts" / "schema.sql"]
        migrations = sorted((ROOT / "scripts" / "migrations").glob("*.sql"))
        files.extend(migrations)

    print(f"applying {len(files)} SQL file(s) to {db_url.split('@')[-1]}")
    for f in files:
        print(f"  - {f.relative_to(ROOT)}")

    if args.dry_run:
        for f in files:
            apply_file(None, f, dry_run=True)
        return 0

    conn = psycopg2.connect(db_url, sslmode="require")
    conn.autocommit = False
    cur = conn.cursor()
    try:
        for f in files:
            print(f"\napplying: {f.relative_to(ROOT)}")
            n = apply_file(cur, f, dry_run=False)
            print(f"  [OK] {n} statements")
        conn.commit()
        print("\n[OK] migrations applied successfully")
    except Exception:
        conn.rollback()
        print("\n[FAIL] migration failed — rolled back")
        return 1
    finally:
        cur.close()
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
