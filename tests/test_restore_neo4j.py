"""tests/test_restore_neo4j.py — OPS-5 restore round-trip parser (offline).

load_snapshot + _build_statements are pure (no neo4j import, no DB), so the whole
parse/plan path is exercised here with a tiny 2-node/1-rel fixture. restore(dry_run=
True) is asserted to plan WITHOUT importing the driver or needing NEO4J_* creds.
The destructive (live) branch is not exercised — there is no database in CI.
"""

from __future__ import annotations

import json

import pytest

import scripts.restore_neo4j as rn

_SNAPSHOT = {
    "nodes": [
        {"internal_id": 1, "labels": ["Paper"], "properties": {"pmid": "12345678"}},
        {"internal_id": 2, "labels": ["Therapy"], "properties": {"name": "cord blood"}},
    ],
    "relationships": [
        {
            "internal_id": 9,
            "source_internal_id": 1,
            "target_internal_id": 2,
            "type": "SUPPORTS",
            "properties": {"confidence": 0.8},
        }
    ],
}


def _write(tmp_path, obj) -> str:
    p = tmp_path / "snap.json"
    p.write_text(json.dumps(obj), encoding="utf-8")
    return str(p)


def test_load_snapshot_roundtrips(tmp_path):
    data = rn.load_snapshot(_write(tmp_path, _SNAPSHOT))
    assert len(data["nodes"]) == 2
    assert len(data["relationships"]) == 1


def test_build_statements_shape_and_params():
    stmts = rn._build_statements(_SNAPSHOT)
    # 2 node CREATEs + 1 rel + 1 cleanup, no wipe
    assert len(stmts) == 4
    node_cyphers = [c for c, _ in stmts if c.startswith("CREATE (n")]
    assert any(":Paper" in c for c in node_cyphers)
    assert any(":Therapy" in c for c in node_cyphers)
    # node params carry the original internal id under _restore_id
    rids = {p["rid"] for c, p in stmts if "rid" in p}
    assert rids == {1, 2}
    # relationship is matched by _restore_id and typed
    rel = next(c for c, _ in stmts if "[rel:SUPPORTS]" in c)
    assert "_restore_id" in rel
    # final statement strips the temp key
    assert "REMOVE n._restore_id" in stmts[-1][0]


def test_build_statements_wipe_prepends_detach_delete():
    stmts = rn._build_statements(_SNAPSHOT, wipe=True)
    assert stmts[0][0] == "MATCH (n) DETACH DELETE n"
    assert len(stmts) == 5  # wipe + 2 nodes + 1 rel + cleanup


def test_node_without_labels_is_allowed():
    snap = {"nodes": [{"internal_id": 7, "properties": {}}], "relationships": []}
    stmts = rn._build_statements(snap)
    assert stmts[0][0].startswith("CREATE (n) SET")  # no :Label segment


def test_custom_nonce_key_used_everywhere():
    key = "_restore_id_deadbeef"
    stmts = rn._build_statements(_SNAPSHOT, key=key)
    assert any(f"n.{key} = $rid" in c for c, _ in stmts)  # node wiring
    assert any(f"{{{key}: $sid}}" in c for c, _ in stmts)  # rel MATCH
    assert stmts[-1][0] == f"MATCH (n) WHERE n.{key} IS NOT NULL REMOVE n.{key}"
    # default key must not leak when a nonce is supplied
    assert not any("n._restore_id =" in c for c, _ in stmts)


def test_wiring_key_set_after_props_cannot_be_clobbered():
    # the wiring assignment must come AFTER `+= $props` in the node CREATE
    stmts = rn._build_statements(_SNAPSHOT)
    node = next(c for c, _ in stmts if c.startswith("CREATE (n"))
    assert node.index("SET n += $props") < node.index("n._restore_id = $rid")


def test_unsafe_wiring_key_rejected():
    with pytest.raises(ValueError, match="unsafe wiring key"):
        rn._build_statements(_SNAPSHOT, key="bad key) DELETE n")


def test_unsafe_label_rejected():
    bad = {
        "nodes": [{"internal_id": 1, "labels": ["Paper) DETACH DELETE (n"]}],
        "relationships": [],
    }
    with pytest.raises(ValueError, match="unsafe node label"):
        rn._build_statements(bad)


def test_unsafe_rel_type_rejected():
    bad = {
        "nodes": [
            {"internal_id": 1, "labels": ["A"]},
            {"internal_id": 2, "labels": ["B"]},
        ],
        "relationships": [
            {"source_internal_id": 1, "target_internal_id": 2, "type": "X]->() DELETE"}
        ],
    }
    with pytest.raises(ValueError, match="unsafe relationship type"):
        rn._build_statements(bad)


@pytest.mark.parametrize(
    "obj, match",
    [
        ([], "must be a JSON object"),  # root not a dict
        ({"nodes": [], "relationships": "x"}, "must contain"),
        ({"nodes": [{"labels": ["A"]}], "relationships": []}, "internal_id"),
        (
            {
                "nodes": [],
                "relationships": [{"source_internal_id": 1, "target_internal_id": 2}],
            },
            "type",
        ),
    ],
)
def test_malformed_snapshot_raises(tmp_path, obj, match):
    with pytest.raises(ValueError, match=match):
        rn.load_snapshot(_write(tmp_path, obj))


def test_load_snapshot_rejects_duplicate_internal_ids(tmp_path):
    dup = {
        "nodes": [
            {"internal_id": 5, "labels": ["A"]},
            {"internal_id": 5, "labels": ["B"]},
        ],
        "relationships": [],
    }
    with pytest.raises(ValueError, match="duplicate node internal_id"):
        rn.load_snapshot(_write(tmp_path, dup))


def test_load_snapshot_rejects_dangling_relationship(tmp_path):
    dangling = {
        "nodes": [{"internal_id": 1, "labels": ["A"]}],
        "relationships": [
            {"source_internal_id": 1, "target_internal_id": 99, "type": "REL"}
        ],
    }
    with pytest.raises(ValueError, match="unknown node internal_id"):
        rn.load_snapshot(_write(tmp_path, dangling))


def test_restore_dry_run_plans_without_driver(tmp_path, monkeypatch):
    # No NEO4J_* env, and any accidental driver import would fail the test.
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    summary = rn.restore(_write(tmp_path, _SNAPSHOT), dry_run=True)
    assert summary["dry_run"] is True
    assert summary["applied"] is False
    assert summary["nodes"] == 2
    assert summary["relationships"] == 1
    assert summary["statements"] == 4


def test_restore_missing_env_raises_not_exits(tmp_path, monkeypatch):
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="NEO4J_URI and NEO4J_PASSWORD"):
        rn.restore(_write(tmp_path, _SNAPSHOT), dry_run=False)


def test_main_dry_run_exit_zero(tmp_path, capsys):
    rc = rn.main([_write(tmp_path, _SNAPSHOT), "--dry-run"])
    assert rc == 0
    assert "dry-run" in capsys.readouterr().out
