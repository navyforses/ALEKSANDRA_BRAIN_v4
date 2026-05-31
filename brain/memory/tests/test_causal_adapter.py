"""brain/memory/tests/test_causal_adapter.py — Phase 7.1 Days 8-9 unit tests.

Scope:
  - CausalNeo4jAdapter.write_causal_edge happy path
  - Each invariant violation gets raised through the adapter
  - add_episode_deprecated raises NotImplementedError + DeprecationWarning
  - Validation runs BEFORE any CREATE cypher (no half-writes)
  - delete_edge returns True/False on hit/miss

All neo4j driver/session calls are mocked. No live DB.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from brain.memory.causal_adapter import (
    CausalNeo4jAdapter,
    add_episode_deprecated,
)
from brain.memory.edge_taxonomy import (
    CausalEdge,
    CausalEdgeError,
    CausalEdgeType,
)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------
class _SessionMock:
    """Mock neo4j session that returns scriptable results per query keyword.

    `run()` calls are recorded; behaviour is driven by the `responses` map
    keyed on a substring search of the cypher query. Each value is a function
    that returns a list of result records (each record is a dict).
    """

    def __init__(self, responses: dict[str, Any]):
        self.responses = responses
        self.calls: list[tuple[str, dict]] = []

    def run(self, cypher: str, **params: Any) -> "_ResultMock":
        self.calls.append((cypher, params))
        for keyword, handler in self.responses.items():
            if keyword in cypher:
                rows = handler(params) if callable(handler) else handler
                return _ResultMock(rows)
        return _ResultMock([])

    def __enter__(self) -> "_SessionMock":
        return self

    def __exit__(self, *_: Any) -> None:
        return None


class _ResultMock:
    """Mock neo4j Result: iterable of dict records + .single() helper."""

    def __init__(self, rows: list[dict]):
        self.rows = list(rows)

    def __iter__(self):
        return iter(self.rows)

    def single(self) -> dict:
        return self.rows[0] if self.rows else {}


def _driver_with(session_mock: _SessionMock) -> Any:
    driver = MagicMock()
    driver.session.return_value = session_mock
    return driver


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------
def test_write_causal_edge_happy_path_causes() -> None:
    """A clean CAUSES edge writes successfully and returns audit envelope."""
    edge = CausalEdge(
        source_id=10,
        target_id=20,
        edge_type=CausalEdgeType.CAUSES,
        confidence=0.8,
        citation="PMID:12345",
        mechanism="direct activation",
    )
    session = _SessionMock(
        {
            "CAUSES|INHIBITS|MEDIATES": [],  # empty DAG → no cycle risk
            "CREATE (s)": [{"edge_id": 999}],
        }
    )
    adapter = CausalNeo4jAdapter(_driver_with(session))

    result = adapter.write_causal_edge(edge)

    assert result["edge_id"] == 999
    assert result["edge_type"] == "CAUSES"
    assert result["source_id"] == 10
    assert result["target_id"] == 20
    assert result["citation_complete"] is True
    assert "written_at" in result


def test_write_causal_edge_tbd_citation_marks_incomplete() -> None:
    """TBD-Day-7-backfill citation passes validation but marks citation_complete=False."""
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.INHIBITS,
        confidence=0.5,
        citation="TBD-Day-7-backfill",
    )
    session = _SessionMock(
        {
            "CAUSES|INHIBITS|MEDIATES": [],
            "CREATE (s)": [{"edge_id": 1}],
        }
    )
    adapter = CausalNeo4jAdapter(_driver_with(session))
    result = adapter.write_causal_edge(edge)
    assert result["citation_complete"] is False


def test_write_causal_edge_passes_audit_fields_to_cypher() -> None:
    """Day-6 carry-forward: legacy_type + classified_by + rationale persist."""
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.CAUSES,
        confidence=0.5,
        citation="PMID:1",
        legacy_type="RELATED_TO",
        classified_by="phase_7_1_day_6",
        classified_rationale="deterministic rule: mechanism keyword 'activates'",
    )
    session = _SessionMock(
        {
            "CAUSES|INHIBITS|MEDIATES": [],
            "CREATE (s)": [{"edge_id": 1}],
        }
    )
    adapter = CausalNeo4jAdapter(_driver_with(session))
    adapter.write_causal_edge(edge)

    create_calls = [c for c in session.calls if "CREATE (s)" in c[0]]
    assert len(create_calls) == 1
    params = create_calls[0][1]
    assert params["legacy_type"] == "RELATED_TO"
    assert params["classified_by"] == "phase_7_1_day_6"
    assert "deterministic" in params["classified_rationale"]


# ---------------------------------------------------------------------------
# Validation-first ordering — invariant violations stop the write
# ---------------------------------------------------------------------------
def test_write_rejects_mediates_without_segment_edges() -> None:
    """MEDIATES with via_node but no segments fails invariant 5."""
    edge = CausalEdge(
        source_id="X",
        target_id="Y",
        edge_type=CausalEdgeType.MEDIATES,
        confidence=0.5,
        citation="PMID:1",
        via_node="M",
    )
    # Empty existing-edges check → MEDIATES segment-existence lookup returns False
    session = _SessionMock(
        {
            "MATCH (s)-[r:CAUSES]->(t)": [{"c": 0}],
            "CAUSES|INHIBITS|MEDIATES": [],
            "MATCH (n)": [{"c": 1}],
        }
    )
    adapter = CausalNeo4jAdapter(_driver_with(session))
    with pytest.raises(CausalEdgeError, match="MEDIATES"):
        adapter.write_causal_edge(edge)
    # No CREATE should have been attempted
    assert not any("CREATE (s)" in c[0] for c in session.calls)


def test_write_rejects_dag_cycle() -> None:
    """Adding C->A when A->B->C already exists must fail invariant 7b."""
    edge = CausalEdge(
        source_id="C",
        target_id="A",
        edge_type=CausalEdgeType.CAUSES,
        confidence=0.5,
        citation="PMID:1",
    )
    session = _SessionMock(
        {
            "CAUSES|INHIBITS|MEDIATES": [
                {"src": "A", "tgt": "B", "et": "CAUSES"},
                {"src": "B", "tgt": "C", "et": "CAUSES"},
            ],
        }
    )
    adapter = CausalNeo4jAdapter(_driver_with(session))
    with pytest.raises(CausalEdgeError, match="cycle"):
        adapter.write_causal_edge(edge)
    assert not any("CREATE (s)" in c[0] for c in session.calls)


def test_write_rejects_confounds_with_missing_node() -> None:
    """CONFOUNDS edge listing a non-existent node fails invariant 6."""
    edge = CausalEdge(
        source_id="A",
        target_id="B",
        edge_type=CausalEdgeType.CONFOUNDS,
        confidence=0.5,
        citation="PMID:1",
        also_confounds=["GHOST"],
    )

    # node_exists_lookup returns 0 for any id → all nodes "missing"
    def respond(params):
        if "nid" in params:
            return [{"c": 0}]
        return [{"c": 0}]

    session = _SessionMock(
        {
            "MATCH (n) WHERE id(n) = $nid": respond,
            "CAUSES|INHIBITS|MEDIATES": [],
        }
    )
    adapter = CausalNeo4jAdapter(_driver_with(session))
    with pytest.raises(CausalEdgeError, match="CONFOUNDS"):
        adapter.write_causal_edge(edge)
    assert not any("CREATE (s)" in c[0] for c in session.calls)


def test_write_rejects_moderates_with_unknown_hash() -> None:
    """MODERATES referring to a non-existent edge fails invariant 7a."""
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.MODERATES,
        confidence=0.5,
        citation="PMID:1",
        moderates_edge="deadbeefcafe0000",
    )
    session = _SessionMock(
        {
            # the hash lookup walks all edges → return zero
            "MATCH (s)-[r]->(t) RETURN id(s)": [],
            "CAUSES|INHIBITS|MEDIATES": [],
            "MATCH (n) WHERE id(n) = $nid": [{"c": 1}],
        }
    )
    adapter = CausalNeo4jAdapter(_driver_with(session))
    with pytest.raises(CausalEdgeError, match="moderates_edge"):
        adapter.write_causal_edge(edge)
    assert not any("CREATE (s)" in c[0] for c in session.calls)


# ---------------------------------------------------------------------------
# Edge-type interpolation safety
# ---------------------------------------------------------------------------
def test_write_uses_correct_edge_label_in_cypher() -> None:
    """INHIBITS edge produces a Cypher CREATE with `r:INHIBITS`."""
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.INHIBITS,
        confidence=0.5,
        citation="PMID:1",
    )
    session = _SessionMock(
        {
            "CAUSES|INHIBITS|MEDIATES": [],
            "CREATE (s)": [{"edge_id": 1}],
        }
    )
    adapter = CausalNeo4jAdapter(_driver_with(session))
    adapter.write_causal_edge(edge)
    create_cypher = next(c[0] for c in session.calls if "CREATE (s)" in c[0])
    assert ":INHIBITS" in create_cypher
    assert ":CAUSES" not in create_cypher.split("CREATE")[1]


# ---------------------------------------------------------------------------
# delete_edge
# ---------------------------------------------------------------------------
def test_delete_edge_returns_true_when_deleted() -> None:
    session = _SessionMock({"DELETE r": [{"c": 1}]})
    adapter = CausalNeo4jAdapter(_driver_with(session))
    assert adapter.delete_edge(42) is True


def test_delete_edge_returns_false_when_missing() -> None:
    session = _SessionMock({"DELETE r": [{"c": 0}]})
    adapter = CausalNeo4jAdapter(_driver_with(session))
    assert adapter.delete_edge(9999) is False


# ---------------------------------------------------------------------------
# Deprecated shim
# ---------------------------------------------------------------------------
def test_add_episode_deprecated_raises_not_implemented() -> None:
    with pytest.warns(DeprecationWarning):
        with pytest.raises(NotImplementedError, match="Phase 7.1"):
            add_episode_deprecated()


def test_add_episode_deprecated_warning_mentions_replacement() -> None:
    with pytest.warns(DeprecationWarning, match="CausalNeo4jAdapter"):
        with pytest.raises(NotImplementedError):
            add_episode_deprecated()


# ---------------------------------------------------------------------------
# Invariant 1+2 caught at Pydantic layer — adapter never even sees them
# ---------------------------------------------------------------------------
def test_invalid_confidence_caught_at_construction_not_adapter() -> None:
    """The Pydantic layer rejects confidence>1 before adapter is ever called."""
    with pytest.raises(Exception):
        CausalEdge(
            source_id=1,
            target_id=2,
            edge_type=CausalEdgeType.CAUSES,
            confidence=2.0,
            citation="PMID:1",
        )


def test_invalid_citation_caught_at_construction_not_adapter() -> None:
    """The Pydantic regex rejects bad citations before adapter is ever called."""
    with pytest.raises(Exception):
        CausalEdge(
            source_id=1,
            target_id=2,
            edge_type=CausalEdgeType.CAUSES,
            confidence=0.5,
            citation="just nope",
        )


# ---------------------------------------------------------------------------
# Audit envelope shape
# ---------------------------------------------------------------------------
def test_audit_envelope_has_all_required_keys() -> None:
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.CAUSES,
        confidence=0.5,
        citation="PMID:1",
    )
    session = _SessionMock(
        {
            "CAUSES|INHIBITS|MEDIATES": [],
            "CREATE (s)": [{"edge_id": 7}],
        }
    )
    adapter = CausalNeo4jAdapter(_driver_with(session))
    audit = adapter.write_causal_edge(edge)
    for key in (
        "edge_id",
        "edge_type",
        "source_id",
        "target_id",
        "citation_complete",
        "written_at",
    ):
        assert key in audit
