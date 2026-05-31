"""Phase 7.2 Day 8 — Counterfactual prediction via structural linear extrapolation.

Answers questions of the form::

    given that we *observed* {Vigabatrin=0, Age=10, ...},
    what would Y have been if we had *intervened* and set Vigabatrin=1?

DoWhy 0.14's high-level ``CausalModel`` does not expose a true E[Y_x | X=x]
counterfactual API for arbitrary SCMs (its ``GCM`` submodule does, but
requires a fitted SCM with explicit noise models — out of scope for the
Phase 7.2 deterministic deliverable). We therefore implement a deliberately
simple structural-linear extrapolation:

    1. Fit a linear regression  Y ~ parents(Y)  on the observational data.
    2. Build the post-intervention parent vector by overlaying the
       ``intervention`` dict onto the ``factual`` dict.
    3. Predict Y from the fitted regression.

The method is honest about its assumption (linear additive noise on the
outcome's parents) — the return payload tags the method
``"structural_linear_extrapolation"`` so callers know not to mistake
this for a full SCM counterfactual.

Hard rule (from agent role §1): DAG must be acyclic; the SCM check
is rerun here so this module is safe to import standalone.

Reference:
    - Pearl, _Causality_ 2nd ed., 2009, §7 (counterfactuals).
    - DoWhy gcm.counterfactual_samples API:
      https://www.pywhy.org/dowhy/v0.11.1/user_guide/causal_tasks/quantify_causal_influence/counterfactuals.html
    - Phase 7.2 spec §1 Day 8 + §2.3 API contract.
"""

from __future__ import annotations

from typing import Any

import math
import networkx as nx
import numpy as np
import pandas as pd

from brain.causal.scm import SCM, SCMError


# ---------------------------------------------------------------------------
# Internal — find a node id by visible name
# ---------------------------------------------------------------------------
def _names_in_graph(graph: nx.DiGraph) -> set[str]:
    return {
        graph.nodes[n].get("name", str(n))
        for n in graph.nodes
    }


def _node_id_for_name(graph: nx.DiGraph, name: str) -> Any:
    for nid in graph.nodes:
        if graph.nodes[nid].get("name") == name:
            return nid
    return None


def _parents_of_outcome(scm: SCM) -> list[str]:
    """Return the visible names of every direct parent of the outcome node."""
    assert scm.graph is not None
    outcome_id = _node_id_for_name(scm.graph, scm.outcome)
    if outcome_id is None:
        raise SCMError(f"outcome {scm.outcome!r} not in scm.graph nodes")
    return [
        scm.graph.nodes[p].get("name", str(p))
        for p in scm.graph.predecessors(outcome_id)
    ]


