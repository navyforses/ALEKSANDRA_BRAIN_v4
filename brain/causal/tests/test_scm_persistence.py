"""Phase 7.2 Days 12-14 — tests for scm_persistence.py.

All tests run in DRY_RUN mode (SUPABASE_DB_URL unset) so they require
no live Postgres. The Day 15 verifier exercises the same code paths
against a live Supabase in --mode production.
"""

from __future__ import annotations

import os

import networkx as nx
import pytest
from pydantic import ValidationError

from brain.causal.scm import build_reference_scm
from brain.causal.scm_persistence import (
    SCMAuditEntry,
    SCMRecord,
    compute_diff,
    create_scm,
    delete_scm,
    get_scm,
    graph_json_to_scm,
    list_scm_audit,
    list_scms,
    revert_scm,
    scm_to_graph_json,
    update_scm,
)


# ---------------------------------------------------------------------------
# Fixture: ensure DRY_RUN by clearing SUPABASE_DB_URL for the duration
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _force_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)


# ---------------------------------------------------------------------------
# Round-trip + diff tests
# ---------------------------------------------------------------------------
def test_round_trip_preserves_reference_scm_edges_and_attrs() -> None:
    """SCM -> graph_json -> SCM preserves 6 reference edges + citations."""
    scm = build_reference_scm()
    payload = scm_to_graph_json(scm)
    rebuilt = graph_json_to_scm(payload)
    assert rebuilt.name == scm.name
    assert rebuilt.treatment == scm.treatment
    assert rebuilt.outcome == scm.outcome
    assert rebuilt.graph is not None
    assert rebuilt.graph.number_of_nodes() == 5
    assert rebuilt.graph.number_of_edges() == 6
    # Verify edge attributes survived
    edge_attrs_preserved = 0
    for _, _, data in rebuilt.graph.edges(data=True):
        if "citation" in data and data["citation"].startswith("PMID:"):
            edge_attrs_preserved += 1
    assert edge_attrs_preserved == 6, (
        f"expected 6 PMID citations preserved, got {edge_attrs_preserved}"
    )


def test_round_trip_preserves_node_names() -> None:
    """Reference SCM node 'name' attributes survive serialise/deserialise."""
    scm = build_reference_scm()
    rebuilt = graph_json_to_scm(scm_to_graph_json(scm))
    names = {
        rebuilt.graph.nodes[n].get("name") for n in rebuilt.graph.nodes()
    }
    assert "Vigabatrin" in names
    assert "Seizure frequency" in names
    assert "Age (months)" in names
    assert "GABA-T enzyme" in names
    assert "Neuroplasticity window" in names


def test_compute_diff_identical_graphs_empty() -> None:
    """Diff of identical graph_json payloads is all-empty lists."""
    scm = build_reference_scm()
    payload = scm_to_graph_json(scm)
    diff = compute_diff(payload, payload)
    assert diff["added_edges"] == []
    assert diff["removed_edges"] == []
    assert diff["added_nodes"] == []
    assert diff["removed_nodes"] == []


def test_compute_diff_one_edge_removed() -> None:
    """Removing one edge surfaces as a single removed_edges entry."""
    scm = build_reference_scm()
    payload_before = scm_to_graph_json(scm)
    # Remove one edge (1 -> 4 INHIBITS in reference SCM)
    g2 = scm.graph.copy()
    g2.remove_edge(1, 4)
    scm2 = scm.model_copy(update={"graph": g2})
    payload_after = scm_to_graph_json(scm2)
    diff = compute_diff(payload_before, payload_after)
    assert len(diff["removed_edges"]) == 1
    assert ("1", "4") in diff["removed_edges"]
    assert diff["added_edges"] == []


# ---------------------------------------------------------------------------
# DRY_RUN CRUD sentinels
# ---------------------------------------------------------------------------
def test_create_scm_dry_run_returns_sentinel() -> None:
    """create_scm returns DRY_RUN:<hash> when SUPABASE_DB_URL unset."""
    scm = build_reference_scm()
    out = create_scm(scm, actor="test_actor")
    assert isinstance(out, str)
    assert out.startswith("DRY_RUN:")
    assert len(out) > len("DRY_RUN:") + 32  # SHA-256 hex = 64 chars


def test_create_scm_requires_actor() -> None:
    """Empty actor raises ValueError (audit-lineage hard rule)."""
    scm = build_reference_scm()
    with pytest.raises(ValueError, match="actor"):
        create_scm(scm, actor="")
    with pytest.raises(ValueError, match="actor"):
        create_scm(scm, actor="   ")


def test_update_scm_dry_run_returns_sentinel() -> None:
    scm = build_reference_scm()
    out = update_scm("reference_vigabatrin_seizure", scm, actor="test_actor")
    assert isinstance(out, str)
    assert out.startswith("DRY_RUN:")


