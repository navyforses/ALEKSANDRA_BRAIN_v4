"""Phase 7.3 Layer C Day 12 — Framework-agnostic Simulation Studio handlers.

These handlers are **framework-agnostic**: they expose typed Pydantic
request / response models plus pure functions that take request payloads
and return response payloads. Mount them onto FastAPI / Starlette / Flask
in the operator bootstrap (Phase 7.6 frontend); Phase 7.3 ships the
contract + behaviour, NOT the HTTP server. FastAPI is intentionally NOT
a dependency of the brain package at this phase.

API shape matches v7_architecture/70_PHASES/73_PHASE_7_3_SIMULATION_ENGINE_3W.md §1
layer C Days 11-12.

Three endpoints worth of contract:

    POST   /api/sim/scenarios          -> handle_save_scenario
    GET    /api/sim/scenarios          -> handle_list_scenarios
    POST   /api/sim/compare            -> handle_compare_scenarios

Budget guard (Day 14, spec §1 + verifier check 11/12):

    check_simulation_budget(scenario) enforces two limits:
        - Hard sample cap: n_samples <= 10_000 (verifier check 11)
        - Posterior-uncertainty guard: at least 7 of 13 dimensions must
          have prior sd / |prior mean| <= 0.5; otherwise raise
          BudgetGuardError (RULE 10 from spec, verifier check 12).

Reference:
    - brain/causal/api.py (framework-agnostic handler precedent)
    - brain/sim/scenario.py + persistence.py + cache.py + compare.py
"""

from __future__ import annotations

import math
from typing import Any, Callable, Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from brain.belief.persistence import BeliefDimension
from brain.belief.schema import load_dimensions_from_toml
from brain.sim.compare import (
    ScenarioComparison,
    compare_scenarios,
    default_prefer_higher_map,
)
from brain.sim.persistence import (
    json_to_scenario,
    list_scenarios as list_scenarios_db,
    save_scenario,
    save_scenario_comparison,
    scenario_to_json,
)
from brain.sim.scenario import Scenario, compute_scenario_hash


# ---------------------------------------------------------------------------
# Budget guard
# ---------------------------------------------------------------------------
HARD_N_SAMPLES_CAP = 10_000
POSTERIOR_SD_RATIO_LIMIT = 0.5
MIN_DIMS_PASSING_SD_GUARD = 7


class BudgetGuardError(RuntimeError):
    """Raised when a scenario violates Phase 7.3 budget / uncertainty caps."""


def _sd_mean_for_dim(dim: BeliefDimension) -> Optional[tuple[float, float]]:
    """Return (sd, |mean|) for a dimension, or None when not derivable.

    For closed-form distributions (beta, normal, poisson, gamma, bernoulli,
    exp_decay) the values come from the prior_params analytically. For
    categorical / vector dims the function returns None (caller treats
    these as automatically passing the guard — sd/mean is ill-defined
    for index-valued or multivariate priors).
    """
    kind = dim.distribution
    p = dim.prior_params
    if kind == "beta":
        a, b = float(p["alpha"]), float(p["beta"])
        denom = a + b
        if denom <= 0:
            return None
        mean = a / denom
        var = (a * b) / (denom * denom * (denom + 1.0))
        return math.sqrt(var), abs(mean)
    if kind == "normal":
        return float(p["sigma"]), abs(float(p["mu"]))
    if kind == "poisson":
        mu = float(p["mu"])
        return math.sqrt(max(mu, 0.0)), abs(mu)
    if kind == "gamma":
        a, b = float(p["alpha"]), float(p["beta"])
        if b <= 0:
            return None
        mean = a / b
        sd = math.sqrt(a) / b
        return sd, abs(mean)
    if kind == "bernoulli":
        p_val = float(p["p"])
        mean = p_val
        sd = math.sqrt(max(0.0, p_val * (1.0 - p_val)))
        return sd, abs(mean)
    if kind == "exp_decay":
        lam = float(p["lam"])
        if lam <= 0:
            return None
        mean = 1.0 / lam
        sd = 1.0 / lam  # exponential distribution: sd == mean
        return sd, abs(mean)
    # categorical / vector: sd/mean ill-defined for our purposes
    return None