# ---------------------------------------------------------------------------
# Public counterfactual API
# ---------------------------------------------------------------------------
def counterfactual_predict(
    scm: SCM,
    *,
    factual: dict[str, float],
    intervention: dict[str, float],
    outcome: str,
    data: pd.DataFrame,
) -> dict:
    """Predict the counterfactual outcome under a do(...) intervention.

    Args:
        scm: an :class:`~brain.causal.scm.SCM` with ``graph`` set.
        factual: dict of {variable_name -> observed_value} forming the
            "what actually happened" anchor row. May supply any subset of
            variables — only those used as outcome parents matter.
        intervention: dict of {variable_name -> do_value}. MUST be
            non-empty. Variables here override their ``factual`` value
            when computing the post-intervention parent vector.
        outcome: outcome variable name; MUST equal ``scm.outcome``.
        data: observational DataFrame used to fit the linear surrogate
            equation Y ~ parents(Y). MUST contain ``outcome`` and every
            parent column.

    Returns:
        ``{"predicted_outcome": float,
           "delta_vs_factual": float,
           "method": "structural_linear_extrapolation"}``

        ``delta_vs_factual`` is ``predicted_outcome - factual[outcome]``
        if ``outcome`` was supplied in ``factual``; otherwise the factual
        outcome is taken to be the mean of the surrogate prediction on
        the raw factual parent vector (no intervention).

    Raises:
        ValueError: empty intervention, or unknown variable in either
            ``factual`` or ``intervention``, or ``outcome`` != ``scm.outcome``.
        SCMError: cyclic ``scm.graph`` or missing graph / outcome.
    """
    if scm.graph is None:
        raise SCMError("scm.graph is None; cannot run counterfactual")

    # Hard rule §1 — DAG check
    if not nx.is_directed_acyclic_graph(scm.graph):
        raise SCMError(
            "scm.graph is not a DAG; refusing to run counterfactual."
        )

    if outcome != scm.outcome:
        raise ValueError(
            f"outcome {outcome!r} does not match scm.outcome {scm.outcome!r}"
        )

    if not intervention:
        raise ValueError("intervention dict must be non-empty")

    valid_names = _names_in_graph(scm.graph)
    for v in intervention:
        if v not in valid_names:
            raise ValueError(
                f"intervention variable {v!r} is not a node in scm.graph; "
                f"known nodes: {sorted(valid_names)}"
            )
    for v in factual:
        if v not in valid_names:
            raise ValueError(
                f"factual variable {v!r} is not a node in scm.graph; "
                f"known nodes: {sorted(valid_names)}"
            )

    # ------------------------------------------------------------------
    # Fit Y ~ parents(Y) by closed-form OLS via numpy
    # ------------------------------------------------------------------
    parent_names = _parents_of_outcome(scm)
    if not parent_names:
        raise SCMError(
            f"outcome {outcome!r} has no parents in scm.graph; "
            "counterfactual is undefined."
        )

    required_cols = set(parent_names) | {outcome}
    missing = required_cols - set(data.columns)
    if missing:
        raise SCMError(
            f"data missing required columns for counterfactual: {sorted(missing)}"
        )

    # Design matrix X (intercept + parents), target y
    X = data[parent_names].to_numpy(dtype=float)
    n_rows = X.shape[0]
    X_aug = np.hstack([np.ones((n_rows, 1)), X])
    y = data[outcome].to_numpy(dtype=float)

    # OLS via lstsq — numerically stable, no statsmodels dep here
    coefs, *_ = np.linalg.lstsq(X_aug, y, rcond=None)
    intercept = float(coefs[0])
    slopes = {name: float(coefs[i + 1]) for i, name in enumerate(parent_names)}

    # ------------------------------------------------------------------
    # Build the post-intervention parent vector
    # ------------------------------------------------------------------
    # Start from factual values; if a parent is missing from factual,
    # fall back to the empirical mean from `data`.
    post_intervention: dict[str, float] = {}
    for p in parent_names:
        if p in intervention:
            post_intervention[p] = float(intervention[p])
        elif p in factual:
            post_intervention[p] = float(factual[p])
        else:
            post_intervention[p] = float(data[p].mean())

    # Predict
    predicted = intercept + sum(
        slopes[p] * post_intervention[p] for p in parent_names
    )

    # Delta vs the factual outcome value if provided
    if outcome in factual:
        factual_y = float(factual[outcome])
    else:
        # Use the surrogate prediction on the raw (un-intervened) parent vector
        raw_pi = {
            p: float(factual.get(p, data[p].mean()))
            for p in parent_names
        }
        factual_y = intercept + sum(slopes[p] * raw_pi[p] for p in parent_names)

    delta = predicted - factual_y

    # Guard against runaway extrapolations producing NaN / inf
    if not math.isfinite(predicted) or not math.isfinite(delta):
        raise SCMError(
            "counterfactual prediction produced non-finite value; "
            "check the observational data + intervention scale."
        )

    return {
        "predicted_outcome": round(float(predicted), 6),
        "delta_vs_factual": round(float(delta), 6),
        "method": "structural_linear_extrapolation",
    }


__all__ = ["counterfactual_predict"]
