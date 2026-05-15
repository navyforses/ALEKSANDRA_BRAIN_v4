"""
graphiti_client.py — Phase 2 sub-phase 2B.

Singleton Graphiti instance configured for the project:
  - Neo4j connection from .env (NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
  - LLM: Claude Haiku 4.5 ('claude-haiku-4-5-20251001'), temperature=0.2
  - Embedder: fastembed BAAI/bge-small-en-v1.5 (reuses Phase 0 model)
  - group_id: 'hie_research' for all Phase 2 episodes

build_indices_and_constraints() must be called ONCE per fresh Neo4j
database — `ensure_indices()` here is idempotent (safe to re-run).
"""

from __future__ import annotations

import os

# CRITICAL: EMBEDDING_DIM must be set BEFORE graphiti_core is imported.
# graphiti_core/embedder/client.py reads `os.getenv('EMBEDDING_DIM', 1024)` at
# module-load time and uses that constant as the size of the zero-vector
# fallback in graphiti_core/search/search.py:152 (`[0.0] * EMBEDDING_DIM`).
# Our fastembed adapter returns 384-dim BAAI/bge-small-en-v1.5 vectors, so the
# fallback must match or `vector.similarity.cosine(name_embedding, $vec)` fails
# with "Argument b is not a valid vector for this similarity function".
os.environ.setdefault("EMBEDDING_DIM", "384")

from graphiti_core import Graphiti
from graphiti_core.embedder.client import EmbedderClient
from graphiti_core.llm_client.anthropic_client import AnthropicClient
from graphiti_core.llm_client.config import LLMConfig

from scripts.ledger import load_env

GROUP_ID = "hie_research"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 8192

_graphiti: Graphiti | None = None
_indices_initialised = False


class _FastEmbedAdapter(EmbedderClient):
    """
    Bridge fastembed (already used by setup_qdrant.py + scripts/chunking/embedder.py)
    into Graphiti's EmbedderClient protocol. Keeps Phase 2 on a single
    embedding model so the Qdrant `papers` collection and Graphiti both
    speak 384-dim BAAI/bge-small-en-v1.5.

    Contract: EmbedderClient.create() returns a SINGLE list[float] regardless
    of whether input_data is a str or a list[str] — Graphiti's search code
    passes the result straight into Cypher as `$search_vector`, which must be
    a 1-D LIST<FLOAT> for `vector.similarity.cosine()`. Returning a list of
    vectors would bind as a nested list and Neo4j throws
    "Argument b is not a valid vector for this similarity function". See
    graphiti_core/embedder/openai.py for the reference implementation
    (returns `result.data[0].embedding[: embedding_dim]`).
    """

    def __init__(self) -> None:
        from scripts.chunking.embedder import _get_embedder

        self._embedder = _get_embedder()

    async def create(self, input_data: str | list[str]) -> list[float]:
        text = (
            input_data
            if isinstance(input_data, str)
            else (input_data[0] if input_data else "")
        )
        vec = next(self._embedder.embed([text]))
        return vec.tolist()

    async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self._embedder.embed(input_data_list)]


def _build_anthropic_client() -> AnthropicClient:
    load_env()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY missing in .env")
    config = LLMConfig(
        api_key=api_key,
        model=DEFAULT_MODEL,
        small_model=DEFAULT_MODEL,
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=DEFAULT_MAX_TOKENS,
    )
    return AnthropicClient(config=config, cache=False)


def get_graphiti() -> Graphiti:
    """Lazy singleton. First call wires up Neo4j + Anthropic + fastembed."""
    global _graphiti
    if _graphiti is not None:
        return _graphiti

    load_env()
    uri = os.environ.get("NEO4J_URI", "").strip()
    user = os.environ.get("NEO4J_USERNAME", "").strip()
    password = os.environ.get("NEO4J_PASSWORD", "").strip()
    if not uri or not user or not password:
        raise RuntimeError("NEO4J_URI/USERNAME/PASSWORD missing in .env")

    _graphiti = Graphiti(
        uri=uri,
        user=user,
        password=password,
        llm_client=_build_anthropic_client(),
        embedder=_FastEmbedAdapter(),
    )
    return _graphiti


async def ensure_indices() -> None:
    """Idempotent — safe to call on every run; Graphiti's helper no-ops if exists."""
    global _indices_initialised
    if _indices_initialised:
        return
    g = get_graphiti()
    await g.build_indices_and_constraints()
    _indices_initialised = True


async def close_graphiti() -> None:
    """Release Neo4j driver — call once at process exit."""
    global _graphiti
    if _graphiti is None:
        return
    try:
        await _graphiti.close()
    except Exception:
        pass
    _graphiti = None
