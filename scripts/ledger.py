"""
ledger.py — Phase 1 shared provenance helper.

Single point of contact for the perception layer's two side-effect surfaces:

    1. Cloudflare R2  (raw_artifact_url)
    2. Supabase evidence_ledger table

Every fetch script (fetch_pubmed, fetch_ctgov, fetch_preprints,
gap_filler, fetch_negative) goes through this module so the five PRC-07
provenance fields are written atomically and consistently:

    source_id, retrieval_method, retrieval_timestamp,
    content_hash, raw_artifact_url

Functions
---------
- compute_hash(payload) -> str
- upload_artifact(source_type, source_id, payload, ext) -> str
- insert_ledger_row(...) -> bool
- is_known_source(source_id, source_type, mode='positive') -> bool

Usage
-----
    from scripts.ledger import (
        compute_hash, upload_artifact, insert_ledger_row, is_known_source,
    )

    if is_known_source(pmid, 'pubmed'):
        continue
    xml = entrez_fetch(pmid)
    h = compute_hash(xml)
    url = upload_artifact('pubmed', pmid, xml, 'xml')
    insert_ledger_row(
        source_id=pmid, source_type='pubmed',
        retrieval_method='eutils',
        content_hash=h, raw_artifact_url=url,
        query=query, payload_metadata={...},
    )
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from typing import Any

import boto3
import httpx
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parent.parent

# Module-level singletons (initialised lazily).
_r2_client = None
_env_loaded = False


# ---------------------------------------------------------------------------
# .env loader (same convention used by every Phase 0 script)
# ---------------------------------------------------------------------------
def load_env() -> None:
    """Load .env into os.environ (idempotent). Existing env vars win."""
    global _env_loaded
    if _env_loaded:
        return
    p = ROOT / ".env"
    if not p.exists():
        _env_loaded = True
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v
    _env_loaded = True


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------
def compute_hash(payload: bytes) -> str:
    """SHA256 hex digest of raw bytes."""
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# R2 client
# ---------------------------------------------------------------------------
def _get_r2_client():
    global _r2_client
    if _r2_client is not None:
        return _r2_client
    load_env()
    required = [
        "CLOUDFLARE_R2_ENDPOINT",
        "CLOUDFLARE_R2_ACCESS_KEY_ID",
        "CLOUDFLARE_R2_SECRET_ACCESS_KEY",
        "CLOUDFLARE_R2_BUCKET",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"R2 env vars missing: {missing}")
    _r2_client = boto3.client(
        "s3",
        endpoint_url=os.environ["CLOUDFLARE_R2_ENDPOINT"],
        aws_access_key_id=os.environ["CLOUDFLARE_R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["CLOUDFLARE_R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    return _r2_client


def _r2_bucket() -> str:
    load_env()
    return os.environ["CLOUDFLARE_R2_BUCKET"]


def _r2_key_exists(key: str) -> bool:
    client = _get_r2_client()
    try:
        client.head_object(Bucket=_r2_bucket(), Key=key)
        return True
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def upload_artifact(
    source_type: str,
    source_id: str,
    payload: bytes,
    ext: str,
    *,
    mode: str = "positive",
) -> str:
    """
    Idempotent upload to R2. Returns the s3:// URL.

    Key layout:
      positive: <source_type>/<source_id>.<ext>
      negative: negative/<source_type>/<source_id>.<ext>
      crawl4ai/firecrawl: <source_type>/<content_hash>.<ext>  (content-addressed)

    If a key already exists, the upload is skipped and the existing URL is
    returned — make sure the caller hashes the payload first if it cares
    about idempotency by content.
    """
    bucket = _r2_bucket()
    safe_id = source_id.replace("/", "_").replace(":", "_")
    if mode == "negative":
        key = f"negative/{source_type}/{safe_id}.{ext}"
    else:
        key = f"{source_type}/{safe_id}.{ext}"

    client = _get_r2_client()
    if not _r2_key_exists(key):
        client.put_object(Bucket=bucket, Key=key, Body=payload)
    return f"s3://{bucket}/{key}"


# ---------------------------------------------------------------------------
# Supabase ledger
# ---------------------------------------------------------------------------
def _supabase_creds() -> tuple[str, str]:
    load_env()
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing in .env")
    return url, key


def _supabase_headers(
    key: str, *, prefer: str = "return=representation"
) -> dict[str, str]:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def is_known_source(
    source_id: str,
    source_type: str,
    *,
    mode: str = "positive",
) -> bool:
    """
    Return True iff a row already exists for (source_id, source_type, mode).
    Used to short-circuit HTTP fetches before they happen.
    """
    url, key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/evidence_ledger",
        params={
            "source_id": f"eq.{source_id}",
            "source_type": f"eq.{source_type}",
            "mode": f"eq.{mode}",
            "select": "id",
            "limit": "1",
        },
        headers=_supabase_headers(key, prefer="count=none"),
        timeout=10,
    )
    if r.status_code != 200:
        raise RuntimeError(
            f"is_known_source query failed: HTTP {r.status_code}: {r.text[:200]}"
        )
    return len(r.json()) > 0


def known_sources(
    source_ids: list[str],
    source_type: str,
    *,
    mode: str = "positive",
    chunk: int = 80,
) -> set[str]:
    """Batch form of is_known_source: return the subset of `source_ids` already
    present in evidence_ledger for (source_type, mode).

    P-4. One ``source_id=in.(...)`` query per chunk instead of one GET per
    candidate. **Fail-open**: on ANY error (missing creds, non-200, network) this
    returns an EMPTY set — i.e. treats everything as unknown so the caller
    re-fetches rather than silently skipping a credible lead. That inverts
    is_known_source (which raises on non-200): a transient Supabase blip must
    never drop a lead. The cost of fail-open is a redundant fetch + a 409 on
    insert (deduped server-side), never a double row.
    """
    ids = sorted({s for s in source_ids if s})
    if not ids:
        return set()
    known: set[str] = set()
    try:
        url, key = _supabase_creds()
        for i in range(0, len(ids), chunk):
            batch = ids[i : i + chunk]
            quoted = ",".join('"' + s.replace('"', '""') + '"' for s in batch)
            r = httpx.get(
                f"{url}/rest/v1/evidence_ledger",
                params={
                    "source_id": f"in.({quoted})",
                    "source_type": f"eq.{source_type}",
                    "mode": f"eq.{mode}",
                    "select": "source_id",
                },
                headers=_supabase_headers(key, prefer="count=none"),
                timeout=15,
            )
            if r.status_code != 200:
                return set()  # fail-open
            for row in r.json():
                sid = row.get("source_id")
                if sid is not None:
                    known.add(str(sid))
    except Exception:
        return set()  # fail-open
    return known


def query_watermark_key(query: str, *, mode: str = "positive") -> str:
    """Stable kv_state key for a fetcher query's incremental date watermark (P-3).

    Folds in `mode` so the positive and negative branches of the same query text
    never collide on one watermark row.
    """
    return f"pubmed_watermark:{mode}:{compute_hash(query.encode('utf-8'))[:16]}"


def insert_ledger_row(
    *,
    source_id: str,
    source_type: str,
    retrieval_method: str,
    content_hash: str,
    raw_artifact_url: str,
    mode: str = "positive",
    query: str | None = None,
    payload_metadata: dict[str, Any] | None = None,
) -> bool:
    """
    INSERT one row into evidence_ledger via Supabase REST.

    Returns True on insert, False on unique-constraint conflict (already known).
    Raises on any other failure.
    """
    url, key = _supabase_creds()
    body = {
        "source_id": source_id,
        "source_type": source_type,
        "retrieval_method": retrieval_method,
        "content_hash": content_hash,
        "raw_artifact_url": raw_artifact_url,
        "mode": mode,
    }
    if query is not None:
        body["query"] = query
    if payload_metadata is not None:
        body["payload_metadata"] = payload_metadata

    r = httpx.post(
        f"{url}/rest/v1/evidence_ledger",
        json=body,
        headers=_supabase_headers(key),
        timeout=10,
    )
    if r.status_code in (200, 201):
        return True
    if r.status_code == 409:
        # unique violation on (source_id, source_type, mode) — already ingested
        return False
    raise RuntimeError(
        f"insert_ledger_row failed: HTTP {r.status_code}: {r.text[:300]}"
    )


# ---------------------------------------------------------------------------
# kv_state — cross-run perception state (Supabase-backed kv store)
# ---------------------------------------------------------------------------
def get_state(key: str) -> dict[str, Any] | None:
    """Fetch a JSON value from kv_state. None if key not present."""
    url, sb_key = _supabase_creds()
    r = httpx.get(
        f"{url}/rest/v1/kv_state",
        params={"key": f"eq.{key}", "select": "value", "limit": "1"},
        headers=_supabase_headers(sb_key, prefer="count=none"),
        timeout=10,
    )
    if r.status_code != 200:
        raise RuntimeError(f"get_state failed: HTTP {r.status_code}: {r.text[:200]}")
    rows = r.json()
    return rows[0]["value"] if rows else None


def set_state(key: str, value: dict[str, Any]) -> None:
    """Upsert a JSON value into kv_state."""
    url, sb_key = _supabase_creds()
    body = {"key": key, "value": value}
    r = httpx.post(
        f"{url}/rest/v1/kv_state",
        json=body,
        headers={
            **_supabase_headers(sb_key),
            "Prefer": "resolution=merge-duplicates,return=representation",
        },
        timeout=10,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"set_state failed: HTTP {r.status_code}: {r.text[:200]}")


# ---------------------------------------------------------------------------
# Smoke test (python -m scripts.ledger)
# ---------------------------------------------------------------------------
def _smoke() -> int:
    print("[ledger.py] smoke test")
    payload = b"phase-1 ledger smoke test payload"
    h = compute_hash(payload)
    print(f"  hash:     {h[:16]}...  ({len(payload)} bytes)")

    url = upload_artifact("pubmed", f"smoke_{h[:8]}", payload, "txt")
    print(f"  uploaded: {url}")

    inserted = insert_ledger_row(
        source_id=f"smoke_{h[:8]}",
        source_type="pubmed",
        retrieval_method="eutils",
        content_hash=h,
        raw_artifact_url=url,
        query="ledger smoke test",
        payload_metadata={"smoke": True, "size": len(payload)},
    )
    print(f"  ledger insert: {'ok' if inserted else 'duplicate (idempotent)'}")

    known = is_known_source(f"smoke_{h[:8]}", "pubmed")
    print(f"  is_known_source check: {known}")

    if not known:
        print("[FAIL] just-inserted row not found by is_known_source")
        return 1
    print("[OK] smoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(_smoke())
