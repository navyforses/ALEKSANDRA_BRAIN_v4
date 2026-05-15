"""
embedder.py — Phase 2 sub-phase 2A.

fastembed BAAI/bge-small-en-v1.5 (384-dim, cosine) + Qdrant upsert.
Same model + same collection (`papers`) that setup_qdrant.py created
in Phase 0, so vector dimension and distance metric match by
construction — no Qdrant collection migration needed.

Two entry points:

  embed_texts(list[str]) -> list[list[float]]
      Local fastembed pass. Cached singleton model. Use for ad-hoc
      ranking / LightRAG bridges.

  upsert_chunks(rows: list[ChunkRow]) -> list[str]
      Embed N raw_texts and upsert to Qdrant `papers` collection.
      Each ChunkRow carries (chunk_id, ledger_id, source_type, source_id,
      raw_text). Returns the list of Qdrant point ids in order, ready
      to be written back into paper_chunks.embedding_id.

Both paths reuse the module-level fastembed singleton so multi-batch
runs don't repay the model-load cost.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Iterable

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from scripts.ledger import load_env

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384
QDRANT_COLLECTION = "papers"
QDRANT_PAYLOAD_TEXT_MAX = 300  # truncate preview field; full text lives in Supabase

_embedder: TextEmbedding | None = None
_qdrant: QdrantClient | None = None


def _get_embedder() -> TextEmbedding:
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedding(model_name=EMBED_MODEL)
    return _embedder


def _get_qdrant() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        load_env()
        url = os.environ.get("QDRANT_URL", "http://localhost:6333")
        _qdrant = QdrantClient(url=url)
    return _qdrant


# ---------------------------------------------------------------------------
# ChunkRow + helpers
# ---------------------------------------------------------------------------
@dataclass
class ChunkRow:
    chunk_id: str  # Supabase paper_chunks.id (UUID as string)
    ledger_id: str  # Supabase evidence_ledger.id
    source_type: str
    source_id: str
    raw_text: str


def embed_texts(texts: Iterable[str]) -> list[list[float]]:
    """Run fastembed on N texts. Returns list of float vectors."""
    emb = _get_embedder()
    return [v.tolist() for v in emb.embed(list(texts))]


def upsert_chunks(rows: list[ChunkRow]) -> list[str]:
    """
    Embed and upsert N chunks into the Qdrant `papers` collection.
    Returns a list of point ids (UUID strings) aligned with `rows`.
    """
    if not rows:
        return []

    vectors = embed_texts([r.raw_text for r in rows])
    client = _get_qdrant()

    point_ids: list[str] = []
    points: list[PointStruct] = []
    for row, vec in zip(rows, vectors):
        pid = str(uuid.uuid4())
        point_ids.append(pid)
        points.append(
            PointStruct(
                id=pid,
                vector=vec,
                payload={
                    "chunk_id": row.chunk_id,
                    "ledger_id": row.ledger_id,
                    "source_type": row.source_type,
                    "source_id": row.source_id,
                    "text_preview": row.raw_text[:QDRANT_PAYLOAD_TEXT_MAX],
                },
            )
        )

    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    return point_ids
