"""Phase 7.3 Day 2 — Monte Carlo trajectory generator.

Given a Scenario and the 13-dimension catalog, this module samples
``n_samples`` trajectories of length ``horizon_days + 1`` per selected
outcome, applies interventions on a per-day grid, and (optionally) injects
the reference SCM's Vigabatrin -> Seizure-frequency mediator effect.

Design choices:
    - Direct ``numpy.random.Generator`` samplers per distribution kind,
      avoiding PyMC sampler overhead (PyMC is for *posterior inference*,
      not forward Monte Carlo over fixed priors).
    - We do NOT materialize ``Trajectory`` objects for every sample (would
      be ~13 dims * (horizon+1) floats * 10K samples = ~50MB+ object
      churn). Instead we return a dense 3-D ``np.ndarray`` of shape
      ``(n_samples, n_outcomes, horizon_days + 1)``.
    - Mediator coefficient (1.2) and GABA-T factor (0.7) for the
      Vigabatrin -> Seizure effect are documented in
      ``brain/causal/scm.py::build_reference_scm`` (edge PMID:7686614,
      Lippa-Loftis GABA-T inhibition). The seizure-reduction delta per
      active-day is ``-1.2 * (1.0 - 0.7) = -0.36`` events/day, clipped at
      seizure_freq_per_day's valid_min.

Performance target (verifier check 2):
    100 samples * 400 days * 5 outcomes < 60 s on a Windows laptop.

Reference:
    - v7_architecture/70_PHASES/73_PHASE_7_3_SIMULATION_ENGINE_3W.md
      section 1 layer A Day 2.
    - brain/causal/scm.py PMID-cited mediator coefficients.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from pydantic import BaseModel, ConfigDict

from brain.belief.persistence import BeliefDimension
from brain.belief.schema import load_dimensions_from_toml
from brain.causal.scm import SCM
from brain.sim.scenario import Intervention, Scenario


# ---------------------------------------------------------------------------
# Mediator constants for Vigabatrin -> Seizure-frequency reduction.
# Sourced from brain/causal/scm.py edge PMID:7686614 (Lippa-Loftis, 1993).
# ---------------------------------------------------------------------------
VIGABATRIN_MEDIATOR_COEFFICIENT = 1.2
VIGABATRIN_GABA_T_FACTOR = 0.7
VIGABATRIN_TARGET_DIM = "seizure_freq_per_day"
VIGABATRIN_INTERVENTION_NAME = "vigabatrin"


# ---------------------------------------------------------------------------
# Ephemeral Trajectory wrapper (not used internally; available for callers
# that want a typed view over a single sample).
# ---------------------------------------------------------------------------
class Trajectory(BaseModel):
    """One sample-level trajectory.

    Memory-heavy; kept ephemeral. ``simulate_scenario`` returns a 3-D
    ndarray instead so 10_000 samples stay below the cache budget.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    sample_id: int
    dimension_values: dict[str, np.ndarray]