def check_simulation_budget(
    scenario: Scenario,
    *,
    dims: Optional[list[BeliefDimension]] = None,
) -> None:
    """Raise BudgetGuardError if a scenario violates phase budget caps.

    Hard rule: ``n_samples <= 10_000`` (verifier check 11).
    Soft rule (RULE 10, verifier check 12): at least 7 of 13 dimensions
    must have ``prior_sd / max(|prior_mean|, 1e-6) <= 0.5``. Categorical
    and vector dims are auto-counted as passing.

    Args:
        scenario: validated Scenario to check.
        dims: optional override for the dimensions catalog; defaults to
            ``load_dimensions_from_toml()``.

    Raises:
        BudgetGuardError: with a message naming the failing dimensions.
    """
    if scenario.n_samples > HARD_N_SAMPLES_CAP:
        raise BudgetGuardError(
            f"n_samples={scenario.n_samples} exceeds hard cap "
            f"{HARD_N_SAMPLES_CAP} (Phase 7.3 verifier check 11)"
        )

    dims_used = dims if dims is not None else load_dimensions_from_toml()

    passing = 0
    failing_names: list[str] = []
    for dim in dims_used:
        pair = _sd_mean_for_dim(dim)
        if pair is None:
            # categorical / vector: count as passing (ill-defined ratio)
            passing += 1
            continue
        sd, abs_mean = pair
        ratio = sd / max(abs_mean, 1e-6)
        if ratio <= POSTERIOR_SD_RATIO_LIMIT:
            passing += 1
        else:
            failing_names.append(f"{dim.name}(ratio={ratio:.2f})")

    if passing < MIN_DIMS_PASSING_SD_GUARD:
        raise BudgetGuardError(
            f"only {passing}/{len(dims_used)} dimensions pass "
            f"sd/mean <= {POSTERIOR_SD_RATIO_LIMIT} "
            f"(need {MIN_DIMS_PASSING_SD_GUARD}); "
            f"failing: {failing_names}"
        )


# ---------------------------------------------------------------------------
# Phase 7.5 Rule #10 — Constitutional uncertainty guard
# ---------------------------------------------------------------------------
# Tighter than the Phase 7.3 prompt-budget check (which counts how many
# of the 13 dims pass a 0.5 ratio bar). Rule #10 forbids running a
# simulation when the AVERAGE empirical sd/mean across the 13 dims is
# itself > 0.5 — even if 7 individual dims happen to pass.
#
# The check draws 200 samples per dim via the Phase 7.3 _sample_from_
# dimension_prior helper, then asks: is the mean posterior sd / mean
# ratio across the catalog under 0.5? If yes, the simulation is
# informative enough to run; if no, the model is too uncertain and the
# simulation would produce confidence-theatre output.
CONSTITUTIONAL_AVG_SD_RATIO_LIMIT = 0.5
CONSTITUTIONAL_DRAWS_PER_DIM = 200


