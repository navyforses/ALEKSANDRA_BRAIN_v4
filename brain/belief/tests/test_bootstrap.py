"""brain/belief/tests/test_bootstrap.py — Phase 7.0 closure-helper unit tests.

Scope:
  - Dry-run path never touches the DB and exits 0 when TOML is clean.
  - Dry-run fails (exit 1) when TOML has stub citations or wrong count.
  - _classify_change correctly distinguishes INSERT / UPDATE / UNCHANGED.
  - Full live-mode pipeline (with mocked persistence) exits 0 on clean run.
  - Single upsert failure is captured (FAIL count) and forces exit 1.
  - Post-write verification catches missing rows.

All DB calls are mocked at the bootstrap-module namespace — bootstrap.py
imports `list_dimensions`, `upsert_dimension` via `from ... import ...`, so
patches target `brain.belief.bootstrap.list_dimensions` etc.
"""

from __future__ import annotations

from unittest import mock

import pytest

from brain.belief.persistence import BeliefDimension


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _make_dim(
    name: str, *, citation: str = "PMID:99999999", **overrides
) -> BeliefDimension:
    """Build a valid BeliefDimension for tests."""
    base = dict(
        name=name,
        distribution="beta",
        prior_params={"alpha": 2.0, "beta": 5.0},
        units="percent",
        valid_min=0.0,
        valid_max=100.0,
        citation=citation,
    )
    base.update(overrides)
    return BeliefDimension(**base)


def _thirteen_clean_dims() -> list[BeliefDimension]:
    """Return 13 valid dimensions with non-stub citations."""
    return [_make_dim(f"dim_{i}") for i in range(13)]


@pytest.fixture
def clean_dims() -> list[BeliefDimension]:
    return _thirteen_clean_dims()


# ---------------------------------------------------------------------------
# _classify_change
# ---------------------------------------------------------------------------
def test_classify_change_insert_when_no_existing() -> None:
    from brain.belief.bootstrap import _classify_change

    new = _make_dim("foo")
    assert _classify_change(None, new) == "INSERT"


def test_classify_change_unchanged_when_identical() -> None:
    from brain.belief.bootstrap import _classify_change

    a = _make_dim("foo")
    b = _make_dim("foo")  # same fields
    assert _classify_change(a, b) == "UNCHANGED"


def test_classify_change_update_when_citation_differs() -> None:
    from brain.belief.bootstrap import _classify_change

    existing = _make_dim("foo", citation="PMID:111")
    new = _make_dim("foo", citation="PMID:222")
    assert _classify_change(existing, new) == "UPDATE"


