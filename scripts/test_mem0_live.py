"""
test_mem0_live — exercise mem0 end-to-end.

Verifies cross-agent shared memory:
  1. mem0 wires up Qdrant + Anthropic + bge-small embedder
  2. "spider" agent writes a memory
  3. "analyzer" agent reads it back through mem0's semantic search

If this script PASSES, the Phase 0+ row "mem0 cross-agent test" flips from
PARTIAL to PASS. Costs ~$0.001 — one Haiku call for fact extraction.

Usage:
    .venv/Scripts/python.exe -m scripts.test_mem0_live
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

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

    try:
        from mem0 import Memory
    except Exception as e:
        print(f"[FAIL] mem0 import: {e}")
        return 1

    config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "mem0_shared",
                "host": "localhost",
                "port": 6333,
                "embedding_model_dims": 384,
            },
        },
        "llm": {
            "provider": "anthropic",
            "config": {
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1024,
            },
        },
        "embedder": {
            "provider": "huggingface",
            "config": {"model": "BAAI/bge-small-en-v1.5"},
        },
    }

    print("[1/4] building Memory client...")
    m = Memory.from_config(config)
    print("[OK] built")

    # Step 2: Spider writes
    print()
    print("[2/4] spider writes a fact to shared memory...")
    spider_messages = [
        {
            "role": "user",
            "content": (
                "I am the Spider agent. I just discovered that erythropoietin (EPO) "
                "has a neuroprotective signal in pediatric HIE; the source is PMID 35124518."
            ),
        }
    ]
    write_result = m.add(spider_messages, user_id="spider", agent_id="spider")
    print(f"[OK] spider wrote: {write_result}")

    # Step 3: Analyzer reads
    print()
    print("[3/4] analyzer queries shared memory ('EPO HIE')...")
    # mem0 >=2.0 API: top-level user_id rejected; pass via filters=
    hits = m.search(
        query="erythropoietin neuroprotection HIE",
        filters={"user_id": "spider"},
        limit=3,
    )
    print(f"[OK] analyzer got {len(hits.get('results', []))} hit(s):")
    for h in hits.get("results", []):
        memory_txt = h.get("memory") or h.get("text") or str(h)
        score = h.get("score", "-")
        print(f"    score={score} memory={memory_txt[:200]!r}")

    # Step 4: verdict
    print()
    print("[4/4] verdict")
    ok = len(hits.get("results", [])) >= 1
    print(
        f"[{'PASS' if ok else 'FAIL'}] cross-agent memory loop "
        f"({'>=1 hit' if ok else 'no hits returned'})"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
