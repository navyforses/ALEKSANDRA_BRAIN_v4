"""Phase 7.1 Days 8-9 — Causal edge taxonomy enforcement (application layer).

Wraps every causal-edge write with the 7 invariants from
docs/PHASE_7_1_TAXONOMY.md + 5 carry-forwards from Day 4-7.

This module is the single trust boundary for the Pearl 5-type SCM contract.
brain/memory/causal_adapter.py is the only thing allowed to bypass it
(adapter still calls into THESE validators before writing to Neo4j).

Enforcement happens at WRITE TIME (pre-flight before cypher), not just read time.

Invariants enforced (cf. docs/PHASE_7_1_TAXONOMY.md §7):
    1. Edge type ∈ {CAUSES, INHIBITS, MEDIATES, CONFOUNDS, MODERATES}
    2. confidence ∈ [0.0, 1.0]
    3. citation matches ^(PMID:\\d+|DOI:.+|https?://.+|TBD-Day-7-backfill)$
    4. MEDIATES edge requires via_node + both segment CAUSES edges
    5. CONFOUNDS edge requires non-empty also_confounds + every node exists
    6. MODERATES edge requires moderates_edge (16-hex sha256[:16]) + ref exists
    7. Post-write DAG invariant on CAUSES + INHIBITS + MEDIATES (NetworkX)

Carry-forwards from Day 4-7 (preserved verbatim):
    - confidence range check happens here (Neo4j cannot)
    - 'TBD-Day-7-backfill' is an accepted-but-incomplete citation placeholder
    - legacy_type / classified_by / classified_rationale audit fields preserved
    - classified_rationale capped at 200 chars
    - MEDIATES/CONFOUNDS/MODERATES never auto-produced by Day 6 — manual triage
"""

from __future__ import annotations

import hashlib
import re
from enum import Enum
from typing import Any, Callable, Optional

import networkx as nx
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Type system
# ---------------------------------------------------------------------------
class CausalEdgeType(str, Enum):
    """5-type Pearl SCM taxonomy from docs/PHASE_7_1_TAXONOMY.md."""

    CAUSES = "CAUSES"
    INHIBITS = "INHIBITS"
    MEDIATES = "MEDIATES"
    CONFOUNDS = "CONFOUNDS"
    MODERATES = "MODERATES"


# Accepted formats: PMID:12345, DOI:10.1234/foo, http(s)://..., or TBD placeholder.
CITATION_REGEX = re.compile(
    r"^(PMID:\d+|DOI:.+|https?://.+|TBD-Day-7-backfill)$", re.IGNORECASE
)
TBD_PLACEHOLDER = "TBD-Day-7-backfill"
MAX_RATIONALE_LEN = 200
MODERATES_EDGE_HASH_LEN = 16

# Edges that participate in the do-calculus DAG. CONFOUNDS + MODERATES are
# meta-edges (latent-common-cause + effect-modifier) and intentionally excluded.
DAG_PARTICIPATING_TYPES = frozenset({"CAUSES", "INHIBITS", "MEDIATES"})


class CausalEdgeError(ValueError):
    """Raised when an edge violates the taxonomy contract."""


