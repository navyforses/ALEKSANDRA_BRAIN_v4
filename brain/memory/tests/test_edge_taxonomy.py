"""brain/memory/tests/test_edge_taxonomy.py — Phase 7.1 Days 8-9 unit tests.

Scope: all 7 invariants in docs/PHASE_7_1_TAXONOMY.md §7.

Invariant coverage map (one or more tests per invariant):
    1. Edge type enum                              → test_edge_type_enum_membership
    2. confidence ∈ [0,1]                          → test_confidence_*
    3. citation regex                              → test_citation_*
    4. validate_mediates_invariant (segments)     → test_mediates_invariant_*
    5. CONFOUNDS also_confounds non-empty + exists → test_confounds_invariant_*
    6. MODERATES hash 16-hex + reference exists    → test_moderates_invariant_*
                                                      / test_moderates_hash_*
    7. DAG invariant on CAUSES+INHIBITS+MEDIATES   → test_dag_invariant_*

Pure unit tests — no live Neo4j. All lookups are passed in as callables.
"""

from __future__ import annotations

import pytest

from brain.memory.edge_taxonomy import (
    CITATION_REGEX,
    DAG_PARTICIPATING_TYPES,
    MAX_RATIONALE_LEN,
    MODERATES_EDGE_HASH_LEN,
    TBD_PLACEHOLDER,
    CausalEdge,
    CausalEdgeError,
    CausalEdgeType,
    compute_edge_hash,
    is_citation_complete,
    validate_confounds_invariant,
    validate_dag_invariant,
    validate_edge_for_write,
    validate_mediates_invariant,
    validate_moderates_invariant,
    validate_structural_invariants,
)


# ---------------------------------------------------------------------------
# Invariant 1 — edge type enum
# ---------------------------------------------------------------------------
def test_edge_type_enum_membership() -> None:
    """Pearl 5-type taxonomy — exactly these five values, no more, no less."""
    assert {e.value for e in CausalEdgeType} == {
        "CAUSES",
        "INHIBITS",
        "MEDIATES",
        "CONFOUNDS",
        "MODERATES",
    }


def test_edge_type_unknown_value_rejected() -> None:
    """Pydantic rejects any string outside the enum."""
    with pytest.raises(Exception):  # pydantic ValidationError or CausalEdgeError
        CausalEdge(
            source_id=1,
            target_id=2,
            edge_type="RELATED_TO",  # type: ignore[arg-type]
            confidence=0.5,
            citation="PMID:12345",
        )


# ---------------------------------------------------------------------------
# Invariant 2 — confidence range
# ---------------------------------------------------------------------------
def test_confidence_zero_accepted() -> None:
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.CAUSES,
        confidence=0.0,
        citation="PMID:1",
    )
    assert edge.confidence == 0.0


def test_confidence_one_accepted() -> None:
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.CAUSES,
        confidence=1.0,
        citation="PMID:1",
    )
    assert edge.confidence == 1.0


def test_confidence_below_zero_rejected() -> None:
    with pytest.raises(Exception):
        CausalEdge(
            source_id=1,
            target_id=2,
            edge_type=CausalEdgeType.CAUSES,
            confidence=-0.01,
            citation="PMID:1",
        )


def test_confidence_above_one_rejected() -> None:
    with pytest.raises(Exception):
        CausalEdge(
            source_id=1,
            target_id=2,
            edge_type=CausalEdgeType.CAUSES,
            confidence=1.01,
            citation="PMID:1",
        )


# ---------------------------------------------------------------------------
# Invariant 3 — citation regex
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "citation",
    [
        "PMID:12345",
        "PMID:99999999",
        "DOI:10.1038/s41597-024-03986-7",
        "https://pubmed.ncbi.nlm.nih.gov/12345",
        "http://example.com/paper.pdf",
        "TBD-Day-7-backfill",
    ],
)
def test_citation_accepted_formats(citation: str) -> None:
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.CAUSES,
        confidence=0.5,
        citation=citation,
    )
    assert edge.citation == citation


@pytest.mark.parametrize(
    "citation",
    [
        "PMID:",  # no digits
        "pmid12345",  # missing colon (regex requires PMID:)
        "ftp://example.com",
        "no-prefix.com",
        "just some text",
    ],
)
def test_citation_rejected_formats(citation: str) -> None:
    with pytest.raises(Exception):
        CausalEdge(
            source_id=1,
            target_id=2,
            edge_type=CausalEdgeType.CAUSES,
            confidence=0.5,
            citation=citation,
        )


def test_citation_regex_is_case_insensitive() -> None:
    """The IGNORECASE flag means lowercase 'pmid:' and 'doi:' are accepted."""
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.CAUSES,
        confidence=0.5,
        citation="pmid:12345",
    )
    assert edge.citation == "pmid:12345"


def test_is_citation_complete_true_for_pmid() -> None:
    assert is_citation_complete("PMID:12345") is True


def test_is_citation_complete_false_for_tbd_placeholder() -> None:
    assert is_citation_complete(TBD_PLACEHOLDER) is False


