"""scripts/backup_to_r2.py — OPS-5 — scheduled offsite backup to Cloudflare R2.

Dumps the two stateful stores and pushes each to R2 under a TIMESTAMPED key:
  - Supabase Postgres  -> pg_dump (plain SQL)      -> backup/supabase_<ts>.sql
  - Neo4j AuraDB       -> backup_neo4j.export_graph -> backup/neo4j_<ts>.json

Why timestamped: `ledger.upload_artifact` is idempotent on the key, so a unique
per-run id means a failed or partial run can NEVER overwrite the last-good object.
An unreachable / unconfigured source is logged and skipped, not fatal — the other
source still backs up (resilience over completeness, per Core Value).

Exit code:
  0  at least one source uploaded
  2  nothing uploaded (no creds / both sources failed)

This module imports cleanly with NO neo4j import at load time (the driver is heavy
and `backup_neo4j` sys.exit(1)s if it is missing); `export_graph` is resolved lazily
and is patchable by tests.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit, urlunsplit

from scripts.ledger import load_env, upload_artifact

# Resolved lazily inside _dump_neo4j so importing this module never triggers the
# neo4j driver import. Tests patch this attribute directly.
export_graph = None

# R2 layout: backup/<source_id>.<ext>
_SOURCE_TYPE = "backup"


class _ConfigError(RuntimeError):
    """A source is not configured (missing creds) — skip it, don't crash the run."""


def _utf8() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")


# ---------------------------------------------------------------------------
# Source dumps — each raises _ConfigError if its creds are absent.
# ---------------------------------------------------------------------------
def _split_db_url(db_url: str) -> tuple[str, dict]:
    """Return (url-without-password, env-with-PGPASSWORD).

    Keeps the DB password OFF the pg_dump argv (where `ps`/`/proc` could observe it)
    by moving it to PGPASSWORD, while preserving every other connection param
    (user/host/port/dbname and query flags like sslmode) in the URL.
    """
    parts = urlsplit(db_url)
    env = os.environ.copy()
    if not parts.password:
        return db_url, env
    env["PGPASSWORD"] = unquote(parts.password)
    host = parts.hostname or ""
    netloc = parts.username or ""
    if host:
        netloc = f"{netloc}@{host}" if netloc else host
        if parts.port:
            netloc += f":{parts.port}"
    safe = urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    return safe, env


def _dump_supabase() -> bytes:
    """Plain-SQL pg_dump of the Supabase database. Raises _ConfigError if unset."""
    db_url = os.environ.get("SUPABASE_DB_URL", "").strip()
    if not db_url:
        raise _ConfigError("SUPABASE_DB_URL not set")
    safe_url, env = _split_db_url(db_url)
    proc = subprocess.run(
        ["pg_dump", "--no-owner", "--no-privileges", safe_url],
        capture_output=True,
        env=env,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or b"").decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"pg_dump exited {proc.returncode}: {stderr}")
    if not proc.stdout:
        raise RuntimeError("pg_dump produced no output")
    return proc.stdout


def _resolve_export_graph():
    """Lazy accessor: return the (possibly test-patched) export_graph callable."""
    global export_graph
    if export_graph is None:
        from scripts.backup_neo4j import export_graph as _eg

        export_graph = _eg
    return export_graph


def _dump_neo4j() -> bytes:
    """JSON snapshot of the whole Neo4j graph. Raises _ConfigError if unset."""
    uri = os.environ.get("NEO4J_URI", "").strip()
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "").strip()
    if not uri or not password:
        raise _ConfigError("NEO4J_URI / NEO4J_PASSWORD not set")

    eg = _resolve_export_graph()
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        graph = eg(driver)
    finally:
        driver.close()
    return json.dumps(graph, ensure_ascii=False, default=str).encode("utf-8")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
def _backup_one(label: str, ext: str, source_id: str, dump_fn, *, dry_run: bool):
    """Dump one source and upload it. Returns the R2 url on success, else None."""
    try:
        payload = dump_fn()
    except _ConfigError as e:
        print(f"[skip] {label}: {e} (last-good object preserved)")
        return None
    except Exception as e:
        print(
            f"[warn] {label} dump failed: {type(e).__name__}: {e} (last-good preserved)"
        )
        return None

    if dry_run:
        print(
            f"[dry-run] {label}: {len(payload)} bytes, would upload {source_id}.{ext}"
        )
        return f"(dry-run:{source_id}.{ext})"

    try:
        url = upload_artifact(_SOURCE_TYPE, source_id, payload, ext)
    except Exception as e:
        print(f"[warn] {label} upload failed: {type(e).__name__}: {e}")
        return None
    print(f"[ok] {label}: {len(payload)} bytes -> {url}")
    return url


def run(*, dry_run: bool = False) -> int:
    load_env()
    _utf8()
    ts = _timestamp()
    print(f"=== backup_to_r2 {ts} ({'dry-run' if dry_run else 'live'}) ===")

    uploads = []
    uploads.append(
        _backup_one(
            "supabase", "sql", f"supabase_{ts}", _dump_supabase, dry_run=dry_run
        )
    )
    uploads.append(
        _backup_one("neo4j", "json", f"neo4j_{ts}", _dump_neo4j, dry_run=dry_run)
    )

    ok = [u for u in uploads if u]
    if ok:
        print(f"[done] {len(ok)}/2 sources backed up")
        return 0
    print("[fail] no source backed up — check creds / connectivity", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Back up Supabase + Neo4j to Cloudflare R2."
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="dump + size only; no R2 upload",
    )
    args = ap.parse_args(argv)
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
