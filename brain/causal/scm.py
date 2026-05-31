"""Phase 7.2 Day 4 — Structural Causal Model specification.

Pydantic model describing one SCM — a NetworkX subgraph + treatment node
+ outcome node + confounders + optional mediators. Used as the input to
``dowhy.CausalModel()`` in Day 5 (``brain/causal/dowhy_bootstrap.py``).

Includes a ``build_scm_from_graph(graph, treatment_name, outcome_name)``
helper that auto-extracts confounders via common-ancestor heuristic; the
heuristic is *deliberately* coarse — DoWhy's own ``identify_effect()``
refines via backdoor criterion in Day 5.

Reference:
    - Pearl, _Causality_ 2nd ed., 2009, §3.3 (backdoor criterion) and
      §3.5 (frontdoor criterion). Common ancestors of (T, Y) are a
      *superset* of the backdoor-admissible adjustment set.
    - ARCHITECTURE §6.2 reference SCM pattern: Vigabatrin -> Seizure
      frequency with Age (confounder) and GABA-T (mediator).
    - PMIDs cited in build_reference_scm():
        * 7686614  : Lippa & Loftis, GABA-T inhibition mechanism (1993)
        * 32713850 : Pellock et al., infantile spasms age-of-onset (2020)
        * 19489084 : Hensch, neuroplasticity critical periods (2009)
"""

from __future__ import annotations

from typing import Optional

import networkx as nx
from pydantic import BaseModel, ConfigDict, Field

from brain.causal.graph_loader import get_node_by_name


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------
class SCMError(ValueError):
    """SCM specification or build error."""


