"""Phase 7.3 Layers A + C — Monte Carlo simulation engine + Simulation Studio.

Layer A scope (Days 1-5):
    - scenario.py     : Pydantic Scenario + Intervention + canonical hash
    - trajectory.py   : Direct-numpy Monte Carlo trajectory generator
    - aggregator.py   : 3-D ndarray -> ScenarioSummary (mean / sd / HDI 80 / HDI 95)
    - compare.py      : Two-scenario delta + P(A better) + interpretation
    - cache.py        : In-process LRU cache for (summary, array) pairs

Layer B (Days 6-10) — TheVirtualBrain Docker neural-mass simulation —
is deferred to a separate dispatch (``brain/sim/tvb_adapter.py`` not
in this package). Verifier checks 7/8/9 SKIP until Layer B lands.

Layer C scope (Days 11-15):
    - persistence.py  : CRUD on scenarios / simulation_runs / comparisons (DRY_RUN fallback)
    - api.py          : framework-agnostic save/list/compare handlers + budget guard
    - viz.py          : matplotlib PNG histogram export (Plotly substituted)
    - migration 019   : 3 new Supabase tables (additive, RLS-enabled)
    - verifier        : scripts/verify_phase_7_3.py 13 checks

Reference:
    - v7_architecture/70_PHASES/73_PHASE_7_3_SIMULATION_ENGINE_3W.md
"""

from brain.sim.aggregator import (
    OutcomeSummary,
    ScenarioSummary,
    aggregate_trajectories,
    summary_to_dataframe,
)
from brain.sim.api import (
    BudgetGuardError,
    CompareScenariosRequest,
    CompareScenariosResponse,
    HARD_N_SAMPLES_CAP,
    ListScenariosResponse,
    MIN_DIMS_PASSING_SD_GUARD,
    POSTERIOR_SD_RATIO_LIMIT,
    SaveScenarioRequest,
    SaveScenarioResponse,
    check_simulation_budget,
    handle_compare_scenarios,
    handle_list_scenarios,
    handle_save_scenario,
)
from brain.sim.cache import (
    ScenarioCache,
    cache_stats,
    clear_cache,
    get_cached,
    put_cached,
    simulate_and_cache,
)
from brain.sim.compare import (
    CompareError,
    InterpretationLiteral,
    OutcomeDelta,
    ScenarioComparison,
    compare_scenarios,
    default_prefer_higher_map,
)
from brain.sim.persistence import (
    ALLOWED_ENGINES,
    EngineLiteral,
    ScenarioComparisonRecord,
    ScenarioRecord,
    SimulationRunRecord,
    delete_scenario,
    get_scenario,
    get_scenario_by_hash,
    json_to_scenario,
    list_scenarios,
    save_scenario,
    save_scenario_comparison,
    save_simulation_run,
    scenario_to_json,
)
from brain.sim.scenario import (
    FrequencyLiteral,
    Intervention,
    InterventionType,
    Scenario,
    build_reference_scenario,
    compute_scenario_hash,
)
from brain.sim.trajectory import (
    VIGABATRIN_GABA_T_FACTOR,
    VIGABATRIN_INTERVENTION_NAME,
    VIGABATRIN_MEDIATOR_COEFFICIENT,
    VIGABATRIN_TARGET_DIM,
    Trajectory,
    simulate_scenario,
    simulate_trajectory,
)
from brain.sim.viz import (
    DEFAULT_SNAPSHOT_DIR,
    FIG_DPI,
    FIG_SIZE,
    HIST_BINS,
    MIN_PNG_BYTES,
    render_comparison_panel,
    render_scenario_histogram,
    render_scenario_summary_panel,
)

__all__ = [
    # scenario
    "Intervention",
    "InterventionType",
    "FrequencyLiteral",
    "Scenario",
    "compute_scenario_hash",
    "build_reference_scenario",
    # trajectory
    "Trajectory",
    "simulate_trajectory",
    "simulate_scenario",
    "VIGABATRIN_MEDIATOR_COEFFICIENT",
    "VIGABATRIN_GABA_T_FACTOR",
    "VIGABATRIN_TARGET_DIM",
    "VIGABATRIN_INTERVENTION_NAME",
    # aggregator
    "OutcomeSummary",
    "ScenarioSummary",
    "aggregate_trajectories",
    "summary_to_dataframe",
    # compare
    "CompareError",
    "OutcomeDelta",
    "ScenarioComparison",
    "InterpretationLiteral",
    "default_prefer_higher_map",
    "compare_scenarios",
    # cache
    "ScenarioCache",
    "get_cached",
    "put_cached",
    "cache_stats",
    "clear_cache",
    "simulate_and_cache",
    # persistence (Layer C)
    "ALLOWED_ENGINES",
    "EngineLiteral",
    "ScenarioRecord",
    "SimulationRunRecord",
    "ScenarioComparisonRecord",
    "scenario_to_json",
    "json_to_scenario",
    "save_scenario",
    "get_scenario",
    "get_scenario_by_hash",
    "list_scenarios",
    "delete_scenario",
    "save_simulation_run",
    "save_scenario_comparison",
    # api (Layer C)
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
    # viz (Layer C)
    "DEFAULT_SNAPSHOT_DIR",
    "FIG_DPI",
    "FIG_SIZE",
    "HIST_BINS",
    "MIN_PNG_BYTES",
    "render_scenario_histogram",
    "render_scenario_summary_panel",
    "render_comparison_panel",
]
