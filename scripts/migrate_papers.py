"""
Papers migration — Phase 0 §6.1 placeholder

Reads scientific PDFs/notes from /uploads, extracts metadata + abstract,
scores relevance to HIE, and writes to:
  1. Supabase papers table
  2. Qdrant papers collection (via fastembed)
  3. Neo4j as Paper nodes (via Graphiti entity extraction)

TODO: implement after §1.1, §1.2, §1.3 are green.
"""

from __future__ import annotations


def main() -> None:
    raise NotImplementedError(
        "Phase 0 §6.1 — to be implemented after Supabase + Qdrant + Neo4j are live."
    )


if __name__ == "__main__":
    main()
