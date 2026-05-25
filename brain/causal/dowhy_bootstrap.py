"""Phase 7.2 Day 5 — DoWhy CausalModel wrapper.

Takes an SCM + observational data (DataFrame) and produces:
    1. ``dowhy.CausalModel`` instance
    2. identified estimand (backdoor / frontdoor / IV per Pearl §3.3-3.5)
    3. list of confounders DoWhy identified, cross-checkable against
       ``SCM.confounders``

Day 6-10 work in this same package (do() API, counterfactual queries,
sensitivity refutation) builds on top of these primitives.

Hard rule (from agent role §1): DAG must be acyclic before passing to
DoWhy. ``build_causal_model`` runs ``is_directed_acyclic_graph`` on
``scm.graph`` and refuses to construct on a cycle.

Reference:
    - Pearl, _Causality_ 2nd ed., 2009, §3.3 (backdoor) and §3.4 (do-calculus).
    - DoWhy ``identify_effect`` API:
      https://www.pywhy.org/dowhy/v0.11.1/user_guide/causal_tasks/estimating_causal_effects/identify_effect.html
    - Foundation smoke: ``v7_architecture/foundation_logs/smoke_dowhy.py``
      (DoWhy ATE estimate 1.4817 vs synthetic truth 1.50 — within tolerance).
"""

from __future__ import annotations

import networkx as nx
import pandas as pd
from dowhy import CausalModel

from brain.causal.scm import SCM, SCMError


# ---------------------------------------------------------------------------
# CausalModel builder
# ---------------------------------------------------------------------------
def build_causal_model(scm: SCM, data: pd.DataFrame) -> CausalModel:
    """Build a ``dowhy.CausalModel`` from an SCM + observational DataFrame.

    Args:
        scm: an :class:`~brain.causal.scm.SCM` spec with ``scm.graph`` set.
        data: pandas DataFrame whose columns include ``scm.treatment``,
            ``scm.outcome``, and every name in ``scm.confounders``.

    Raises:
        SCMError: if DataFrame is missing required columns, if ``scm.graph``
            is None, or if ``scm.graph`` is cyclic.
    """
    if scm.graph is None:
        raise SCMError("scm.graph is None; cannot build CausalModel")

    # Hard rule §1: DAG must be acyclic
    if not nx.is_directed_acyclic_graph(scm.graph):
        cycles = list(nx.simple_cycles(scm.graph))[:3]
        raise SCMError(
            f"scm.graph is not a DAG; cycles found (first 3): {cycles!r}. "
            "Refusing to build CausalModel on a cyclic graph (DoWhy will fail "
            "with an opaque error)."
        )

    required_cols = {scm.treatment, scm.outcome} | set(scm.confounders)
    missing = required_cols - set(data.columns)
    if missing:
        raise SCMError(
            f"DataFrame missing required columns: {sorted(missing)}"
        )

    graph_str = scm.to_dowhy_graph_string()
    return CausalModel(
        data=data,
        treatment=scm.treatment,
        outcome=scm.outcome,
        graph=graph_str,
    )


# ---------------------------------------------------------------------------
# Identification (cheap; no sampling)
# ---------------------------------------------------------------------------
def identify_effect(model: CausalModel) -> dict:
    """Run DoWhy identification and return a structured result.

    Returns a dict::

        {
            "estimand_type":            str,
            "backdoor_variables":       list[str],
            "instrumental_variables":   list[str],
            "frontdoor_variables":      list[str],
            "estimand_str":             str,  # full DoWhy pretty-print
        }
    """
    estimand = model.identify_effect(proceed_when_unidentifiable=True)
    return {
        "estimand_type": str(estimand.estimand_type),
        "backdoor_variables": list(estimand.get_backdoor_variables() or []),
        "instrumental_variables": list(
            estimand.get_instrumental_variables() or []
        ),
        "frontdoor_variables": list(estimand.get_frontdoor_variables() or []),
        "estimand_str": str(estimand),
    }


# ---------------------------------------------------------------------------
# Synthetic data for the reference SCM
# ---------------------------------------------------------------------------
def synthetic_data_for_reference_scm(
    n: int = 200, *, random_seed: int = 7
) -> pd.DataFrame:
    """Generate synthetic data for the reference SCM
    (Vigabatrin -> Seizure frequency).

    Used in tests to verify DoWhy identification + estimation produce
    sensible numbers. The data-generating process embeds:

        - Age (months) ~ Uniform(2, 18)
        - Neuroplasticity = exp(-0.05 * Age)
        - Vigabatrin ~ Bernoulli(sigmoid(0.5 * (Age - 10)))
            (older infants more likely to be treated — confounding)
        - GABA-T = 1 - 0.7 * Vigabatrin             (Vigabatrin inhibits)
        - Seizure frequency = 2.0
                              - 1.2 * (1 - GABA-T)  (mediator effect)
                              - 0.3 * Neuroplasticity
                              + 0.05 * Age
                              + N(0, 0.2)

    The marginal effect of Vigabatrin on Seizure frequency is negative
    (Vigabatrin reduces seizures); a naive correlation would be biased
    upward by the Age confounder.

    Args:
        n: sample size (default 200; sufficient for identification tests).
        random_seed: numpy RNG seed for reproducibility.
    """
    import numpy as np

    rng = np.random.default_rng(random_seed)

    age = rng.uniform(2, 18, size=n)
    neuroplasticity = np.exp(-age * 0.05)
    # Logistic propensity gated on age
    propensity = 1.0 / (1.0 + np.exp(-(age - 10) * 0.5))
    vigabatrin = rng.binomial(1, p=propensity, size=n).astype(float)
    gabat = 1.0 - vigabatrin * 0.7
    seizure_freq = (
        2.0
        - 1.2 * (1.0 - gabat)
        - 0.3 * neuroplasticity
        + 0.05 * age
        + rng.normal(0.0, 0.2, size=n)
    )
    seizure_freq = np.clip(seizure_freq, 0.0, None)

    return pd.DataFrame(
        {
            "Vigabatrin": vigabatrin,
            "Seizure frequency": seizure_freq,
            "Age (months)": age,
            "GABA-T enzyme": gabat,
            "Neuroplasticity window": neuroplasticity,
        }
    )


__all__ = [
    "build_causal_model",
    "identify_effect",
    "synthetic_data_for_reference_scm",
]
