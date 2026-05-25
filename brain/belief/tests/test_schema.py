"""brain/belief/tests/test_schema.py — Phase 7.0 Day 6 unit tests.

Scope:
  - TOML catalog loads to exactly 13 `BeliefDimension` rows.
  - DistributionSpec enforces required prior_params per kind.
  - DistributionSpec.to_pm() instantiates inside `with pm.Model():` for all
    7 scalar kinds + the MVP vector path (independent normals).
  - validate_dimension_catalog correctly flags TBD-* citation stubs.
  - schema.py does not break the Day 5 persistence tests (no model mutation).

Pure unit tests — no Supabase connection.
"""

from __future__ import annotations


import pytest
from pydantic import ValidationError

import pymc as pm

from brain.belief.persistence import BeliefDimension
from brain.belief.schema import (
    DEFAULT_TOML_PATH,
    DISTRIBUTION_KINDS,
    REQUIRED_PARAMS,
    DistributionSpec,
    ValidationReport,
    get_dimension_spec,
    load_dimensions_from_toml,
    validate_dimension_catalog,
)


# ---------------------------------------------------------------------------
# TOML catalog — shape
# ---------------------------------------------------------------------------
def test_default_toml_path_exists() -> None:
    assert (
        DEFAULT_TOML_PATH.is_file()
    ), f"dimensions.toml missing at {DEFAULT_TOML_PATH}"


def test_load_dimensions_from_toml_returns_13() -> None:
    dims = load_dimensions_from_toml()
    assert len(dims) == 13, f"expected 13 dimensions, got {len(dims)}"


def test_all_dimensions_have_unique_names() -> None:
    dims = load_dimensions_from_toml()
    names = [d.name for d in dims]
    assert len(set(names)) == len(names), f"duplicate names found: {names}"


def test_all_distributions_in_allowed_set() -> None:
    """Every loaded row's distribution must be in the typed kind set."""
    allowed = set(REQUIRED_PARAMS.keys())
    dims = load_dimensions_from_toml()
    for d in dims:
        assert (
            d.distribution in allowed
        ), f"dim {d.name!r} uses unknown distribution {d.distribution!r}"


def test_all_dimensions_have_citation_field() -> None:
    """BeliefDimension already enforces non-empty citation; double-check it
    survives the TOML round-trip."""
    dims = load_dimensions_from_toml()
    for d in dims:
        assert d.citation, f"dim {d.name!r} has empty citation"
        assert len(d.citation) >= 1


# ---------------------------------------------------------------------------
# DistributionSpec — prior_params validation
# ---------------------------------------------------------------------------
def test_distribution_spec_accepts_well_formed_beta() -> None:
    spec = DistributionSpec(kind="beta", params={"alpha": 2.0, "beta": 5.0})
    assert spec.kind == "beta"


def test_distribution_spec_rejects_missing_required_params() -> None:
    """Each kind's `_validate_params_for_kind` must flag missing keys."""
    cases = [
        ("beta", {"alpha": 2.0}),  # missing beta
        ("normal", {"mu": 0.0}),  # missing sigma
        ("poisson", {}),  # missing mu
        ("categorical", {}),  # missing probs
        ("gamma", {"alpha": 2.0}),  # missing beta
        ("bernoulli", {}),  # missing p
        ("vector", {"mu_vec": [0.0]}),  # missing sigma_vec
        ("exp_decay", {}),  # missing lam
    ]
    for kind, params in cases:
        with pytest.raises(ValidationError):
            DistributionSpec(kind=kind, params=params)


def test_distribution_spec_required_params_table_covers_all_kinds() -> None:
    """REQUIRED_PARAMS must cover every kind in the Literal."""
    # DISTRIBUTION_KINDS is a Literal; its __args__ are the string values
    expected_kinds = set(DISTRIBUTION_KINDS.__args__)
    assert set(REQUIRED_PARAMS.keys()) == expected_kinds


# ---------------------------------------------------------------------------
# DistributionSpec.to_pm — PyMC RV construction
# ---------------------------------------------------------------------------
def _pm_factory_cases() -> list[tuple[str, dict]]:
    """One construction-valid params dict per scalar kind."""
    return [
        ("beta", {"alpha": 2.0, "beta": 5.0}),
        ("normal", {"mu": 0.0, "sigma": 1.0}),
        ("poisson", {"mu": 1.5}),
        ("categorical", {"probs": [0.2, 0.5, 0.3]}),
        ("gamma", {"alpha": 2.0, "beta": 0.5}),
        ("bernoulli", {"p": 0.4}),
        ("exp_decay", {"lam": 0.01}),
    ]


@pytest.mark.parametrize("kind,params", _pm_factory_cases())
def test_distribution_spec_to_pm_creates_rv(kind: str, params: dict) -> None:
    """Inside `with pm.Model():`, every scalar kind returns a non-None RV."""
    spec = DistributionSpec(kind=kind, params=params)
    with pm.Model():
        rv = spec.to_pm(name=f"test_{kind}")
        assert rv is not None
        # PyMC RVs are PyTensor TensorVariables — check the attribute exists
        assert hasattr(rv, "name")


def test_distribution_spec_to_pm_vector_mvp() -> None:
    """Vector path lowers to independent normals over a flat shape vector."""
    spec = DistributionSpec(
        kind="vector",
        params={"mu_vec": [0.0, 1.0, 2.0], "sigma_vec": [1.0, 1.0, 1.0]},
    )
    with pm.Model():
        rv = spec.to_pm(name="test_vec")
        assert rv is not None


def test_distribution_spec_to_pm_vector_dim_mismatch_raises() -> None:
    spec = DistributionSpec(
        kind="vector",
        params={"mu_vec": [0.0, 1.0], "sigma_vec": [1.0]},
    )
    with pm.Model():
        with pytest.raises(ValueError, match="vector dim mismatch"):
            spec.to_pm(name="bad_vec")