def check_simulation_uncertainty_constitutional(
    scenario: Scenario,
    *,
    dims: Optional[list[BeliefDimension]] = None,
) -> None:
    """Phase 7.5 Rule #10 — Constitutional uncertainty guard.

    Runs the Phase 7.3 ``check_simulation_budget`` first (so existing
    rules still hold), then computes the empirical sd/mean ratio per
    dim by drawing ``CONSTITUTIONAL_DRAWS_PER_DIM`` samples per dim
    and refuses if the mean ratio across the catalog exceeds
    ``CONSTITUTIONAL_AVG_SD_RATIO_LIMIT``.

    Tighter than ``check_simulation_budget``: that function counts how
    many dims pass a per-dim 0.5 bar; this function asks whether the
    AVERAGE ratio is itself under 0.5. A catalog where every dim sits
    exactly at sd/mean == 1.0 would pass check_simulation_budget
    (categorical dims auto-pass) but fail this constitutional check.

    Raises:
        BudgetGuardError: scenario violates Phase 7.3 caps OR the
            empirical-ratio mean exceeds the constitutional bar.
    """
    # Defence in depth: Phase 7.3 check fires first.
    check_simulation_budget(scenario, dims=dims)

    # Lazy import to avoid a circular dependency at module load time.
    from brain.sim.trajectory import _sample_from_dimension_prior

    dims_used = dims if dims is not None else load_dimensions_from_toml()
    rng = np.random.default_rng(seed=7)

    ratios: list[float] = []
    for dim in dims_used:
        try:
            draws = np.asarray(
                [
                    _sample_from_dimension_prior(dim, rng)
                    for _ in range(CONSTITUTIONAL_DRAWS_PER_DIM)
                ],
                dtype=float,
            )
        except Exception:  # pragma: no cover
            # Dims that cannot be sampled (categorical with bad probs etc.)
            # are skipped — they neither help nor hurt the average.
            continue
        mean = float(np.mean(draws))
        sd = float(np.std(draws, ddof=1))
        denom = max(abs(mean), 1e-6)
        ratios.append(sd / denom)

    if not ratios:
        raise BudgetGuardError(
            "Phase 7.5 Rule #10: no samplable dimensions in catalog — "
            "cannot evaluate constitutional uncertainty guard"
        )

    avg_ratio = float(np.mean(ratios))
    if avg_ratio > CONSTITUTIONAL_AVG_SD_RATIO_LIMIT:
        raise BudgetGuardError(
            f"Phase 7.5 Rule #10: empirical avg sd/mean ratio "
            f"{avg_ratio:.3f} > {CONSTITUTIONAL_AVG_SD_RATIO_LIMIT} "
            f"({len(ratios)} dims sampled, "
            f"{CONSTITUTIONAL_DRAWS_PER_DIM} draws/dim). Posterior too "
            f"uncertain to run an informative simulation; collect more "
            f"evidence via active-learning loop first."
        )


# ---------------------------------------------------------------------------
# Save scenario — request + response
# ---------------------------------------------------------------------------
class SaveScenarioRequest(BaseModel):
    """Request body for POST /api/sim/scenarios."""

    model_config = ConfigDict(extra="forbid")

    scenario: dict[str, Any]
    created_by: str = Field("system", min_length=1)


