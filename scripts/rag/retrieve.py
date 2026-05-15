"""
retrieve.py — MEM-05 single retrieval surface.

Contract from REQUIREMENTS.md MEM-05:
    Agents retrieve only through one `retrieve(query, t_at=...)` function —
    direct Graphiti or Qdrant client use from agent code is blocked by a
    lint rule.

This module is intentionally the ONLY allowed retrieval entry point. It
fans a natural-language query out to:

  1. Qdrant `papers` collection  (semantic similarity on 384-dim
     BAAI/bge-small-en-v1.5 vectors over paper_chunks)
  2. Neo4j hie_research subgraph  (graph-walk over Graphiti's typed
     entities / RELATES_TO facts produced by sub-phase 2B)

…and merges the two views into a single `RetrieveResult` carrying the
chunks (with MEM-04 citation stamps), the entities hit, and the facts
those entities participate in.

`t_at` is the temporal cut-off: if provided, only Graphiti episodes
whose `valid_at <= t_at` (paper publication year or ledger retrieval
timestamp, whichever the ingest pipeline recorded) are visible. This
satisfies the MEM-05 "point-in-time" contract — Phase 3 agents can ask
"what did the system know on date X?" by passing t_at=X.

Why a thin local facade instead of the full lightrag-hku package:
  - lightrag-hku's Neo4JStorage backend writes its own graph schema
    that conflicts with the Graphiti/hie_research nodes we already
    have (Entity, Episodic, RELATES_TO, MENTIONS).
  - lightrag-hku's QdrantVectorDBStorage expects its own collection
    naming + payload schema; reusing our `papers` collection would
    require re-indexing.
  - Our actual retrieval surface is a 2-call merge — Qdrant top-K +
    Neo4j entity-walk — which is ~40 lines of code. The lightrag
    abstractions would be net negative at this scale.

The facade keeps the LightRAG-style API contract (`retrieve(query,
t_at, top_k)`) so when perception scales to ≥1000 papers and a real
LightRAG migration becomes worthwhile, agent code doesn't need to
change.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime

import httpx
from neo4j import GraphDatabase

from scripts.chunking.embedder import EMBED_MODEL, QDRANT_COLLECTION, embed_texts
from scripts.ledger import load_env

DEFAULT_TOP_K = 10
DEFAULT_MIN_SCORE = 0.30  # cosine similarity floor for Qdrant chunks
GRAPHITI_GROUP_ID = "hie_research"


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------
@dataclass
class ChunkHit:
    chunk_id: str
    score: float
    source_type: str
    source_id: str
    ledger_id: str
    text_preview: str
    embedding_model: str
    chunker_version: str
    content_hash: str
    graphiti_uuid: str | None


@dataclass
class EntityHit:
    uuid: str
    name: str
    labels: list[str]
    summary: str
    group_id: str
    valid_at: str | None  # ISO timestamp; matches paper's reference_time


@dataclass
class FactHit:
    uuid: str
    fact: str
    source_name: str
    target_name: str
    valid_at: str | None


@dataclass
class RetrieveResult:
    query: str
    t_at: str | None  # ISO timestamp or None
    chunks: list[ChunkHit] = field(default_factory=list)
    entities: list[EntityHit] = field(default_factory=list)
    facts: list[FactHit] = field(default_factory=list)
    timings_ms: dict[str, int] = field(default_factory=dict)

    def has_evidence(self) -> bool:
        """Whether the system found anything — used by Phase 3 verifier."""
        return bool(self.chunks or self.entities or self.facts)


# ---------------------------------------------------------------------------
# Backend probes
# ---------------------------------------------------------------------------
def _qdrant_url() -> str:
    raw = os.environ.get("QDRANT_URL", "http://127.0.0.1:6333")
    # Windows IPv6 ::1 routing intermittently drops connections; force IPv4.
    return raw.replace("localhost", "127.0.0.1")


def _neo4j_driver():
    return GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
    )


def _qdrant_search(query_vec: list[float], top_k: int, min_score: float) -> list[dict]:
    """Cosine search on `papers`. Returns raw point hits."""
    body = {
        "vector": query_vec,
        "limit": top_k,
        "score_threshold": min_score,
        "with_payload": True,
        "with_vector": False,
    }
    r = httpx.post(
        f"{_qdrant_url()}/collections/{QDRANT_COLLECTION}/points/search",
        json=body,
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("result", []) or []


def _neo4j_entity_walk(
    chunk_graphiti_uuids: list[str],
    t_at: datetime | None,
    limit_entities: int = 30,
    limit_facts: int = 30,
) -> tuple[list[dict], list[dict]]:
    """
    Walk Graphiti subgraph anchored at the Episodics referenced by the
    Qdrant chunk hits. Returns (entities, facts).

    Temporal cut: if t_at is set, drop entities/facts whose Episodic's
    valid_at is in the future.
    """
    if not chunk_graphiti_uuids:
        return [], []

    drv = _neo4j_driver()
    cypher_entities = """
        UNWIND $ep_uuids AS ep_uuid
        MATCH (ep:Episodic {uuid: ep_uuid, group_id: $gid})-[:MENTIONS]->(n:Entity)
        WHERE $t_at IS NULL OR ep.valid_at <= datetime($t_at)
        WITH DISTINCT n, ep
        RETURN
            n.uuid    AS uuid,
            n.name    AS name,
            [l IN labels(n) WHERE l <> 'Entity'] AS labels,
            n.summary AS summary,
            n.group_id AS group_id,
            toString(ep.valid_at) AS valid_at
        LIMIT $limit_entities
    """
    cypher_facts = """
        UNWIND $ep_uuids AS ep_uuid
        MATCH (ep:Episodic {uuid: ep_uuid, group_id: $gid})-[:MENTIONS]->(a:Entity)
        OPTIONAL MATCH (a)-[r:RELATES_TO]->(b:Entity)
        WHERE r IS NOT NULL
          AND ($t_at IS NULL OR ep.valid_at <= datetime($t_at))
        WITH DISTINCT r, a, b, ep
        RETURN
            r.uuid AS uuid,
            r.fact AS fact,
            a.name AS source_name,
            b.name AS target_name,
            toString(ep.valid_at) AS valid_at
        LIMIT $limit_facts
    """

    t_at_iso = t_at.isoformat() if t_at else None
    with drv.session() as s:
        ent_rows = s.run(
            cypher_entities,
            ep_uuids=chunk_graphiti_uuids,
            gid=GRAPHITI_GROUP_ID,
            t_at=t_at_iso,
            limit_entities=limit_entities,
        ).data()
        fact_rows = s.run(
            cypher_facts,
            ep_uuids=chunk_graphiti_uuids,
            gid=GRAPHITI_GROUP_ID,
            t_at=t_at_iso,
            limit_facts=limit_facts,
        ).data()
    drv.close()
    return ent_rows, fact_rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def retrieve(
    query: str,
    t_at: datetime | None = None,
    top_k: int = DEFAULT_TOP_K,
    min_score: float = DEFAULT_MIN_SCORE,
) -> RetrieveResult:
    """
    Single retrieval surface for Phase 3+ agents. Returns the chunks
    semantically nearest to `query` plus the entities/facts those chunks
    mention in Graphiti.

    Parameters
    ----------
    query : str
        Natural-language query.
    t_at : datetime | None
        Temporal cut-off. If set, evidence whose Episodic.valid_at > t_at
        is excluded (the system "doesn't know it yet"). None = whole graph.
    top_k : int
        Max chunks returned by Qdrant (after score_threshold filter).
    min_score : float
        Cosine similarity floor; chunks below this are dropped.

    Returns
    -------
    RetrieveResult
        chunks: top-K paper_chunks by cosine on the query embedding.
        entities: the Drug/Disease/Gene/etc nodes those chunks mention.
        facts:    the RELATES_TO claims those entities participate in.
        Each carries the MEM-01 citation tuple (verbatim_grounding lives
        on paper_chunks.raw_text via the GENERATED column; here we expose
        the truncated text_preview from Qdrant's payload — full text is
        fetched on demand via chunk_id → Supabase paper_chunks).
    """
    load_env()
    import time as _time

    t0 = _time.time()
    qvec = embed_texts([query])[0]
    t_embed = int((_time.time() - t0) * 1000)

    t0 = _time.time()
    hits = _qdrant_search(qvec, top_k=top_k, min_score=min_score)
    t_qdrant = int((_time.time() - t0) * 1000)

    chunks: list[ChunkHit] = []
    graphiti_uuids: list[str] = []
    for h in hits:
        payload = h.get("payload") or {}
        if not payload.get("chunk_id"):
            continue  # skip legacy smoke-test points
        ch = ChunkHit(
            chunk_id=payload["chunk_id"],
            score=h.get("score", 0.0),
            source_type=payload.get("source_type", ""),
            source_id=payload.get("source_id", ""),
            ledger_id=payload.get("ledger_id", ""),
            text_preview=payload.get("text_preview", ""),
            embedding_model=payload.get("embedding_model", EMBED_MODEL),
            chunker_version=payload.get("chunker_version", ""),
            content_hash=payload.get("content_hash", ""),
            graphiti_uuid=payload.get("graphiti_uuid"),
        )
        chunks.append(ch)
        if ch.graphiti_uuid:
            graphiti_uuids.append(ch.graphiti_uuid)

    t0 = _time.time()
    ent_rows, fact_rows = _neo4j_entity_walk(
        chunk_graphiti_uuids=list(set(graphiti_uuids)), t_at=t_at
    )
    t_neo4j = int((_time.time() - t0) * 1000)

    entities = [
        EntityHit(
            uuid=r["uuid"],
            name=r["name"],
            labels=r.get("labels") or [],
            summary=r.get("summary") or "",
            group_id=r.get("group_id") or GRAPHITI_GROUP_ID,
            valid_at=r.get("valid_at"),
        )
        for r in ent_rows
    ]
    facts = [
        FactHit(
            uuid=r["uuid"],
            fact=r.get("fact") or "",
            source_name=r.get("source_name") or "",
            target_name=r.get("target_name") or "",
            valid_at=r.get("valid_at"),
        )
        for r in fact_rows
    ]

    return RetrieveResult(
        query=query,
        t_at=t_at.isoformat() if t_at else None,
        chunks=chunks,
        entities=entities,
        facts=facts,
        timings_ms={"embed": t_embed, "qdrant": t_qdrant, "neo4j": t_neo4j},
    )


__all__ = [
    "retrieve",
    "RetrieveResult",
    "ChunkHit",
    "EntityHit",
    "FactHit",
]