# ---------------------------------------------------------------------------
# Per-distribution prior sampler
# ---------------------------------------------------------------------------
def _sample_from_dimension_prior(
    dim: BeliefDimension,
    rng: np.random.Generator,
) -> float:
    """Draw a single scalar from a dimension's prior distribution.

    Honours ``valid_min`` / ``valid_max`` via post-sample clipping for
    unbounded distributions (normal). Bounded distributions (beta,
    poisson with non-negative support, bernoulli) clip only when the
    catalog row sets a stricter bound.
    """
    kind = dim.distribution
    p = dim.prior_params
    vmin = dim.valid_min
    vmax = dim.valid_max

    if kind == "beta":
        val = float(rng.beta(p["alpha"], p["beta"]))
    elif kind == "normal":
        val = float(rng.normal(p["mu"], p["sigma"]))
    elif kind == "poisson":
        val = float(rng.poisson(p["mu"]))
    elif kind == "categorical":
        probs = np.asarray(p["probs"], dtype=float)
        probs = probs / probs.sum()
        val = float(rng.choice(len(probs), p=probs))
    elif kind == "gamma":
        # scipy/numpy gamma uses scale = 1/rate; our toml convention
        # mirrors PyMC (alpha + beta-as-rate), so scale = 1/beta.
        val = float(rng.gamma(p["alpha"], 1.0 / p["beta"]))
    elif kind == "bernoulli":
        val = float(rng.binomial(1, p["p"]))
    elif kind == "vector":
        mu_vec = np.asarray(p["mu_vec"], dtype=float)
        sigma_vec = np.asarray(p["sigma_vec"], dtype=float)
        # Trajectory uses scalar; pick first component as canonical scalar.
        val = float(rng.normal(mu_vec[0], sigma_vec[0]))
    elif kind == "exp_decay":
        val = float(rng.exponential(1.0 / p["lam"]))
    else:
        raise ValueError(f"unknown distribution kind: {kind!r}")

    if vmin is not None and val < vmin:
        val = float(vmin)
    if vmax is not None and val > vmax:
        val = float(vmax)
    return val


def _initial_state_for_sample(
    dims: list[BeliefDimension],
    rng: np.random.Generator,
) -> dict[str, float]:
    """Draw a day-0 value for every dimension in the catalog."""
    return {d.name: _sample_from_dimension_prior(d, rng) for d in dims}


# ---------------------------------------------------------------------------
# Intervention-activity grid
# ---------------------------------------------------------------------------
def _intervention_active_on_day(intv: Intervention, day: int) -> bool:
    """Return True iff this intervention fires on ``day``."""
    start = intv.effective_start_day()
    if day < start:
        return False

    duration = intv.duration_days
    if duration is not None and day >= start + duration:
        return False

    freq = intv.frequency or "once"
    if freq == "once":
        return day == start
    if freq == "daily":
        return True
    if freq == "weekly":
        return (day - start) % 7 == 0
    if freq == "monthly":
        return (day - start) % 30 == 0
    return False


def _clip_to_dim(value: float, dim: Optional[BeliefDimension]) -> float:
    if dim is None:
        return value
    if dim.valid_min is not None and value < dim.valid_min:
        return float(dim.valid_min)
    if dim.valid_max is not None and value > dim.valid_max:
        return float(dim.valid_max)
    return value


def _apply_intervention_to_state(
    state: dict[str, float],
    intv: Intervention,
    dim_index: dict[str, BeliefDimension],
) -> None:
    """Apply one intervention's deltas to ``state`` in place."""
    if intv.type == "manual_dimension_shift":
        target = intv.target_dimension
        if target is None or intv.dimension_delta is None:  # pragma: no cover
            return
        state[target] = _clip_to_dim(
            state.get(target, 0.0) + float(intv.dimension_delta),
            dim_index.get(target),
        )
        return

    for dim_name, delta in (intv.effect_per_dim or {}).items():
        if dim_name not in state:
            continue
        state[dim_name] = _clip_to_dim(
            state[dim_name] + float(delta),
            dim_index.get(dim_name),
        )