def test_classify_change_update_when_prior_params_differ() -> None:
    from brain.belief.bootstrap import _classify_change

    existing = _make_dim("foo", prior_params={"alpha": 1.0, "beta": 1.0})
    new = _make_dim("foo", prior_params={"alpha": 2.0, "beta": 5.0})
    assert _classify_change(existing, new) == "UPDATE"


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------
def test_bootstrap_dry_run_does_not_touch_db(
    clean_dims: list[BeliefDimension],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dry-run must not call list_dimensions, upsert_dimension, or psycopg2 at all."""
    from brain.belief import bootstrap

    monkeypatch.setattr(bootstrap, "load_dimensions_from_toml", lambda: clean_dims)
    list_mock = mock.MagicMock()
    upsert_mock = mock.MagicMock()
    monkeypatch.setattr(bootstrap, "list_dimensions", list_mock)
    monkeypatch.setattr(bootstrap, "upsert_dimension", upsert_mock)
    monkeypatch.setattr("sys.argv", ["bootstrap", "--dry-run"])

    rc = bootstrap.main()

    assert rc == 0
    assert list_mock.call_count == 0
    assert upsert_mock.call_count == 0


def test_bootstrap_dry_run_exits_zero_on_clean_toml(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dry-run against the REAL dimensions.toml (which Day 6 ships clean) → exit 0."""
    from brain.belief import bootstrap

    monkeypatch.setattr("sys.argv", ["bootstrap", "--dry-run"])
    rc = bootstrap.main()
    assert rc == 0


def test_bootstrap_dry_run_exits_one_if_stubs_present(
    clean_dims: list[BeliefDimension],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Patch the loader to return a TBD-stub citation → exit 1."""
    from brain.belief import bootstrap

    stubbed = [
        _make_dim(
            f"dim_{i}", citation=("TBD-Day-7-librarian-A" if i == 0 else "PMID:99")
        )
        for i in range(13)
    ]
    monkeypatch.setattr(bootstrap, "load_dimensions_from_toml", lambda: stubbed)
    monkeypatch.setattr("sys.argv", ["bootstrap", "--dry-run"])

    rc = bootstrap.main()
    assert rc == 1


def test_bootstrap_dry_run_exits_one_if_count_not_13(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Patch loader to return 12 dims → exit 1."""
    from brain.belief import bootstrap

    twelve = [_make_dim(f"dim_{i}") for i in range(12)]
    monkeypatch.setattr(bootstrap, "load_dimensions_from_toml", lambda: twelve)
    monkeypatch.setattr("sys.argv", ["bootstrap", "--dry-run"])

    rc = bootstrap.main()
    assert rc == 1


# ---------------------------------------------------------------------------
# Live UPSERT mode (mocked DB)
# ---------------------------------------------------------------------------
def test_bootstrap_full_pipeline_with_mocked_db(
    clean_dims: list[BeliefDimension],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live mode with empty DB → 13 INSERT, exit 0, post-verify finds 13 rows."""
    from brain.belief import bootstrap

    monkeypatch.setattr(bootstrap, "load_dimensions_from_toml", lambda: clean_dims)

    # Two reads: first returns empty (snapshot before write), second returns all 13.
    list_calls = {"n": 0}

    def fake_list_dimensions() -> list[BeliefDimension]:
        list_calls["n"] += 1
        if list_calls["n"] == 1:
            return []  # snapshot: nothing exists yet
        return clean_dims  # post-write: all 13 present

    monkeypatch.setattr(bootstrap, "list_dimensions", fake_list_dimensions)

    upsert_mock = mock.MagicMock(side_effect=lambda d: 1)  # return fake id=1
    monkeypatch.setattr(bootstrap, "upsert_dimension", upsert_mock)

    monkeypatch.setattr("sys.argv", ["bootstrap"])
    rc = bootstrap.main()

    assert rc == 0
    assert upsert_mock.call_count == 13
    # All upserts received BeliefDimension instances
    for call in upsert_mock.call_args_list:
        assert isinstance(call.args[0], BeliefDimension)


def test_bootstrap_propagates_upsert_failure(
    clean_dims: list[BeliefDimension],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One upsert raises → FAIL counter increments and exit code is 1."""
    from brain.belief import bootstrap

    monkeypatch.setattr(bootstrap, "load_dimensions_from_toml", lambda: clean_dims)

    list_calls = {"n": 0}

    def fake_list_dimensions() -> list[BeliefDimension]:
        list_calls["n"] += 1
        if list_calls["n"] == 1:
            return []
        # Post-write: 12 succeeded, 1 failed → return 12
        return clean_dims[:12]

    monkeypatch.setattr(bootstrap, "list_dimensions", fake_list_dimensions)

    call_count = {"n": 0}

    def fake_upsert(dim: BeliefDimension) -> int:
        call_count["n"] += 1
        if call_count["n"] == 7:  # arbitrary mid-batch failure
            raise RuntimeError("simulated DB error on dim 7")
        return call_count["n"]

    monkeypatch.setattr(bootstrap, "upsert_dimension", fake_upsert)
    monkeypatch.setattr("sys.argv", ["bootstrap"])

    rc = bootstrap.main()
    assert rc == 1
    # All 13 attempted, even after the failure
    assert call_count["n"] == 13


def test_bootstrap_final_verification_catches_missing_rows(
    clean_dims: list[BeliefDimension],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Upsert claims success but post-verify only finds 12 rows → exit 1."""
    from brain.belief import bootstrap

    monkeypatch.setattr(bootstrap, "load_dimensions_from_toml", lambda: clean_dims)

    list_calls = {"n": 0}

    def fake_list_dimensions() -> list[BeliefDimension]:
        list_calls["n"] += 1
        if list_calls["n"] == 1:
            return []
        return clean_dims[:12]  # post-verify finds only 12

    monkeypatch.setattr(bootstrap, "list_dimensions", fake_list_dimensions)
    monkeypatch.setattr(bootstrap, "upsert_dimension", lambda d: 1)
    monkeypatch.setattr("sys.argv", ["bootstrap"])

    rc = bootstrap.main()
    assert rc == 1


def test_bootstrap_snapshot_read_failure_exits_one(
    clean_dims: list[BeliefDimension],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Initial list_dimensions read fails (e.g., migration not applied) → exit 1."""
    from brain.belief import bootstrap

    monkeypatch.setattr(bootstrap, "load_dimensions_from_toml", lambda: clean_dims)

    def boom() -> list[BeliefDimension]:
        raise RuntimeError("UndefinedTable: belief_dimensions")

    monkeypatch.setattr(bootstrap, "list_dimensions", boom)
    upsert_mock = mock.MagicMock()
    monkeypatch.setattr(bootstrap, "upsert_dimension", upsert_mock)
    monkeypatch.setattr("sys.argv", ["bootstrap"])

    rc = bootstrap.main()
    assert rc == 1
    # We aborted before any UPSERT
    assert upsert_mock.call_count == 0


def test_bootstrap_unchanged_path_on_idempotent_rerun(
    clean_dims: list[BeliefDimension],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Second run with identical existing rows → 13 UNCHANGED, exit 0."""
    from brain.belief import bootstrap

    monkeypatch.setattr(bootstrap, "load_dimensions_from_toml", lambda: clean_dims)
    # Both reads return the same 13 dims → classifier marks every one UNCHANGED.
    monkeypatch.setattr(bootstrap, "list_dimensions", lambda: list(clean_dims))
    monkeypatch.setattr(bootstrap, "upsert_dimension", lambda d: 42)
    monkeypatch.setattr("sys.argv", ["bootstrap"])

    rc = bootstrap.main()
    assert rc == 0
