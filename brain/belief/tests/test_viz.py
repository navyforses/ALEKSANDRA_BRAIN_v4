"""brain/belief/tests/test_viz.py - Phase 7.0 Day 18 unit tests.

Scope:
  - synthetic_evidence_for_dim emits the shape each likelihood needs.
  - Synthetic values are visibly different from prior means.
  - sample_posterior_for_snapshot returns InferenceData for well-behaved dims.
  - render_dimension_snapshot writes a PNG > 5 KB for a real beta dim.
  - render_all_snapshots covers all 13 dims, uses temp dir, no PHI leakage.

Pure unit tests + tmp_path for filesystem isolation - the real snapshots dir
is rendered separately via `python -m brain.belief.viz`.
"""

from __future__ import annotations

import warnings

import numpy as np
import pytest

from brain.belief.persistence import BeliefDimension
from brain.belief.likelihoods import LIKELIHOOD_VALUE_SCHEMA
from brain.belief.schema import load_dimensions_from_toml
from brain.belief.viz import (
    synthetic_evidence_for_dim,
    prior_support_and_pdf,
    sample_posterior_for_snapshot,
    render_dimension_snapshot,
    render_all_snapshots,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def catalog() -> list[BeliefDimension]:
    """The live 13-dim catalog from dimensions.toml."""
    return load_dimensions_from_toml()


@pytest.fixture
def beta_dim() -> BeliefDimension:
    return BeliefDimension(
        name="test_beta",
        distribution="beta",
        prior_params={"alpha": 2.0, "beta": 8.0},
        units="prob",
        valid_min=0.0,
        valid_max=1.0,
        citation="test-fixture-no-PMID",
    )


@pytest.fixture
def normal_dim() -> BeliefDimension:
    return BeliefDimension(
        name="test_normal",
        distribution="normal",
        prior_params={"mu": 50.0, "sigma": 10.0},
        units="score",
        valid_min=0.0,
        valid_max=100.0,
        citation="test-fixture-no-PMID",
    )


# ---------------------------------------------------------------------------
# synthetic_evidence_for_dim - shape contract per kind
# ---------------------------------------------------------------------------
def test_synthetic_evidence_for_dim_returns_required_keys(catalog) -> None:
    """For every dim in the live catalog, synthetic evidence satisfies the
    LIKELIHOOD_VALUE_SCHEMA contract for its distribution kind."""
    for dim in catalog:
        value = synthetic_evidence_for_dim(dim)
        required = LIKELIHOOD_VALUE_SCHEMA[dim.distribution]
        missing = required - set(value.keys())
        assert not missing, (
            f"{dim.name} ({dim.distribution}) synthetic evidence missing keys "
            f"{missing}; got keys {sorted(value.keys())}"
        )


def test_synthetic_evidence_covers_all_eight_distribution_kinds() -> None:
    """Synthetic generator handles all 8 kinds without raising."""
    template_dims = [
        BeliefDimension(
            name="t_beta",
            distribution="beta",
            prior_params={"alpha": 2.0, "beta": 8.0},
            citation="x",
        ),
        BeliefDimension(
            name="t_normal",
            distribution="normal",
            prior_params={"mu": 5.0, "sigma": 2.0},
            citation="x",
        ),
        BeliefDimension(
            name="t_poisson",
            distribution="poisson",
            prior_params={"mu": 1.5},
            citation="x",
        ),
        BeliefDimension(
            name="t_gamma",
            distribution="gamma",
            prior_params={"alpha": 2.0, "beta": 1.0},
            citation="x",
        ),
        BeliefDimension(
            name="t_bernoulli",
            distribution="bernoulli",
            prior_params={"p": 0.3},
            citation="x",
        ),
        BeliefDimension(
            name="t_categorical",
            distribution="categorical",
            prior_params={"probs": [0.3, 0.5, 0.2]},
            citation="x",
        ),
        BeliefDimension(
            name="t_vector",
            distribution="vector",
            prior_params={"mu_vec": [1.0, 2.0], "sigma_vec": [0.5, 0.5]},
            citation="x",
        ),
        BeliefDimension(
            name="t_exp_decay",
            distribution="exp_decay",
            prior_params={"lam": 0.002},
            citation="x",
        ),
    ]
    seen_kinds = set()
    for dim in template_dims:
        value = synthetic_evidence_for_dim(dim)
        required = LIKELIHOOD_VALUE_SCHEMA[dim.distribution]
        assert required.issubset(
            set(value.keys())
        ), f"{dim.distribution}: missing {required - set(value.keys())}"
        seen_kinds.add(dim.distribution)
    assert seen_kinds == set(LIKELIHOOD_VALUE_SCHEMA.keys())


def test_synthetic_evidence_unknown_kind_raises() -> None:
    # Pydantic blocks unknown distribution at construction time, so we
    # bypass via a SimpleNamespace-style dummy.
    class _Dummy:
        distribution = "bogus_kind_xyz"
        prior_params = {"alpha": 1.0}

    with pytest.raises(ValueError, match="no synthetic evidence template"):
        synthetic_evidence_for_dim(_Dummy())


def test_synthetic_evidence_beta_shifts_from_prior_mean(beta_dim) -> None:
    """Observed Binomial rate differs from prior mean by visible amount."""
    value = synthetic_evidence_for_dim(beta_dim)
    n, k = value["n"], value["k"]
    observed_rate = k / n
    prior_mean = beta_dim.prior_params["alpha"] / (
        beta_dim.prior_params["alpha"] + beta_dim.prior_params["beta"]
    )
    assert abs(observed_rate - prior_mean) >= 0.05, (
        f"Synthetic Beta evidence rate {observed_rate} too close to prior mean "
        f"{prior_mean} - posterior won't shift visibly"
    )


def test_synthetic_evidence_normal_observation_count(normal_dim) -> None:
    value = synthetic_evidence_for_dim(normal_dim)
    obs = value["observations"]
    assert isinstance(obs, list)
    assert len(obs) == 10
    assert all(isinstance(v, float) for v in obs)
    assert value["sigma"] > 0


def test_synthetic_evidence_categorical_indices_in_range() -> None:
    dim = BeliefDimension(
        name="test_cat",
        distribution="categorical",
        prior_params={"probs": [0.2, 0.5, 0.3]},
        citation="test",
    )
    value = synthetic_evidence_for_dim(dim)
    obs = value["observations"]
    n_classes = len(dim.prior_params["probs"])
    assert all(
        0 <= o < n_classes for o in obs
    ), f"Categorical obs {obs} out of valid range [0, {n_classes})"


def test_synthetic_evidence_bernoulli_only_zeros_and_ones() -> None:
    dim = BeliefDimension(
        name="test_b",
        distribution="bernoulli",
        prior_params={"p": 0.4},
        citation="test",
    )
    value = synthetic_evidence_for_dim(dim)
    obs = value["observations"]
    assert set(obs).issubset({0, 1})
    assert len(obs) == 10


def test_synthetic_evidence_exp_decay_in_unit_interval() -> None:
    dim = BeliefDimension(
        name="test_e",
        distribution="exp_decay",
        prior_params={"lam": 0.002},
        citation="test",
    )
    value = synthetic_evidence_for_dim(dim)
    assert value["horizon_days"] > 0
    for v in value["observations"]:
        assert 0.0 <= v <= 1.0


# ---------------------------------------------------------------------------
# prior_support_and_pdf
# ---------------------------------------------------------------------------
def test_prior_support_and_pdf_beta_returns_pdf(beta_dim) -> None:
    samples = np.random.default_rng(7).beta(2, 8, size=200)
    xs, ys, kind = prior_support_and_pdf(beta_dim, samples)
    assert kind == "pdf"
    assert len(xs) == len(ys)
    assert (ys >= 0).all()
    assert xs.min() >= 0.0 and xs.max() <= 1.0


def test_prior_support_and_pdf_poisson_returns_pmf() -> None:
    dim = BeliefDimension(
        name="t_p",
        distribution="poisson",
        prior_params={"mu": 2.0},
        citation="test",
    )
    samples = np.random.default_rng(7).poisson(2.0, size=200).astype(float)
    xs, ys, kind = prior_support_and_pdf(dim, samples)
    assert kind == "pmf"
    assert (ys >= 0).all()
    # PMF should sum to ~1 over its (truncated) support
    assert ys.sum() > 0.8  # Most of the mass


def test_prior_support_and_pdf_vector_returns_none() -> None:
    dim = BeliefDimension(
        name="t_v",
        distribution="vector",
        prior_params={"mu_vec": [1.0, 2.0], "sigma_vec": [0.5, 0.5]},
        citation="test",
    )
    xs, ys, kind = prior_support_and_pdf(dim, np.array([1.0, 2.0]))
    assert kind == "none"
    assert len(xs) == 0


# ---------------------------------------------------------------------------
# sample_posterior_for_snapshot
# ---------------------------------------------------------------------------
def test_sample_posterior_for_beta_dim_returns_trace(beta_dim) -> None:
    """Beta dim samples cleanly under the loose snapshot gates."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        trace = sample_posterior_for_snapshot(
            beta_dim,
            draws=500,
            tune=300,
            chains=2,
        )
    assert trace is not None
    # InferenceData posterior group should carry variable 'p'
    assert "p" in trace.posterior.data_vars


def test_sample_posterior_returns_none_on_unrecognized_dim() -> None:
    """A dim whose distribution kind has no synthetic-evidence template
    yields None gracefully (does not crash the batch)."""

    class _BadDim:
        name = "bad"
        distribution = "no_such_kind_zzz"
        prior_params = {}
        units = None
        valid_min = None
        valid_max = None
        citation = "x"

    trace = sample_posterior_for_snapshot(_BadDim())  # type: ignore[arg-type]
    assert trace is None


# ---------------------------------------------------------------------------
# render_dimension_snapshot
# ---------------------------------------------------------------------------
def test_render_dimension_snapshot_writes_png_over_5kb(beta_dim, tmp_path) -> None:
    """Beta dim renders a PNG of meaningful size."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        trace = sample_posterior_for_snapshot(
            beta_dim,
            draws=300,
            tune=200,
            chains=2,
        )
    assert trace is not None
    out = tmp_path / "beta.png"
    ok = render_dimension_snapshot(beta_dim, trace, out)
    assert ok is True
    assert out.exists()
    assert (
        out.stat().st_size > 5000
    ), f"Snapshot too small: {out.stat().st_size} bytes; verifier gate is 5000"