# ---------------------------------------------------------------------------
# Single-sample trajectory
# ---------------------------------------------------------------------------
def simulate_trajectory(
    scenario: Scenario,
    *,
    dims: list[BeliefDimension],
    reference_scm: Optional[SCM] = None,
    sample_id: int = 0,
    rng_seed: Optional[int] = None,
) -> dict[str, np.ndarray]:
    """Generate one Monte Carlo trajectory.

    Args:
        scenario: the Scenario to simulate.
        dims: full dimension catalog (used to look up valid_min/valid_max
            and to sample day-0 state).
        reference_scm: when provided AND a ``vigabatrin`` intervention is
            present, apply the GABA-T-mediated seizure-frequency reduction
            on every Vigabatrin-active day.
        sample_id: index of this sample within the batch (used to
            stagger the seed deterministically).
        rng_seed: override seed. When ``None``, falls back to
            ``scenario.random_seed + sample_id`` (defaulting to
            ``42 + sample_id`` when scenario.random_seed is also None).

    Returns:
        Dict keyed by scenario.outcomes name -> ndarray of shape
        ``(horizon_days + 1,)``. Only the selected outcomes are stored
        (saves memory; non-outcome dims are still simulated but discarded).
    """
    if rng_seed is None:
        base = scenario.random_seed if scenario.random_seed is not None else 42
        rng_seed = base + sample_id
    rng = np.random.default_rng(rng_seed)

    dim_index = {d.name: d for d in dims}

    state = _initial_state_for_sample(dims, rng)
    horizon = scenario.horizon_days
    n_steps = horizon + 1

    out: dict[str, np.ndarray] = {
        name: np.empty(n_steps, dtype=float) for name in scenario.outcomes
    }
    for name in scenario.outcomes:
        out[name][0] = state.get(name, 0.0)

    has_vigabatrin = (
        reference_scm is not None
        and any(
            intv.name == VIGABATRIN_INTERVENTION_NAME
            for intv in scenario.interventions
        )
    )
    vigabatrin_interventions = [
        intv
        for intv in scenario.interventions
        if intv.name == VIGABATRIN_INTERVENTION_NAME
    ]
    seizure_dim = dim_index.get(VIGABATRIN_TARGET_DIM)
    mediator_delta = -VIGABATRIN_MEDIATOR_COEFFICIENT * (
        1.0 - VIGABATRIN_GABA_T_FACTOR
    )

    for day in range(1, n_steps):
        # Daily state carries forward the previous day.
        # (No diffusion/decay for layer A; deferred to Phase 7.4+.)
        for intv in scenario.interventions:
            if _intervention_active_on_day(intv, day):
                _apply_intervention_to_state(state, intv, dim_index)

        if has_vigabatrin:
            for vintv in vigabatrin_interventions:
                if _intervention_active_on_day(vintv, day):
                    state[VIGABATRIN_TARGET_DIM] = _clip_to_dim(
                        state.get(VIGABATRIN_TARGET_DIM, 0.0) + mediator_delta,
                        seizure_dim,
                    )
                    break  # apply mediator once per day even if multiple rows

        for name in scenario.outcomes:
            out[name][day] = state.get(name, 0.0)

    return out


# ---------------------------------------------------------------------------
# Batched scenario simulation
# ---------------------------------------------------------------------------
def simulate_scenario(
    scenario: Scenario,
    *,
    dims: Optional[list[BeliefDimension]] = None,
    reference_scm: Optional[SCM] = None,
) -> np.ndarray:
    """Run ``scenario.n_samples`` trajectories.

    Args:
        scenario: the Scenario to simulate.
        dims: optional dimension catalog override; loaded from
            ``dimensions.toml`` when omitted (no DB call).
        reference_scm: optional SCM whose Vigabatrin -> Seizure mediator
            effect is applied when a vigabatrin intervention is present.

    Returns:
        3-D ndarray of shape
        ``(n_samples, n_outcomes, horizon_days + 1)``; column index
        matches ``scenario.outcomes`` order exactly.
    """
    if dims is None:
        dims = load_dimensions_from_toml()

    n = scenario.n_samples
    o = len(scenario.outcomes)
    h = scenario.horizon_days + 1
    out = np.empty((n, o, h), dtype=float)

    for sample_id in range(n):
        traj = simulate_trajectory(
            scenario,
            dims=dims,
            reference_scm=reference_scm,
            sample_id=sample_id,
        )
        for j, name in enumerate(scenario.outcomes):
            out[sample_id, j, :] = traj[name]

    return out


__all__ = [
    "Trajectory",
    "simulate_trajectory",
    "simulate_scenario",
    "VIGABATRIN_MEDIATOR_COEFFICIENT",
    "VIGABATRIN_GABA_T_FACTOR",
    "VIGABATRIN_TARGET_DIM",
    "VIGABATRIN_INTERVENTION_NAME",
]
