"""Phase 7.2 — DoWhy causal-inference layer.

Reads Phase 7.1 causal graph (568 CausalNode + ~250-300 typed causal edges
from brain/memory/edge_taxonomy.py + causal_adapter.py), builds Structural
Causal Models (SCMs), and answers do() + counterfactual queries.

Days 1-5 (Foundation):
    - graph_loader.py : Neo4j / JSON-snapshot -> nx.DiGraph adapter
    - dag_validation.py : pre-flight DAG quality report
    - scm.py : SCM Pydantic spec + auto-confounder extraction + reference SCM
    - dowhy_bootstrap.py : dowhy.CausalModel wrapper + identification

Days 6-10 (do-calculus API + counterfactuals + sensitivity + belief cross-link):
    - estimators.py : typed EstimateResult wrapping DoWhy estimators
    - counterfactual.py : structural-linear counterfactual prediction
    - sensitivity.py : random_common_cause + placebo refutation reports
    - api.py : framework-agnostic do() + counterfactual request/response handlers
    - cross_link.py : causal estimate -> belief_evidence writeback

Days 11-15 (SCM editor backend + Verifier):
    - structure_learning.py : pgmpy HillClimb-BIC + PC structure learning
      + LearnedStructureReport precision / recall / F1 vs reference
    - scm_persistence.py : versioned SCM CRUD + audit log + revert,
      DRY_RUN-when-DSN-unset; persists to migration 018 tables
      (scms / scm_audit_log / causal_estimates)

Reference:
    - Pearl, _Causality_ 2nd ed., 2009.
    - DoWhy user guide: https://www.pywhy.org/dowhy/v0.11.1/user_guide/intro.html
    - v7_architecture/70_PHASES/72_PHASE_7_2_CAUSAL_LAYER_3W.md §1
"""

from brain.causal.api import (
    CounterfactualRequest,
    CounterfactualResponse,
    DoQueryRequest,
    DoQueryResponse,
    handle_counterfactual_query,
    handle_do_query,
)
from brain.causal.counterfactual import counterfactual_predict
from brain.causal.cross_link import record_causal_estimate_as_evidence
from brain.causal.estimators import (
    EstimateMethod,
    EstimateResult,
    EstimationError,
    estimate_effect,
)
from brain.causal.scm_persistence import (
    SCMAuditEntry,
    SCMRecord,
    compute_diff,
    create_scm,
    delete_scm,
    get_scm,
    graph_json_to_scm,
    list_scm_audit,
    list_scms,
    revert_scm,
    scm_to_graph_json,
    update_scm,
)
from brain.causal.sensitivity import (
    RefutationError,
    RefutationReport,
    refute_estimate,
    refute_estimate_all,
)
from brain.causal.structure_learning import (
    LearnedStructureReport,
    StructureLearningError,
    StructureLearningMethod,
    compare_structures,
    learn_from_synthetic_reference,
    learn_structure,
)

__all__ = [
    # Day 6 estimators
    "EstimateMethod",
    "EstimateResult",
    "EstimationError",
    "estimate_effect",
    # Day 9 sensitivity
    "RefutationReport",
    "RefutationError",
    "refute_estimate",
    "refute_estimate_all",
    # Day 8 counterfactual
    "counterfactual_predict",
    # Day 7 + Day 8 handlers
    "DoQueryRequest",
    "DoQueryResponse",
    "CounterfactualRequest",
    "CounterfactualResponse",
    "handle_do_query",
    "handle_counterfactual_query",
    # Day 10 belief cross-link
    "record_causal_estimate_as_evidence",
    # Day 11 structure learning
    "LearnedStructureReport",
    "StructureLearningMethod",
    "StructureLearningError",
    "learn_structure",
    "compare_structures",
    "learn_from_synthetic_reference",
    # Days 12-13 SCM persistence
    "SCMRecord",
    "SCMAuditEntry",
    "create_scm",
    "get_scm",
    "update_scm",
    "delete_scm",
    "revert_scm",
    "list_scms",
    "list_scm_audit",
    "scm_to_graph_json",
    "graph_json_to_scm",
    "compute_diff",
]