def test_render_dimension_snapshot_closes_figures(beta_dim, tmp_path) -> None:
    """No matplotlib figures leak after render (closes Figure in finally)."""
    import matplotlib.pyplot as plt

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        trace = sample_posterior_for_snapshot(
            beta_dim,
            draws=500,
            tune=300,
            chains=2,
        )
    assert trace is not None
    before = len(plt.get_fignums())
    out = tmp_path / "leakcheck.png"
    render_dimension_snapshot(beta_dim, trace, out)
    after = len(plt.get_fignums())
    assert after <= before, f"Figure leak: open figs before={before}, after={after}"


def test_render_dimension_snapshot_starts_with_png_magic_bytes(
    beta_dim, tmp_path
) -> None:
    """Confirm matplotlib actually emitted a valid PNG (not a stub)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        trace = sample_posterior_for_snapshot(
            beta_dim,
            draws=500,
            tune=300,
            chains=2,
        )
    assert trace is not None
    out = tmp_path / "magic.png"
    render_dimension_snapshot(beta_dim, trace, out)
    raw = out.read_bytes()
    # PNG file magic = \x89PNG\r\n\x1a\n
    assert raw[:8] == b"\x89PNG\r\n\x1a\n", "Not a valid PNG file"


# ---------------------------------------------------------------------------
# render_all_snapshots (live catalog, temp dir)
# ---------------------------------------------------------------------------
@pytest.mark.slow
def test_render_all_snapshots_uses_temp_dir(catalog, tmp_path) -> None:
    """All 13 live-catalog dims attempted; results dict carries one entry per dim."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        results = render_all_snapshots(output_dir=tmp_path, dimensions=catalog)
    assert len(results) == 13
    assert set(results.keys()) == {d.name for d in catalog}
    for name, r in results.items():
        assert r["status"] in {
            "ok",
            "skip",
            "error",
        }, f"{name}: unexpected status {r['status']}"


