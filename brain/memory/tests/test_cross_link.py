"""brain/memory/tests/test_cross_link.py — Phase 7.1 Day 9 unit tests.

Scope:
  - link_causal_nodes_to_dimensions: linked / ambiguous / unmatched buckets
  - dry_run skips the SET cypher but still walks every dim
  - Audit JSON shape per status
  - dimension_loader injection avoids Supabase calls in tests

All neo4j driver/session calls are mocked. No live DB.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from brain.belief.persistence import BeliefDimension
from brain.memory.cross_link import link_causal_nodes_to_dimensions


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------
class _SessionMock:
    """Mock neo4j session — programmable match results per dim_name."""

    def __init__(self, match_results: dict[str, list[dict]]):
        """match_results: dim_name -> list of {nid, name} rows."""
        self.match_results = match_results
        self.calls: list[tuple[str, dict]] = []

    def run(self, cypher: str, **params: Any) -> "_ResultMock":
        self.calls.append((cypher, params))
        # MATCH-on-name (lookup) vs SET (write)
        if "SET n.dimension_ref" in cypher:
            return _ResultMock([])
        # Lookup query: dim_name in params
        dim_name = params.get("dim_name", "")
        rows = self.match_results.get(dim_name, [])
        return _ResultMock(rows)

    def __enter__(self) -> "_SessionMock":
        return self

    def __exit__(self, *_: Any) -> None:
        return None


class _ResultMock:
    def __init__(self, rows: list[dict]):
        self.rows = list(rows)

    def __iter__(self):
        return iter(self.rows)


def _driver_with(session_mock: _SessionMock) -> Any:
    driver = MagicMock()
    driver.session.return_value = session_mock
    return driver


def _make_dim(name: str, dim_id: int = 1) -> BeliefDimension:
    """Build a minimal valid BeliefDimension for a given name."""
    return BeliefDimension(
        id=dim_id,
        name=name,
        distribution="beta",
        prior_params={"alpha": 1.0, "beta": 1.0},
        citation="PMID:1",
    )


# ---------------------------------------------------------------------------
# Linked / ambiguous / unmatched
# ---------------------------------------------------------------------------
def test_single_match_links_and_writes() -> None:
    """One CausalNode matches → linked count +1, SET cypher fires."""
    session = _SessionMock({"GABA-T": [{"nid": 100, "name": "GABA-T"}]})
    dims = [_make_dim("GABA-T", dim_id=5)]
    result = link_causal_nodes_to_dimensions(
        _driver_with(session),
        dimension_loader=lambda: dims,
    )
    assert result["counts"] == {"linked": 1, "ambiguous": 0, "unmatched": 0}
    set_calls = [c for c in session.calls if "SET n.dimension_ref" in c[0]]
    assert len(set_calls) == 1
    assert set_calls[0][1] == {"nid": 100, "dim_id": 5}


def test_dry_run_does_not_write() -> None:
    """dry_run=True still counts but never issues SET."""
    session = _SessionMock({"GABA-T": [{"nid": 100, "name": "GABA-T"}]})
    dims = [_make_dim("GABA-T")]
    result = link_causal_nodes_to_dimensions(
        _driver_with(session),
        dimension_loader=lambda: dims,
        dry_run=True,
    )
    assert result["counts"]["linked"] == 1
    set_calls = [c for c in session.calls if "SET n.dimension_ref" in c[0]]
    assert len(set_calls) == 0


def test_ambiguous_match_is_skipped_not_linked() -> None:
    """Two matches for the same dim → ambiguous bucket, no SET fires."""
    session = _SessionMock(
        {
            "vigabatrin": [
                {"nid": 1, "name": "Vigabatrin"},
                {"nid": 2, "name": "Vigabatrin dose"},
            ]
        }
    )
    dims = [_make_dim("vigabatrin")]
    result = link_causal_nodes_to_dimensions(
        _driver_with(session),
        dimension_loader=lambda: dims,
    )
    assert result["counts"] == {"linked": 0, "ambiguous": 1, "unmatched": 0}
    set_calls = [c for c in session.calls if "SET n.dimension_ref" in c[0]]
    assert len(set_calls) == 0


def test_unmatched_dimension_is_skipped() -> None:
    session = _SessionMock({})  # nothing matches anything
    dims = [_make_dim("nonexistent_dim")]
    result = link_causal_nodes_to_dimensions(
        _driver_with(session),
        dimension_loader=lambda: dims,
    )
    assert result["counts"] == {"linked": 0, "ambiguous": 0, "unmatched": 1}


# ---------------------------------------------------------------------------
# Audit JSON shape
# ---------------------------------------------------------------------------
def test_audit_record_for_linked_has_node_id_and_name() -> None:
    session = _SessionMock({"GABA-T": [{"nid": 100, "name": "GABA-T enzyme"}]})
    dims = [_make_dim("GABA-T")]
    result = link_causal_nodes_to_dimensions(
        _driver_with(session),
        dimension_loader=lambda: dims,
    )
    record = result["audit"][0]
    assert record["status"] == "linked"
    assert record["dim"] == "GABA-T"
    assert record["causal_node_id"] == 100
    assert record["causal_node_name"] == "GABA-T enzyme"


def test_audit_record_for_ambiguous_has_candidates_list() -> None:
    session = _SessionMock(
        {
            "vigabatrin": [
                {"nid": 1, "name": "Vigabatrin"},
                {"nid": 2, "name": "Vigabatrin (drug)"},
            ]
        }
    )
    dims = [_make_dim("vigabatrin")]
    result = link_causal_nodes_to_dimensions(
        _driver_with(session),
        dimension_loader=lambda: dims,
    )
    record = result["audit"][0]
    assert record["status"] == "ambiguous"
    assert record["candidates"] == ["Vigabatrin", "Vigabatrin (drug)"]


def test_audit_record_for_unmatched_has_only_status() -> None:
    session = _SessionMock({})
    dims = [_make_dim("orphan")]
    result = link_causal_nodes_to_dimensions(
        _driver_with(session),
        dimension_loader=lambda: dims,
    )
    record = result["audit"][0]
    assert record["status"] == "unmatched"
    assert record["dim"] == "orphan"


# ---------------------------------------------------------------------------
# Multi-dim mixed batches
# ---------------------------------------------------------------------------
def test_mixed_batch_three_buckets_counted() -> None:
    """Linked + ambiguous + unmatched in one run all show up correctly."""
    session = _SessionMock(
        {
            "GABA-T": [{"nid": 100, "name": "GABA-T"}],
            "vigabatrin": [
                {"nid": 1, "name": "Vigabatrin"},
                {"nid": 2, "name": "Vigabatrin dose"},
            ],
            # 'orphan' returns nothing → unmatched
        }
    )
    dims = [
        _make_dim("GABA-T", dim_id=1),
        _make_dim("vigabatrin", dim_id=2),
        _make_dim("orphan", dim_id=3),
    ]
    result = link_causal_nodes_to_dimensions(
        _driver_with(session),
        dimension_loader=lambda: dims,
    )
    assert result["counts"] == {"linked": 1, "ambiguous": 1, "unmatched": 1}


def test_empty_dimension_list_returns_zero_counts() -> None:
    session = _SessionMock({})
    result = link_causal_nodes_to_dimensions(
        _driver_with(session),
        dimension_loader=lambda: [],
    )
    assert result["counts"] == {"linked": 0, "ambiguous": 0, "unmatched": 0}
    assert result["audit"] == []


# ---------------------------------------------------------------------------
# Cypher query content sanity
# ---------------------------------------------------------------------------
def test_lookup_query_is_case_insensitive() -> None:
    """The MATCH query should use toLower() on both sides for case-insensitivity."""
    session = _SessionMock({"GABA-T": [{"nid": 100, "name": "GABA-T"}]})
    dims = [_make_dim("GABA-T")]
    link_causal_nodes_to_dimensions(
        _driver_with(session),
        dimension_loader=lambda: dims,
    )
    lookup_calls = [c for c in session.calls if "CausalNode" in c[0]]
    assert len(lookup_calls) >= 1
    cypher = lookup_calls[0][0]
    assert "toLower" in cypher


def test_lookup_query_uses_contains_for_substring_fallback() -> None:
    session = _SessionMock({"GABA-T": [{"nid": 100, "name": "GABA-T"}]})
    dims = [_make_dim("GABA-T")]
    link_causal_nodes_to_dimensions(
        _driver_with(session),
        dimension_loader=lambda: dims,
    )
    lookup_calls = [c for c in session.calls if "CausalNode" in c[0]]
    assert "CONTAINS" in lookup_calls[0][0]