# ---------------------------------------------------------------------------
# Pydantic SCM spec
# ---------------------------------------------------------------------------
class SCM(BaseModel):
    """One structural causal model specification.

    Attributes:
        name: short SCM identifier (snake_case recommended).
        description: human-readable purpose / scientific claim.
        treatment: name of treatment node (must exist in graph).
        outcome: name of outcome node (must exist in graph).
        confounders: candidate adjustment set (common ancestors of T & Y).
        mediators: nodes on a directed T -> Y path (excluding endpoints).
        graph: the underlying nx.DiGraph (carried alongside spec; not
            serialised since networkx graphs are not directly Pydantic-friendly).
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    treatment: str = Field(..., min_length=1)
    outcome: str = Field(..., min_length=1)
    confounders: list[str] = Field(default_factory=list)
    mediators: list[str] = Field(default_factory=list)
    # Reference to the source graph (NOT serialized; carried alongside the spec)
    graph: Optional[nx.DiGraph] = None

    def to_dowhy_graph_string(self) -> str:
        """Emit a DoWhy-compatible graph string (DOT-like format).

        DoWhy's parser uses the regex ``.*graph\\s*\\{.*\\}\\s*`` to detect
        an inline DOT string, which *requires no graph identifier between
        ``digraph`` and ``{``*. We therefore emit::

            digraph { "treatment" -> "outcome"; "confounder" -> "treatment"; ... }

        Node *names* (not internal ids) are used because the user-supplied
        DataFrame columns in ``CausalModel(data=...)`` must align with the
        node names in the graph string.
        """
        if self.graph is None:
            raise SCMError(
                "SCM.graph is None; cannot emit DoWhy string without underlying graph"
            )
        edges = []
        for u, v, _ in self.graph.edges(data=True):
            u_name = self.graph.nodes[u].get("name", str(u))
            v_name = self.graph.nodes[v].get("name", str(v))
            edges.append(f'"{u_name}" -> "{v_name}";')
        return "digraph { " + " ".join(edges) + " }"


# ---------------------------------------------------------------------------
# Auto-builder from a graph
# ---------------------------------------------------------------------------
def build_scm_from_graph(
    graph: nx.DiGraph,
    *,
    treatment_name: str,
    outcome_name: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> SCM:
    """Auto-build an SCM from a NetworkX DiGraph by extracting confounders.

    Confounder heuristic: any node Z that is a *common ancestor* of both
    treatment and outcome is a candidate confounder. This is a *superset*
    of the backdoor-admissible set; DoWhy's ``identify_effect()`` refines
    the actual adjustment set per Pearl §3.3.

    Mediator extraction: any node M on a directed simple path
    treatment -> ... -> M -> ... -> outcome (excluding endpoints) up to
    length 4. Cap chosen to keep the search tractable on the 568-node
    Phase 7.1 graph.

    Args:
        graph: source NetworkX DiGraph (from ``brain.causal.graph_loader``).
        treatment_name: case-insensitive node name for treatment.
        outcome_name: case-insensitive node name for outcome.
        name: optional SCM identifier; defaults to ``"{treatment}_to_{outcome}"``.
        description: optional human description.

    Raises:
        SCMError: if treatment or outcome node not found in graph.
    """
    treatment_id = get_node_by_name(graph, treatment_name)
    outcome_id = get_node_by_name(graph, outcome_name)
    if treatment_id is None:
        raise SCMError(f"treatment node {treatment_name!r} not in graph")
    if outcome_id is None:
        raise SCMError(f"outcome node {outcome_name!r} not in graph")

    # Confounders: common ancestors of (T, Y), excluding T itself
    treat_ancestors = nx.ancestors(graph, treatment_id)
    outcome_ancestors = nx.ancestors(graph, outcome_id)
    candidate_confounders = treat_ancestors & outcome_ancestors
    candidate_confounders.discard(treatment_id)
    confounder_names = sorted(
        graph.nodes[c].get("name", str(c)) for c in candidate_confounders
    )

    # Mediators: nodes on directed simple paths T -> Y (excluding endpoints)
    mediators_set: set = set()
    try:
        for path in nx.all_simple_paths(graph, treatment_id, outcome_id, cutoff=4):
            mediators_set.update(path[1:-1])
    except nx.NodeNotFound:  # pragma: no cover — endpoints already validated
        pass
    mediator_names = sorted(
        graph.nodes[m].get("name", str(m)) for m in mediators_set
    )

    return SCM(
        name=name or f"{treatment_name}_to_{outcome_name}",
        description=description,
        treatment=treatment_name,
        outcome=outcome_name,
        confounders=confounder_names,
        mediators=mediator_names,
        graph=graph,
    )


# ---------------------------------------------------------------------------
# Reference SCM (PHI-free)
# ---------------------------------------------------------------------------
def build_reference_scm() -> SCM:
    """Synthetic reference SCM for testing without live Neo4j.

    Pattern from ARCHITECTURE §6.2:
        Vigabatrin --INHIBITS--> GABA-T --CAUSES--> Seizure frequency
        Age --CAUSES--> Vigabatrin
        Age --CAUSES--> Seizure frequency           (confounding)
        Age --CAUSES--> Neuroplasticity window --CAUSES--> Seizure frequency

    Citations attached to every edge so the SCM is *citation-complete*
    (would pass ``is_citation_complete()`` filter at write-time).
    """
    graph = nx.DiGraph()
    nodes = {
        1: "Vigabatrin",
        2: "Seizure frequency",
        3: "Age (months)",
        4: "GABA-T enzyme",
        5: "Neuroplasticity window",
    }
    for nid, node_name in nodes.items():
        graph.add_node(
            nid, name=node_name, dimension_ref=None, labels=["CausalNode"]
        )

    edges = [
        (1, 4, "INHIBITS", "PMID:7686614", "irreversible GABA-T inhibition"),
        (4, 2, "CAUSES",   "PMID:7686614", "GABA inhibition reduces hyperexcitability"),
        (3, 1, "CAUSES",   "PMID:32713850", "age gates treatment eligibility"),
        (3, 2, "CAUSES",   "PMID:32713850", "age-related seizure phenotype"),
        (3, 5, "CAUSES",   "PMID:19489084", "neuroplasticity opens at birth"),
        (5, 2, "CAUSES",   "PMID:19489084", "plasticity moderates seizure recovery"),
    ]
    for src, tgt, et, cite, mech in edges:
        graph.add_edge(
            src,
            tgt,
            edge_type=et,
            confidence=0.85,
            citation=cite,
            mechanism=mech,
            time_lag_days=None,
        )

    return build_scm_from_graph(
        graph,
        treatment_name="Vigabatrin",
        outcome_name="Seizure frequency",
        name="reference_vigabatrin_seizure",
        description=(
            "Synthetic reference SCM (Vigabatrin -> Seizure frequency) "
            "per ARCHITECTURE §6.2. PHI-free."
        ),
    )


__all__ = ["SCM", "SCMError", "build_reference_scm", "build_scm_from_graph"]