class CausalEdge(BaseModel):
    """One edge write spec, validated against all 7 invariants before persisting.

    Pydantic field validators handle invariants 1-3 + the type-specific field
    sanity checks (hash format on moderates_edge, rationale cap).

    Composite cross-edge invariants (4-7) require live DB lookups and are
    delegated to validate_edge_for_write().
    """

    model_config = ConfigDict(extra="forbid", use_enum_values=False)

    source_id: str | int
    target_id: str | int
    edge_type: CausalEdgeType
    confidence: float = Field(..., ge=0.0, le=1.0)
    citation: str = Field(..., min_length=1)
    mechanism: Optional[str] = None
    time_lag_days: Optional[int] = None
    # Type-specific fields (None unless edge_type requires)
    via_node: Optional[str | int] = None  # required for MEDIATES
    also_confounds: Optional[list[str | int]] = None  # required for CONFOUNDS
    moderates_edge: Optional[str] = None  # required for MODERATES (sha256[:16])
    # Audit (Phase 7.1 Day-6 carry-forward)
    classified_by: Optional[str] = None
    classified_rationale: Optional[str] = None
    legacy_type: Optional[str] = None

    @field_validator("citation")
    @classmethod
    def _validate_citation(cls, v: str) -> str:
        if not CITATION_REGEX.match(v):
            raise CausalEdgeError(
                f"citation must match {CITATION_REGEX.pattern}, got {v!r}"
            )
        return v

    @field_validator("classified_rationale")
    @classmethod
    def _cap_rationale(cls, v: Optional[str]) -> Optional[str]:
        # Day-6 carry-forward: silently truncate to 200 chars to mirror
        # scripts/refactor/classify_edges.py apply_classification behaviour.
        if v is not None and len(v) > MAX_RATIONALE_LEN:
            return v[:MAX_RATIONALE_LEN]
        return v

    @field_validator("moderates_edge")
    @classmethod
    def _validate_moderates_hash(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if len(v) != MODERATES_EDGE_HASH_LEN:
                raise CausalEdgeError(
                    f"moderates_edge must be {MODERATES_EDGE_HASH_LEN}-char hex, "
                    f"got len={len(v)}"
                )
            if not re.match(r"^[0-9a-f]+$", v.lower()):
                raise CausalEdgeError(f"moderates_edge must be hex, got {v!r}")
        return v


def compute_edge_hash(
    source_id: str | int, target_id: str | int, edge_type: str
) -> str:
    """Deterministic edge identifier — used as MODERATES.moderates_edge ref."""
    payload = f"{source_id}|{target_id}|{edge_type}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[
        :MODERATES_EDGE_HASH_LEN
    ]


def is_citation_complete(citation: str) -> bool:
    """True if citation is a real PMID/DOI/URL (NOT the TBD placeholder).

    Phase 7.2 estimands must filter on this — TBD-Day-7-backfill edges
    do not count as having provenance and are excluded from identify_effect().
    """
    return citation != TBD_PLACEHOLDER


# ---------------------------------------------------------------------------
# Per-type structural validation
# ---------------------------------------------------------------------------
def validate_structural_invariants(edge: CausalEdge) -> None:
    """Check type-specific required fields. Raises CausalEdgeError on violation."""
    t = edge.edge_type
    if t == CausalEdgeType.MEDIATES:
        if not edge.via_node:
            raise CausalEdgeError("MEDIATES edge requires via_node")
    elif t == CausalEdgeType.CONFOUNDS:
        if not edge.also_confounds:
            raise CausalEdgeError(
                "CONFOUNDS edge requires also_confounds (non-empty list)"
            )
    elif t == CausalEdgeType.MODERATES:
        if not edge.moderates_edge:
            raise CausalEdgeError(
                "MODERATES edge requires moderates_edge (sha256[:16])"
            )
    # CAUSES + INHIBITS have no extra required fields beyond the base 4 + audit


def validate_mediates_invariant(
    edge: CausalEdge,
    existing_edges_lookup: Callable[[Any, Any, str], bool],
) -> None:
    """For a MEDIATES X->Y edge with via_node=M, the two segment edges
    (X-[CAUSES]->M) + (M-[CAUSES]->Y) MUST already exist.

    Args:
        edge: the MEDIATES edge being written
        existing_edges_lookup: callable(source, target, type) -> bool
    """
    if edge.edge_type != CausalEdgeType.MEDIATES:
        return
    if not existing_edges_lookup(edge.source_id, edge.via_node, "CAUSES"):
        raise CausalEdgeError(
            f"MEDIATES invariant: missing segment "
            f"({edge.source_id})-[CAUSES]->({edge.via_node})"
        )
    if not existing_edges_lookup(edge.via_node, edge.target_id, "CAUSES"):
        raise CausalEdgeError(
            f"MEDIATES invariant: missing segment "
            f"({edge.via_node})-[CAUSES]->({edge.target_id})"
        )


def validate_confounds_invariant(
    edge: CausalEdge,
    node_exists_lookup: Callable[[Any], bool],
) -> None:
    """All node ids listed in also_confounds must exist."""
    if edge.edge_type != CausalEdgeType.CONFOUNDS:
        return
    missing = [
        n for n in (edge.also_confounds or []) if not node_exists_lookup(n)
    ]
    if missing:
        raise CausalEdgeError(
            f"CONFOUNDS invariant: also_confounds nodes don't exist: {missing}"
        )