class SaveScenarioResponse(BaseModel):
    """Response body for POST /api/sim/scenarios."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    scenario_hash: str = Field(..., min_length=64, max_length=64)
    was_dry_run: bool


def handle_save_scenario(req: SaveScenarioRequest) -> SaveScenarioResponse:
    """Validate + persist a Scenario; return id + hash.

    The handler:
        1. Rebuilds the Scenario from ``req.scenario`` via Pydantic.
        2. Runs ``check_simulation_budget`` for fast-fail.
        3. Computes the scenario hash.
        4. Calls ``save_scenario`` (DRY_RUN sentinel when DSN unset).

    Raises:
        pydantic.ValidationError: malformed scenario payload.
        BudgetGuardError: scenario violates n_samples or sd/mean caps.
    """
    scenario = json_to_scenario(req.scenario)
    check_simulation_budget(scenario)
    scenario_hash = compute_scenario_hash(scenario)
    saved_id = save_scenario(scenario, created_by=req.created_by)
    return SaveScenarioResponse(
        scenario_id=saved_id,
        scenario_hash=scenario_hash,
        was_dry_run=saved_id.startswith("DRY_RUN:"),
    )


# ---------------------------------------------------------------------------
# List scenarios — response
# ---------------------------------------------------------------------------
class ListScenariosResponse(BaseModel):
    """Response body for GET /api/sim/scenarios."""

    model_config = ConfigDict(extra="forbid")

    scenarios: list[dict[str, Any]]
    count: int = Field(..., ge=0)


def handle_list_scenarios() -> ListScenariosResponse:
    """List all scenarios. DRY_RUN -> empty list."""
    records = list_scenarios_db()
    payloads = [r.model_dump() for r in records]
    return ListScenariosResponse(
        scenarios=payloads,
        count=len(payloads),
    )


# ---------------------------------------------------------------------------
# Compare scenarios — request + response
# ---------------------------------------------------------------------------
class CompareScenariosRequest(BaseModel):
    """Request body for POST /api/sim/compare.

    When ``SUPABASE_DB_URL`` is unset and the named scenarios are not
    found in DRY_RUN, the handler will fall back to building the Scenarios
    from the request payload via ``scenario_a_payload`` /
    ``scenario_b_payload`` (both required in DRY_RUN mode).
    """

    model_config = ConfigDict(extra="forbid")

    scenario_a_name: str = Field(..., min_length=1)
    scenario_b_name: str = Field(..., min_length=1)
    scenario_a_payload: Optional[dict[str, Any]] = None
    scenario_b_payload: Optional[dict[str, Any]] = None
    prefer_higher: Optional[dict[str, bool]] = None


class CompareScenariosResponse(BaseModel):
    """Response body for POST /api/sim/compare."""

    model_config = ConfigDict(extra="forbid")

    comparison: dict[str, Any]
    summary_a_hash: str = Field(..., min_length=64, max_length=64)
    summary_b_hash: str = Field(..., min_length=64, max_length=64)
    comparison_id: str
    was_dry_run: bool


def _resolve_scenario_for_compare(
    *,
    name: str,
    payload: Optional[dict[str, Any]],
) -> Scenario:
    """Resolve a scenario by name, falling back to payload in DRY_RUN.

    In a real DB (DSN set) this would look up the row by name; if missing,
    raises ValueError. In DRY_RUN, the persistence helper returns None for
    every name, so we must use the inline payload.
    """
    from brain.sim.persistence import get_scenario, _supabase_url_set

    record = get_scenario(name) if _supabase_url_set() else None
    if record is not None:
        return json_to_scenario(record.scenario_json)
    # DRY_RUN fallback or missing row.
    if payload is None:
        raise ValueError(
            f"scenario {name!r} not found and no payload supplied "
            "(DRY_RUN mode requires inline scenario payload)"
        )
    return json_to_scenario(payload)


def handle_compare_scenarios(
    req: CompareScenariosRequest,
    *,
    simulate_fn: Optional[Callable[[Scenario], tuple[Any, np.ndarray]]] = None,
) -> CompareScenariosResponse:
    """Simulate two scenarios and persist their comparison.

    Args:
        req: validated CompareScenariosRequest.
        simulate_fn: optional injection hook for tests. Default is
            ``brain.sim.cache.simulate_and_cache`` (memoised
            simulate-and-aggregate).

    Raises:
        ValueError: scenarios missing in production-mode lookup or
            scenarios have incompatible outcomes / horizons.
        BudgetGuardError: either scenario violates the budget guard.
        CompareError: outcome / horizon mismatch in compare_scenarios.
    """
    if simulate_fn is None:
        from brain.sim.cache import simulate_and_cache

        simulate_fn = simulate_and_cache

    scenario_a = _resolve_scenario_for_compare(
        name=req.scenario_a_name, payload=req.scenario_a_payload
    )
    scenario_b = _resolve_scenario_for_compare(
        name=req.scenario_b_name, payload=req.scenario_b_payload
    )

    check_simulation_budget(scenario_a)
    check_simulation_budget(scenario_b)

    summary_a, arr_a = simulate_fn(scenario_a)
    summary_b, arr_b = simulate_fn(scenario_b)

    prefer = (
        req.prefer_higher
        if req.prefer_higher is not None
        else default_prefer_higher_map()
    )
    comparison: ScenarioComparison = compare_scenarios(
        summary_a, summary_b, arr_a, arr_b, prefer_higher=prefer
    )

    # Persist both scenarios + comparison record (DRY_RUN sentinels OK).
    scenario_a_id = save_scenario(scenario_a, created_by="api_compare")
    scenario_b_id = save_scenario(scenario_b, created_by="api_compare")
    comparison_id = save_scenario_comparison(
        scenario_a_id=scenario_a_id,
        scenario_b_id=scenario_b_id,
        comparison=comparison,
    )

    return CompareScenariosResponse(
        comparison=comparison.model_dump(),
        summary_a_hash=summary_a.scenario_hash,
        summary_b_hash=summary_b.scenario_hash,
        comparison_id=comparison_id,
        was_dry_run=comparison_id.startswith("DRY_RUN:"),
    )


__all__ = [
    "BudgetGuardError",
    "HARD_N_SAMPLES_CAP",
    "POSTERIOR_SD_RATIO_LIMIT",
    "MIN_DIMS_PASSING_SD_GUARD",
    "check_simulation_budget",
    "SaveScenarioRequest",
    "SaveScenarioResponse",
    "handle_save_scenario",
    "ListScenariosResponse",
    "handle_list_scenarios",
    "CompareScenariosRequest",
    "CompareScenariosResponse",
    "handle_compare_scenarios",
]