# ---------------------------------------------------------------------------
# Day-6 carry-forward — rationale capped at 200 chars
# ---------------------------------------------------------------------------
def test_classified_rationale_capped_at_200() -> None:
    long_rationale = "x" * 500
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.CAUSES,
        confidence=0.5,
        citation="PMID:1",
        classified_rationale=long_rationale,
    )
    assert edge.classified_rationale is not None
    assert len(edge.classified_rationale) == MAX_RATIONALE_LEN


def test_classified_rationale_short_preserved() -> None:
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.CAUSES,
        confidence=0.5,
        citation="PMID:1",
        classified_rationale="ok",
    )
    assert edge.classified_rationale == "ok"


# ---------------------------------------------------------------------------
# Invariant 4 — structural required fields per edge type
# ---------------------------------------------------------------------------
def test_structural_mediates_requires_via_node() -> None:
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.MEDIATES,
        confidence=0.5,
        citation="PMID:1",
    )
    with pytest.raises(CausalEdgeError, match="via_node"):
        validate_structural_invariants(edge)


def test_structural_confounds_requires_also_confounds() -> None:
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.CONFOUNDS,
        confidence=0.5,
        citation="PMID:1",
    )
    with pytest.raises(CausalEdgeError, match="also_confounds"):
        validate_structural_invariants(edge)


def test_structural_moderates_requires_moderates_edge() -> None:
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.MODERATES,
        confidence=0.5,
        citation="PMID:1",
    )
    with pytest.raises(CausalEdgeError, match="moderates_edge"):
        validate_structural_invariants(edge)


def test_structural_causes_has_no_extra_required_fields() -> None:
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.CAUSES,
        confidence=0.5,
        citation="PMID:1",
    )
    validate_structural_invariants(edge)  # should not raise


def test_structural_inhibits_has_no_extra_required_fields() -> None:
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.INHIBITS,
        confidence=0.5,
        citation="PMID:1",
    )
    validate_structural_invariants(edge)  # should not raise


# ---------------------------------------------------------------------------
# Invariant 5 — MEDIATES segment edges must exist
# ---------------------------------------------------------------------------
def test_mediates_invariant_pass_when_both_segments_exist() -> None:
    edge = CausalEdge(
        source_id="X",
        target_id="Y",
        edge_type=CausalEdgeType.MEDIATES,
        confidence=0.7,
        citation="PMID:1",
        via_node="M",
    )
    existing = {("X", "M", "CAUSES"), ("M", "Y", "CAUSES")}
    lookup = lambda s, t, e: (s, t, e) in existing  # noqa: E731
    validate_mediates_invariant(edge, lookup)  # no raise


def test_mediates_invariant_fail_when_first_segment_missing() -> None:
    edge = CausalEdge(
        source_id="X",
        target_id="Y",
        edge_type=CausalEdgeType.MEDIATES,
        confidence=0.7,
        citation="PMID:1",
        via_node="M",
    )
    existing = {("M", "Y", "CAUSES")}  # missing X-->M
    lookup = lambda s, t, e: (s, t, e) in existing  # noqa: E731
    with pytest.raises(CausalEdgeError, match="CAUSES"):
        validate_mediates_invariant(edge, lookup)


def test_mediates_invariant_skipped_for_other_types() -> None:
    edge = CausalEdge(
        source_id="X",
        target_id="Y",
        edge_type=CausalEdgeType.CAUSES,
        confidence=0.7,
        citation="PMID:1",
    )
    lookup = lambda *_: False  # noqa: E731 — should never be called
    validate_mediates_invariant(edge, lookup)  # no raise


# ---------------------------------------------------------------------------
# Invariant 6 — CONFOUNDS also_confounds nodes must exist
# ---------------------------------------------------------------------------
def test_confounds_invariant_pass_when_all_nodes_exist() -> None:
    edge = CausalEdge(
        source_id="A",
        target_id="B",
        edge_type=CausalEdgeType.CONFOUNDS,
        confidence=0.6,
        citation="PMID:1",
        also_confounds=["C", "D"],
    )
    node_exists = {"A", "B", "C", "D"}
    lookup = lambda n: n in node_exists  # noqa: E731
    validate_confounds_invariant(edge, lookup)  # no raise


def test_confounds_invariant_fail_when_node_missing() -> None:
    edge = CausalEdge(
        source_id="A",
        target_id="B",
        edge_type=CausalEdgeType.CONFOUNDS,
        confidence=0.6,
        citation="PMID:1",
        also_confounds=["C", "MISSING"],
    )
    node_exists = {"A", "B", "C"}
    lookup = lambda n: n in node_exists  # noqa: E731
    with pytest.raises(CausalEdgeError, match="MISSING"):
        validate_confounds_invariant(edge, lookup)


# ---------------------------------------------------------------------------
# Invariant 7a — MODERATES hash format + reference existence
# ---------------------------------------------------------------------------
def test_moderates_hash_must_be_16_chars() -> None:
    with pytest.raises(Exception, match="16-char hex"):
        CausalEdge(
            source_id=1,
            target_id=2,
            edge_type=CausalEdgeType.MODERATES,
            confidence=0.5,
            citation="PMID:1",
            moderates_edge="abc",  # wrong length
        )


