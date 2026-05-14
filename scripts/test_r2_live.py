"""
test_r2_live — upload + read round-trip against Cloudflare R2.

Verifies the four CLOUDFLARE_* env vars work end-to-end:
  1. boto3 S3 client points at the R2 endpoint
  2. put_object writes a small payload
  3. list_objects_v2 sees the key
  4. get_object reads the payload back byte-for-byte

This is the Phase 0+ companion to scripts/setup_qdrant.py — it proves the
raw-artifact store is reachable BEFORE Phase 1's Crawl4AI starts dumping
HTML/PDF blobs into it.

Usage:
    .venv/Scripts/python.exe -m scripts.test_r2_live
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import boto3

ROOT = Path(__file__).resolve().parent.parent


def load_env() -> None:
    p = ROOT / ".env"
    if not p.exists():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> int:
    load_env()

    required = [
        "CLOUDFLARE_R2_ENDPOINT",
        "CLOUDFLARE_R2_ACCESS_KEY_ID",
        "CLOUDFLARE_R2_SECRET_ACCESS_KEY",
        "CLOUDFLARE_R2_BUCKET",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"[FAIL] missing env vars: {missing}")
        return 1

    client = boto3.client(
        "s3",
        endpoint_url=os.environ["CLOUDFLARE_R2_ENDPOINT"],
        aws_access_key_id=os.environ["CLOUDFLARE_R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["CLOUDFLARE_R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    bucket = os.environ["CLOUDFLARE_R2_BUCKET"]
    key = "phase-0-test/hello.txt"
    body = b"Phase 0+ verification - R2 round-trip OK"

    client.put_object(Bucket=bucket, Key=key, Body=body)
    print(f"[OK] uploaded s3://{bucket}/{key} ({len(body)}B)")

    resp = client.list_objects_v2(Bucket=bucket, Prefix="phase-0-test/")
    for obj in resp.get("Contents", []):
        print(f"     listed: {obj['Key']:30} size={obj['Size']}B")

    got = client.get_object(Bucket=bucket, Key=key)["Body"].read()
    ok = got == body
    print(f"[{'OK' if ok else 'FAIL'}] read-back matches: {got!r}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
