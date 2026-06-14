"""tests/test_backup_to_r2.py — OPS-5 scheduled backup orchestration (offline).

No pg_dump, no neo4j, no R2: subprocess.run, export_graph, and upload_artifact are
all mocked. Asserts timestamped source_ids, exit 0 when >=1 source uploads, exit 2
when nothing is configured, and that an unreachable source is skipped (not fatal)
while the other still uploads.
"""

from __future__ import annotations

import re
import types

import scripts.backup_to_r2 as btr


def _fake_completed(returncode=0, stdout=b"-- pg_dump SQL\n"):
    return types.SimpleNamespace(returncode=returncode, stdout=stdout, stderr=b"")


def _wire_happy(monkeypatch):
    """Both sources configured + their transports mocked. Returns the upload recorder."""
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://u:p@h:5432/db")
    monkeypatch.setenv("NEO4J_URI", "neo4j+s://abc.databases.neo4j.io")
    monkeypatch.setenv("NEO4J_PASSWORD", "secret")
    monkeypatch.setattr(btr.subprocess, "run", lambda *a, **k: _fake_completed())
    monkeypatch.setattr(
        btr, "export_graph", lambda driver: {"nodes": [], "relationships": []}
    )
    # _dump_neo4j still does `from neo4j import GraphDatabase`; stub the driver factory
    monkeypatch.setattr(
        "neo4j.GraphDatabase.driver",
        lambda *a, **k: types.SimpleNamespace(close=lambda: None),
    )
    calls = []

    def _fake_upload(source_type, source_id, payload, ext, **kw):
        calls.append((source_type, source_id, ext, len(payload)))
        return f"s3://bucket/{source_type}/{source_id}.{ext}"

    monkeypatch.setattr(btr, "upload_artifact", _fake_upload)
    monkeypatch.setattr(btr, "load_env", lambda: None)
    return calls


def test_both_sources_upload_exit_zero(monkeypatch):
    calls = _wire_happy(monkeypatch)
    rc = btr.run()
    assert rc == 0
    assert len(calls) == 2
    source_ids = {c[1] for c in calls}
    assert any(re.match(r"^neo4j_\d", sid) for sid in source_ids)
    assert any(sid.startswith("supabase_") for sid in source_ids)
    # timestamped -> the two ids are distinct from any fixed name (no clobber)
    assert all("_" in sid for sid in source_ids)


def test_no_creds_exit_two(monkeypatch):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    monkeypatch.setattr(btr, "load_env", lambda: None)
    called = []
    monkeypatch.setattr(btr, "upload_artifact", lambda *a, **k: called.append(a))
    rc = btr.run()
    assert rc == 2
    assert called == []  # nothing uploaded when no source is configured


def test_one_source_down_other_still_uploads(monkeypatch):
    # supabase configured + pg_dump fails; neo4j configured + ok -> still exit 0.
    calls = _wire_happy(monkeypatch)
    monkeypatch.setattr(
        btr.subprocess, "run", lambda *a, **k: _fake_completed(returncode=1, stdout=b"")
    )
    rc = btr.run()
    assert rc == 0
    assert {c[1].split("_")[0] for c in calls} == {"neo4j"}  # only neo4j uploaded


def test_dry_run_skips_upload(monkeypatch):
    calls = _wire_happy(monkeypatch)
    rc = btr.run(dry_run=True)
    assert rc == 0
    assert calls == []  # dry-run dumps + sizes but never uploads


def test_source_ids_are_unique_per_run(monkeypatch):
    calls = _wire_happy(monkeypatch)
    btr.run()
    ids = [c[1] for c in calls]
    assert len(ids) == len(set(ids))
