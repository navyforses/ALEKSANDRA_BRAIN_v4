"""
setup_qdrant — create the 3 baseline Qdrant collections + fastembed sanity test.

Collections:
  - papers       (research literature chunks)
  - therapies    (drug + intervention candidates)
  - hypotheses   (cross-disease patterns surfaced by the Hypothesis agent)

Embedding: BAAI/bge-small-en-v1.5 (384-dim, fastembed default; runs locally
without network calls, satisfies the no-API-cost-for-embeddings invariant).

Idempotent — re-running upserts collection config and skips test docs that
were already inserted (deduped by point ID).

Usage:
    .venv/Scripts/python.exe -m scripts.setup_qdrant
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

ROOT = Path(__file__).resolve().parent.parent


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = ROOT / ".env"
    if not env_path.exists():
        return env
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


COLLECTIONS = {
    "papers": "research literature chunks (PubMed, bioRxiv, medRxiv, ClinicalTrials)",
    "therapies": "drug + intervention candidates (HIE, neuroprotection, cross-disease)",
    "hypotheses": "cross-disease patterns surfaced by the Hypothesis agent",
}

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384


def main() -> int:
    env = load_env()
    for k, v in env.items():
        os.environ.setdefault(k, v)

    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    client = QdrantClient(url=url)

    # 1. Create / upsert collections
    existing = {c.name for c in client.get_collections().collections}
    for name, desc in COLLECTIONS.items():
        if name in existing:
            print(f"  [skip] {name} already exists")
            continue
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )
        print(f"  [OK] created {name}  -- {desc}")

    # 2. Smoke test — embed + upsert + search one doc into `papers`
    print()
    print("[smoke test] loading fastembed BAAI/bge-small-en-v1.5 ...")
    emb = TextEmbedding(model_name=EMBED_MODEL)
    sample_text = (
        "neuroprotection in hypoxic-ischemic encephalopathy via cord blood therapy"
    )
    vector = next(emb.embed([sample_text]))
    client.upsert(
        collection_name="papers",
        points=[
            PointStruct(
                id=1,
                vector=vector.tolist(),
                payload={
                    "kind": "smoke_test",
                    "text": sample_text,
                    "source": "setup_qdrant.py",
                },
            )
        ],
    )
    print(f"  [OK] embedded + upserted 1 doc into papers (vec dim={len(vector)})")

    # 3. Search round-trip (qdrant-client 1.18+: query_points replaces search)
    query_vec = next(emb.embed(["cord blood HIE"]))
    response = client.query_points(
        collection_name="papers",
        query=query_vec.tolist(),
        limit=3,
    )
    print(f"  [OK] query_points returned {len(response.points)} hit(s)")
    for r in response.points:
        print(f"    score={r.score:.3f}  payload={r.payload}")

    # 4. Final summary
    print()
    print("=== Qdrant collections ===")
    for c in client.get_collections().collections:
        info = client.get_collection(c.name)
        # qdrant-client 1.18: vectors_count removed, use points_count
        print(
            f"  {c.name:12} points={info.points_count or 0}  " f"status={info.status}"
        )
    print("\n[OK] Qdrant setup complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
