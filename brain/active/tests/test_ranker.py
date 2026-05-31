"""Phase 7.4 Day 4 — ranker tests."""

from __future__ import annotations

import numpy as np

from brain.active.ranker import (
    RankedObservation,
    rank_for_single_dimension,
    rank_observations,
    top_k,
)
from brain.belief.schema import load_dimensions_from_toml


def test_rank_returns_sorted_descending() -> None:
    """Verifier check 3: rank_observations returns top-K sorted descending."""
    dims = load_dimensions_from_toml()
    ranked = rank_observations(dimensions=dims, n_simulations=200)
    assert len(ranked) >= 13
    scores = [r.cost_weighted_eig for r in ranked]
    assert scores == sorted(scores, reverse=True), f"not descending: {scores}"
    assert all(isinstance(r, RankedObservation) for r in ranked)


def test_top_k_respects_k() -> None:
    dims = load_dimensions_from_toml()
    ranked = rank_observations(dimensions=dims, n_simulations=100)
    top3 = top_k(ranked, k=3)
    assert len(top3) <= 3
    top0 = top_k(ranked, k=0)
    assert top0 == []


def test_exclude_filter_respected() -> None:
    dims = load_dimensions_from_toml()
    ranked = rank_observations(dimensions=dims, n_simulations=100)
    if not ranked:
        return
    excluded_type = ranked[0].observation.observation_type
    filtered = top_k(ranked, k=5, exclude_observation_types={excluded_type})
    assert all(
        r.observation.observation_type != excluded_type for r in filtered
    )


def test_deterministic_with_seed() -> None:
    dims = load_dimensions_from_toml()
    r1 = rank_observations(
        dimensions=dims, n_simulations=100, rng=np.random.default_rng(7)
    )
    r2 = rank_observations(
        dimensions=dims, n_simulations=100, rng=np.random.default_rng(7)
    )
    pairs1 = [(r.observation.dim_name, r.observation.observation_type) for r in r1]
    pairs2 = [(r.observation.dim_name, r.observation.observation_type) for r in r2]
    assert pairs1 == pairs2


def test_rank_for_single_dimension() -> None:
    dims = load_dimensions_from_toml()
    dim = next(d for d in dims if d.name == "head_control_seconds")
    ranked = rank_for_single_dimension(dim, n_simulations=100)
    assert all(r.observation.dim_name == "head_control_seconds" for r in ranked)