def validate_moderates_invariant(
    edge: CausalEdge,
    edge_exists_by_hash_lookup: Callable[[str], bool],
) -> None:
    """The moderates_edge hash must reference an existing edge."""
    if edge.edge_type != CausalEdgeType.MODERATES:
        return
    if not edge_exists_by_hash_lookup(edge.moderates_edge):
        raise CausalEdgeError(
            f"MODERATES invariant: moderates_edge {edge.moderates_edge!r} "
            f"not found"
        )


# ---------------------------------------------------------------------------
# DAG invariant (post-write check)
# ---------------------------------------------------------------------------
def validate_dag_invariant(all_edges: list[tuple[Any, Any, str]]) -> None:
    """Build a NetworkX DiGraph from all CAUSES/INHIBITS/MEDIATES edges and
    confirm it stays acyclic. CONFOUNDS + MODERATES are meta-edges and don't
    participate in the DAG.

    Args:
        all_edges: list of (source_id, target_id, edge_type) tuples
    """
    graph = nx.DiGraph()
    for src, tgt, t in all_edges:
        if t in DAG_PARTICIPATING_TYPES:
            graph.add_edge(src, tgt)
    if not nx.is_directed_acyclic_graph(graph):
        cycles = list(nx.simple_cycles(graph))
        first_cycle = cycles[0] if cycles else "<unknown>"
        raise CausalEdgeError(
            f"DAG invariant violated: cycle found {first_cycle!r}. "
            f"Total cycles detected: {len(cycles)}."
        )


# ---------------------------------------------------------------------------
# Composite pre-write validator
# ---------------------------------------------------------------------------
def validate_edge_for_write(
    edge: CausalEdge,
    *,
    existing_edges_lookup: Optional[Callable[[Any, Any, str], bool]] = None,
    node_exists_lookup: Optional[Callable[[Any], bool]] = None,
    edge_exists_by_hash_lookup: Optional[Callable[[str], bool]] = None,
    all_edges_for_dag_check: Optional[list[tuple[Any, Any, str]]] = None,
) -> None:
    """One-call pre-flight before writing edge to Neo4j.

    Runs all 7 invariants in order; raises CausalEdgeError on first violation.
    Lookups default to no-op callables for tests that don't need full graph state.

    Invariant coverage:
        1-3. Enforced by Pydantic on edge construction (type / confidence / citation)
        4.   validate_structural_invariants (per-type required fields)
        5.   validate_mediates_invariant (requires existing_edges_lookup)
        6.   validate_confounds_invariant (requires node_exists_lookup)
        7a.  validate_moderates_invariant (requires edge_exists_by_hash_lookup)
        7b.  validate_dag_invariant (requires all_edges_for_dag_check)
    """
    # 1-3 already enforced by Pydantic on edge construction
    # 4. Structural type-specific fields
    validate_structural_invariants(edge)
    # 5. MEDIATES segment existence
    if existing_edges_lookup is not None:
        validate_mediates_invariant(edge, existing_edges_lookup)
    # 6. CONFOUNDS node existence
    if node_exists_lookup is not None:
        validate_confounds_invariant(edge, node_exists_lookup)
    # 7a. MODERATES edge-hash existence
    if edge_exists_by_hash_lookup is not None:
        validate_moderates_invariant(edge, edge_exists_by_hash_lookup)
    # 7b. DAG check (post-write simulation)
    if all_edges_for_dag_check is not None:
        proposed = list(all_edges_for_dag_check) + [
            (edge.source_id, edge.target_id, edge.edge_type.value)
        ]
        validate_dag_invariant(proposed)


__all__ = [
    "CausalEdge",
    "CausalEdgeError",
    "CausalEdgeType",
    "CITATION_REGEX",
    "DAG_PARTICIPATING_TYPES",
    "MAX_RATIONALE_LEN",
    "MODERATES_EDGE_HASH_LEN",
    "TBD_PLACEHOLDER",
    "compute_edge_hash",
    "is_citation_complete",
    "validate_confounds_invariant",
    "validate_dag_invariant",
    "validate_edge_for_write",
    "validate_mediates_invariant",
    "validate_moderates_invariant",
    "validate_structural_invariants",
]
