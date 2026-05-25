"""Phase 7.5 Rule #12 - PDF ≥ 5 primary sources.

Any PDF that surfaces to the family or a clinician MUST cite at least
5 primary sources. "Primary" means a PubMed entry, a DOI URL, a
ClinicalTrials.gov registration, or a Cochrane review URL. Personal
notes, internal documents, and Telegram screenshots do NOT count.

This module ships ONLY the guard. The PDF builder itself
(``brain/docs/pdf_builder.py``) is Phase 7.7 scope; the guard is
import-ready so any builder added in Phase 7.6/7.7 can call:

    from brain.common.pdf_guard import assert_min_primary_sources
    assert_min_primary_sources(self.citations, doc_id=self.id)

before flushing the PDF to disk.

Reference:
    .claude/agents/v7-constitution.md Rule #12 row
    v7_architecture/70_PHASES/77_PHASE_7_7_ACCEPTANCE_WINDOW_2W.md
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Primary-source patterns
# ---------------------------------------------------------------------------
# Substring match, case-insensitive. Conservative list; expand only via
# a constitutional_overrides row + this module update.
PRIMARY_SOURCE_PATTERNS: tuple[str, ...] = (
    "pubmed.ncbi.nlm.nih.gov",
    "doi.org",
    "clinicaltrials.gov",
    "cochranelibrary.com",
)

DEFAULT_MIN_PRIMARY_SOURCES = 5


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class InsufficientSourcesError(ValueError):
    """Raised when a PDF would ship with fewer than the required primary sources."""


# ---------------------------------------------------------------------------
# Counters + asserts
# ---------------------------------------------------------------------------
def count_primary_sources(citations: list[str]) -> int:
    """Return the number of `citations` matching a primary-source pattern.

    Substring match, case-insensitive. A single citation contributes at
    most 1 to the count (deduplication is the caller's responsibility).

    Args:
        citations: list of citation strings (URLs, PMIDs, plain text).

    Returns:
        Integer count in ``[0, len(citations)]``.
    """
    if not isinstance(citations, list):
        raise TypeError(
            f"count_primary_sources expects list; got {type(citations).__name__}"
        )
    count = 0
    for c in citations:
        if not isinstance(c, str):
            continue
        lowered = c.lower()
        if any(p in lowered for p in PRIMARY_SOURCE_PATTERNS):
            count += 1
    return count


def assert_min_primary_sources(
    citations: list[str],
    *,
    minimum: int = DEFAULT_MIN_PRIMARY_SOURCES,
    doc_id: str = "unknown",
) -> None:
    """Raise InsufficientSourcesError if primary-source count < minimum.

    Args:
        citations: list of citation strings.
        minimum: required count (default 5).
        doc_id: caller-supplied PDF identifier used in the error
            message (does NOT include raw citation content, so the
            message is safe to log).

    Raises:
        InsufficientSourcesError: count_primary_sources(citations) < minimum.
    """
    actual = count_primary_sources(citations)
    if actual < minimum:
        raise InsufficientSourcesError(
            f"Phase 7.5 Rule #12: doc_id={doc_id!r} has {actual} primary "
            f"source(s); minimum required = {minimum}. Primary patterns: "
            f"{PRIMARY_SOURCE_PATTERNS}"
        )


__all__ = [
    "DEFAULT_MIN_PRIMARY_SOURCES",
    "InsufficientSourcesError",
    "PRIMARY_SOURCE_PATTERNS",
    "assert_min_primary_sources",
    "count_primary_sources",
]