def test_moderates_hash_must_be_hex() -> None:
    with pytest.raises(Exception, match="hex"):
        CausalEdge(
            source_id=1,
            target_id=2,
            edge_type=CausalEdgeType.MODERATES,
            confidence=0.5,
            citation="PMID:1",
            moderates_edge="ZZZZZZZZZZZZZZZZ",  # 16 chars but not hex
        )


def test_moderates_invariant_fail_when_hash_not_found() -> None:
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.MODERATES,
        confidence=0.5,
        citation="PMID:1",
        moderates_edge="0123456789abcdef",
    )
    lookup = lambda h: False  # noqa: E731
    with pytest.raises(CausalEdgeError, match="moderates_edge"):
        validate_moderates_invariant(edge, lookup)


def test_moderates_invariant_pass_when_hash_found() -> None:
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.MODERATES,
        confidence=0.5,
        citation="PMID:1",
        moderates_edge="0123456789abcdef",
    )
    lookup = lambda h: h == "0123456789abcdef"  # noqa: E731
    validate_moderates_invariant(edge, lookup)  # no raise


def test_compute_edge_hash_is_deterministic() -> None:
    h1 = compute_edge_hash("X", "Y", "CAUSES")
    h2 = compute_edge_hash("X", "Y", "CAUSES")
    assert h1 == h2
    assert len(h1) == MODERATES_EDGE_HASH_LEN
    assert all(c in "0123456789abcdef" for c in h1)


def test_compute_edge_hash_distinct_for_different_inputs() -> None:
    assert compute_edge_hash("X", "Y", "CAUSES") != compute_edge_hash(
        "X", "Y", "INHIBITS"
    )
    assert compute_edge_hash("X", "Y", "CAUSES") != compute_edge_hash(
        "Y", "X", "CAUSES"
    )


# ---------------------------------------------------------------------------
# Invariant 7b — post-write DAG invariant
# ---------------------------------------------------------------------------
def test_dag_invariant_accepts_acyclic_graph() -> None:
    edges = [
        ("A", "B", "CAUSES"),
        ("B", "C", "CAUSES"),
        ("A", "C", "INHIBITS"),
    ]
    validate_dag_invariant(edges)  # no raise


def test_dag_invariant_rejects_cycle() -> None:
    """A -> B -> C -> A is a 3-cycle; must raise."""
    edges = [
        ("A", "B", "CAUSES"),
        ("B", "C", "CAUSES"),
        ("C", "A", "CAUSES"),
    ]
    with pytest.raises(CausalEdgeError, match="cycle"):
        validate_dag_invariant(edges)


def test_dag_invariant_ignores_confounds_and_moderates_edges() -> None:
    """CONFOUNDS + MODERATES are meta-edges; they must not break DAG-ness."""
    edges = [
        ("A", "B", "CAUSES"),
        # These two would form A-B-A cycle if CONFOUNDS counted in the DAG.
        ("B", "A", "CONFOUNDS"),
        ("A", "B", "MODERATES"),
    ]
    validate_dag_invariant(edges)  # no raise


def test_dag_participating_types_constant_is_correct() -> None:
    assert DAG_PARTICIPATING_TYPES == {"CAUSES", "INHIBITS", "MEDIATES"}


# ---------------------------------------------------------------------------
# Composite validator end-to-end
# ---------------------------------------------------------------------------
def test_validate_edge_for_write_happy_path_no_lookups() -> None:
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.CAUSES,
        confidence=0.5,
        citation="PMID:1",
    )
    # No lookups passed → only structural check runs; should pass.
    validate_edge_for_write(edge)


def test_validate_edge_for_write_catches_proposed_cycle() -> None:
    """A new CAUSES edge that would close a cycle must be rejected."""
    edge = CausalEdge(
        source_id="C",
        target_id="A",
        edge_type=CausalEdgeType.CAUSES,
        confidence=0.5,
        citation="PMID:1",
    )
    existing_dag = [("A", "B", "CAUSES"), ("B", "C", "CAUSES")]
    with pytest.raises(CausalEdgeError, match="cycle"):
        validate_edge_for_write(edge, all_edges_for_dag_check=existing_dag)


def test_validate_edge_for_write_runs_structural_first() -> None:
    """MEDIATES without via_node fails on invariant 4 before reaching invariant 5."""
    edge = CausalEdge(
        source_id=1,
        target_id=2,
        edge_type=CausalEdgeType.MEDIATES,
        confidence=0.5,
        citation="PMID:1",
    )
    with pytest.raises(CausalEdgeError, match="via_node"):
        validate_edge_for_write(
            edge,
            existing_edges_lookup=lambda *_: True,  # would otherwise pass
        )


# ---------------------------------------------------------------------------
# CITATION_REGEX exposed for reuse
# ---------------------------------------------------------------------------
def test_citation_regex_export_matches_pmid() -> None:
    assert CITATION_REGEX.match("PMID:1") is not None
    assert CITATION_REGEX.match("garbage") is None