# ---------------------------------------------------------------------------
# validate_dimension_catalog
# ---------------------------------------------------------------------------
def test_validate_dimension_catalog_flags_stub_citations() -> None:
    """Synthetic 'TBD-' fixture → reported as stub. Tests stub-detection LOGIC.

    Day 6 had 13 live stubs; Days 7-9 librarians filled them all with real
    PubMed PMIDs, so the live catalog now has 0 stubs (covered by
    test_live_catalog_has_zero_stubs below). This test exercises the
    detection logic against a synthetic stub row to guard the logic
    itself.
    """
    stub_dim = BeliefDimension(
        name="stub_test_dim",
        distribution="beta",
        prior_params={"alpha": 1.0, "beta": 1.0},
        citation="TBD-Day-99-librarian-Z",
    )
    real_dim = BeliefDimension(
        name="real_test_dim",
        distribution="normal",
        prior_params={"mu": 0.0, "sigma": 1.0},
        citation="https://pubmed.ncbi.nlm.nih.gov/9183258/",
    )
    report = validate_dimension_catalog([stub_dim, real_dim])

    assert isinstance(report, ValidationReport)
    assert report.total == 2
    assert report.valid == 2
    assert report.invalid == []
    assert report.stubs_pending_citation == ["stub_test_dim"]


def test_live_catalog_has_zero_stubs() -> None:
    """v7.0-ready gate: the live dimensions.toml must have 0 unresolved citations.

    This test FAILS during Day 6 (13 stubs expected) and PASSES once Days 7-9
    librarian work lands real PubMed PMIDs for every dimension. After Day 9
    this should stay PASS forever (Phase 7.0 closure invariant).
    """
    dims = load_dimensions_from_toml()
    report = validate_dimension_catalog(dims)

    assert report.total == 13
    assert report.valid == 13
    assert report.invalid == []
    assert (
        report.stubs_pending_citation == []
    ), f"live catalog still has stub citations: {report.stubs_pending_citation}"


def test_validate_dimension_catalog_passes_on_real_citations() -> None:
    """Synthetic fixture with PubMed citations → 0 stubs reported."""
    real_dims = [
        BeliefDimension(
            name="dim_a",
            distribution="beta",
            prior_params={"alpha": 2.0, "beta": 5.0},
            citation="https://pubmed.ncbi.nlm.nih.gov/9183258/",
        ),
        BeliefDimension(
            name="dim_b",
            distribution="normal",
            prior_params={"mu": 100.0, "sigma": 15.0},
            citation="https://doi.org/10.1038/s41597-024-03986-7",
        ),
    ]
    report = validate_dimension_catalog(real_dims, expected_total=2)
    assert report.total == 2
    assert report.valid == 2
    assert report.stubs_pending_citation == []


def test_validate_dimension_catalog_records_invalid_params() -> None:
    """A dimension with bad prior_params shape lands in report.invalid."""
    # BeliefDimension itself doesn't check params shape (only distribution
    # name). validate_dimension_catalog catches the shape mismatch.
    bad = BeliefDimension(
        name="bad_beta",
        distribution="beta",
        prior_params={"alpha": 2.0},  # missing 'beta'
        citation="https://example.com/source",
    )
    report = validate_dimension_catalog([bad], expected_total=1)
    assert report.total == 1
    assert report.valid == 0
    assert len(report.invalid) == 1
    assert report.invalid[0]["name"] == "bad_beta"


def test_validate_dimension_catalog_reports_distribution_coverage() -> None:
    """The 13-D catalog touches multiple distribution kinds."""
    dims = load_dimensions_from_toml()
    report = validate_dimension_catalog(dims)
    # Architecture §3 uses: beta, categorical, poisson, normal, gamma,
    # bernoulli, vector, exp_decay — all 8.
    expected = {
        "beta",
        "categorical",
        "poisson",
        "normal",
        "gamma",
        "bernoulli",
        "vector",
        "exp_decay",
    }
    assert set(report.distributions_covered) == expected


# ---------------------------------------------------------------------------
# get_dimension_spec — projection helper
# ---------------------------------------------------------------------------
def test_get_dimension_spec_round_trips() -> None:
    dim = BeliefDimension(
        name="x",
        distribution="gamma",
        prior_params={"alpha": 2.0, "beta": 0.5},
        citation="https://example.com",
    )
    spec = get_dimension_spec(dim)
    assert spec.kind == "gamma"
    assert spec.params == {"alpha": 2.0, "beta": 0.5}


# ---------------------------------------------------------------------------
# Day 5 persistence regression — schema.py imports must not break models
# ---------------------------------------------------------------------------
def test_schema_does_not_break_persistence_models() -> None:
    """Importing schema.py + loading the TOML must leave `BeliefDimension`
    usable exactly as Day 5 tests expect it."""
    # Round-trip every loaded row through model_dump → re-construct
    dims = load_dimensions_from_toml()
    for d in dims:
        d2 = BeliefDimension(**d.model_dump())
        assert d == d2


def test_schema_load_does_not_touch_db() -> None:
    """The Day 5 _get_conn() raises without SUPABASE_DB_URL; schema loaders
    must not touch the DB at all (pure file I/O)."""
    import os

    saved = os.environ.pop("SUPABASE_DB_URL", None)
    try:
        # Should succeed even with no DB env present.
        dims = load_dimensions_from_toml()
        assert len(dims) == 13
        report = validate_dimension_catalog(dims)
        assert report.total == 13
    finally:
        if saved is not None:
            os.environ["SUPABASE_DB_URL"] = saved