def test_revert_scm_dry_run_returns_sentinel() -> None:
    out = revert_scm(
        "reference_vigabatrin_seizure", target_version=1, actor="test_actor"
    )
    assert isinstance(out, str)
    assert out.startswith("DRY_RUN:")


def test_revert_scm_rejects_zero_version() -> None:
    """target_version must be >= 1 (matches schema CHECK constraint)."""
    with pytest.raises(ValueError, match="target_version"):
        revert_scm("any_name", target_version=0, actor="test_actor")


def test_delete_scm_dry_run_returns_one() -> None:
    """Soft-delete returns 1 in DRY_RUN (tombstone would-be-row count)."""
    count = delete_scm(
        "reference_vigabatrin_seizure", actor="test_actor", soft=True
    )
    assert count == 1


def test_delete_scm_hard_delete_not_implemented() -> None:
    """soft=False raises NotImplementedError (immutable-history guard)."""
    with pytest.raises(NotImplementedError):
        delete_scm("any_name", actor="test_actor", soft=False)


def test_list_scms_dry_run_returns_empty_list() -> None:
    assert list_scms() == []


def test_list_scm_audit_dry_run_returns_empty_list() -> None:
    assert list_scm_audit("reference_vigabatrin_seizure") == []


def test_get_scm_dry_run_returns_none() -> None:
    assert get_scm("reference_vigabatrin_seizure") is None
    assert get_scm("any_name", version=2) is None


# ---------------------------------------------------------------------------
# Pydantic validation
# ---------------------------------------------------------------------------
def test_scm_record_pydantic_rejects_extra() -> None:
    """SCMRecord rejects unknown fields (extra='forbid')."""
    with pytest.raises(ValidationError):
        SCMRecord(
            name="x",
            version=1,
            graph_json={},
            created_by="me",
            unknown="nope",  # type: ignore[call-arg]
        )


def test_scm_record_version_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        SCMRecord(name="x", version=0, graph_json={}, created_by="me")


def test_scm_audit_entry_pydantic_rejects_unknown_operation() -> None:
    """Operation must be one of the 4 allowed verbs."""
    with pytest.raises(ValidationError):
        SCMAuditEntry(
            operation="purge",  # type: ignore[arg-type]
            diff={},
            actor="me",
        )


def test_scm_audit_entry_accepts_all_valid_operations() -> None:
    for op in ("create", "update", "delete", "revert"):
        entry = SCMAuditEntry(operation=op, diff={"k": "v"}, actor="me")
        assert entry.operation == op


# ---------------------------------------------------------------------------
# Day 14 — multi-SCM workspace
# ---------------------------------------------------------------------------
def test_multi_scm_workspace() -> None:
    """Three distinct named SCMs co-exist; each create_scm returns a distinct sentinel.

    DRY_RUN does not persist, so ``list_scms()`` returns empty.
    """
    reference = build_reference_scm()

    # Build two alternative-hypothesis SCMs by tweaking the reference name.
    alt1 = reference.model_copy(
        update={
            "name": "experimental_cord_blood_motor",
            "description": "Cord-blood motor-outcome hypothesis (Phase 7.2 test)",
        }
    )
    alt2 = reference.model_copy(
        update={
            "name": "placebo_baseline",
            "description": "Placebo-arm baseline SCM (Phase 7.2 test)",
        }
    )

    s1 = create_scm(reference, actor="test_actor")
    s2 = create_scm(alt1, actor="test_actor")
    s3 = create_scm(alt2, actor="test_actor")

    # All three sentinels are unique (payload differs by name + description)
    assert s1 != s2
    assert s2 != s3
    assert s1 != s3
    assert all(s.startswith("DRY_RUN:") for s in (s1, s2, s3))

    # DRY_RUN doesn't persist
    assert list_scms() == []


# ---------------------------------------------------------------------------
# Round-trip with attribute preservation for diff helpers
# ---------------------------------------------------------------------------
def test_graph_json_to_scm_rejects_missing_scm_spec() -> None:
    with pytest.raises(ValueError, match="scm_spec"):
        graph_json_to_scm({"nodes": [], "edges": []})


def test_compute_diff_node_added() -> None:
    """Adding one node + its incoming edge surfaces both in the diff."""
    scm = build_reference_scm()
    before = scm_to_graph_json(scm)
    g2 = scm.graph.copy()
    g2.add_node(99, name="Extra node")
    g2.add_edge(99, 2, edge_type="CAUSES", confidence=0.5, citation="PMID:1")
    scm2 = scm.model_copy(update={"graph": g2})
    after = scm_to_graph_json(scm2)
    diff = compute_diff(before, after)
    assert "99" in diff["added_nodes"]
    assert ("99", "2") in diff["added_edges"]
    assert diff["removed_nodes"] == []
    assert diff["removed_edges"] == []