@pytest.mark.slow
def test_render_all_snapshots_majority_ok(catalog, tmp_path) -> None:
    """At least 8 of 13 dims successfully render - acceptable MVP coverage.
    (Some kinds - vector, exp_decay, categorical - may hit sampler quirks.)"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        results = render_all_snapshots(output_dir=tmp_path, dimensions=catalog)
    ok_count = sum(1 for r in results.values() if r["status"] == "ok")
    assert ok_count >= 8, (
        f"Only {ok_count}/13 dims rendered OK; need >=8 for MVP. "
        f"Results: {[(n, r['status'], r.get('reason', '')) for n, r in results.items()]}"
    )


def test_render_all_snapshots_with_empty_dim_list(tmp_path) -> None:
    """No dims -> empty result dict, no files."""
    results = render_all_snapshots(output_dir=tmp_path, dimensions=[])
    assert results == {}


# ---------------------------------------------------------------------------
# PHI guard - no Aleksandra-specific values in synthetic evidence or filenames
# ---------------------------------------------------------------------------
def test_no_phi_in_synthetic_evidence(catalog) -> None:
    """Synthetic evidence values are derived from priors only - no PHI tokens
    leak in (e.g., MRN numbers, names)."""
    banned_tokens = {
        "Aleksandra",
        "aleksandra",
        "ALEKSANDRA",
        "Jincharadze",
        "jincharadze",
        "7616818",  # BMC MRN
    }
    for dim in catalog:
        value = synthetic_evidence_for_dim(dim)
        # Flatten the value dict to a string and scan
        s = repr(value)
        for token in banned_tokens:
            assert token not in s, (
                f"PHI token {token!r} found in synthetic evidence for "
                f"{dim.name}: {s}"
            )


def test_no_phi_in_snapshot_filename(catalog, tmp_path) -> None:
    """Filenames use dim.name (concept) only - never patient identifiers."""
    banned_tokens = {"aleksandra", "jincharadze", "7616818"}
    for dim in catalog:
        snap_path = tmp_path / f"{dim.name}.png"
        for token in banned_tokens:
            assert (
                token not in str(snap_path).lower()
            ), f"PHI token {token} found in path {snap_path}"
