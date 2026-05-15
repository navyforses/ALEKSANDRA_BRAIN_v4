"""
chunker.py — Phase 2 sub-phase 2A.

Wraps LangChain's RecursiveCharacterTextSplitter so the rest of the
pipeline only sees a clean Chunk dataclass. Defaults match BAAI/bge-
small-en-v1.5's effective context window (512 tokens ≈ ~2000 chars,
but smaller chunks lift retrieval precision):

    chunk_size    = 512 chars
    chunk_overlap =  64 chars
    separators    = ["\\n\\n", "\\n", ". ", " ", ""]  (LangChain default)

For texts shorter than chunk_size we emit a single chunk so very short
abstracts and bio/medRxiv RSS entries don't get dropped.
"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 64

# CHUNKER_VERSION is stamped on every Qdrant point's payload (MEM-04). If you
# change the splitter algorithm, the chunk size, the overlap, or the separator
# set, BUMP this string so old vectors are distinguishable from new ones during
# any rechunk pass. Format: "<algo>-<size>-<overlap>-v<n>".
CHUNKER_VERSION = "rcst-512-64-v1"


@dataclass
class Chunk:
    chunk_index: int
    raw_text: str
    char_count: int

    @property
    def chunk_type(self) -> str:
        # very short -> abstract; otherwise plain text
        if self.char_count <= DEFAULT_CHUNK_SIZE and self.chunk_index == 0:
            return "abstract"
        return "text"


# Module-level singleton so repeated calls don't re-instantiate the splitter.
_splitter: RecursiveCharacterTextSplitter | None = None


def _get_splitter(
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> RecursiveCharacterTextSplitter:
    global _splitter
    if _splitter is None:
        _splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
    return _splitter


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Chunk]:
    """
    Split text into chunks. Empty input -> empty list. Single-chunk
    short texts get chunk_index=0 and chunk_type=abstract.
    """
    text = (text or "").strip()
    if not text:
        return []

    if len(text) <= chunk_size:
        return [Chunk(chunk_index=0, raw_text=text, char_count=len(text))]

    splitter = _get_splitter(chunk_size, chunk_overlap)
    pieces = splitter.split_text(text)
    return [
        Chunk(chunk_index=i, raw_text=piece, char_count=len(piece))
        for i, piece in enumerate(pieces)
        if piece.strip()
    ]
