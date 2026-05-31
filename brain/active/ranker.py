"""Phase 7.4 Day 4 — EIG ranker (cost-weighted).

Walks every (BeliefDimension, CandidateObservation) pair, computes EIG,
and ranks by `cost_weighted_eig = eig.eig_nats / max(wife_time_min, 0.1)`.

Spec §1 Day 4: "top-K observations by EIG; cost-weighted (wife time ≤ 5
min/observation)". We don't enforce the 5-min cap here — Bayley-III is
clinician-administered and exceeds it; the cost weighting handles it
automatically by deprioritising long observations.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from brain.active.catalog import (
    CANDIDATE_CATALOG,
    CandidateObservation,
    get_catalog_for_dimension,
)
from brain.active.eig import EIGEstimate, compute_eig_for_dimension
from brain.belief.persistence import BeliefDimension


class RankedObservation(BaseModel):
    """One (CandidateObservation, EIG) pair with cost-weighted score."""

    model_config = ConfigDict(extra="forbid")

    observation: CandidateObservation
    eig: EIGEstimate
    cost_weighted_eig: float = Field(..., ge=0.0)


def _cost_weighted(eig_nats: float, wife_time_minutes: float) -> float:
    return float(eig_nats / max(wife_time_minutes, 0.1))


def rank_observations(
    *,
    dimensions: list[BeliefDimension],
    n_simulations: int = 1000,
    rng: Optional[np.random.Generator] = None,
) -> list[RankedObservation]:
    """Compute EIG for every (dim, candidate) pair and sort by cost-weighted EIG.

    Deterministic: same inputs + same seed -> same output ordering.
    """
    if rng is None:
        rng = np.random.default_rng(7)
    dim_by_name = {d.name: d for d in dimensions}
    ranked: list[RankedObservation] = []
    for candidate in CANDIDATE_CATALOG:
        dim = dim_by_name.get(candidate.dim_name)
        if dim is None:
            continue
        est = compute_eig_for_dimension(
            dim,
            observation_type=candidate.observation_type,
            n_simulations=n_simulations,
            rng=rng,
        )
        score = _cost_weighted(est.eig_nats, candidate.wife_time_minutes)
        ranked.append(
            RankedObservation(
                observation=candidate, eig=est, cost_weighted_eig=score
            )
        )
    # Stable sort: tie-breaks by dim_name then observation_type for determinism.
    ranked.sort(
        key=lambda r: (
            -r.cost_weighted_eig,
            r.observation.dim_name,
            r.observation.observation_type,
        )
    )
    return ranked


def top_k(
    ranked: list[RankedObservation],
    k: int = 3,
    *,
    exclude_observation_types: Optional[set[str]] = None,
) -> list[RankedObservation]:
    """Return up to `k` highest-scoring observations, optionally filtered."""
    if k <= 0:
        return []
    excluded = exclude_observation_types or set()
    filtered = [r for r in ranked if r.observation.observation_type not in excluded]
    return filtered[:k]


def rank_for_single_dimension(
    dim: BeliefDimension,
    *,
    n_simulations: int = 1000,
    rng: Optional[np.random.Generator] = None,
) -> list[RankedObservation]:
    """Convenience: rank candidates for a single dimension only."""
    if rng is None:
        rng = np.random.default_rng(7)
    candidates = get_catalog_for_dimension(dim.name)
    ranked: list[RankedObservation] = []
    for candidate in candidates:
        est = compute_eig_for_dimension(
            dim,
            observation_type=candidate.observation_type,
            n_simulations=n_simulations,
            rng=rng,
        )
        score = _cost_weighted(est.eig_nats, candidate.wife_time_minutes)
        ranked.append(
            RankedObservation(
                observation=candidate, eig=est, cost_weighted_eig=score
            )
        )
    ranked.sort(key=lambda r: -r.cost_weighted_eig)
    return ranked


__all__ = [
    "RankedObservation",
    "rank_observations",
    "top_k",
    "rank_for_single_dimension",
]
