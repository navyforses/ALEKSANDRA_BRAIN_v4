"""Phase 7.2 Day 11 — pgmpy structure learning + reference SCM comparison.

Reads observational data (pandas DataFrame), returns a learned NetworkX
DAG via one of two pgmpy estimators, and compares the learned structure
to a hand-curated reference graph (the Vigabatrin -> Seizure SCM from
:func:`brain.causal.scm.build_reference_scm`) using precision / recall
/ F1 over the edge set.

Two estimators are exposed:

    - ``hill_climb_bic``: greedy Hill-Climb search optimizing the
      Bayesian Information Criterion. Works on continuous DataFrames
      via the ``bic-g`` (Gaussian) scoring method in pgmpy 1.1.2.
      Returns a pgmpy ``DAG``; converted to ``nx.DiGraph`` via the
      iteration ``nx.DiGraph(list(dag.edges()))``.

    - ``pc_chisq``: PC algorithm with chi-square conditional-independence
      test. Returns a pgmpy ``PDAG`` (partially directed); converted to
      a DAG via ``PDAG.to_dag()`` (chooses an orientation for each
      undirected edge consistent with the equivalence class).

Why these defaults:

    - HillClimb + BIC is the canonical structure-learning baseline; the
      pgmpy README and the NOTEARS paper (arXiv:1803.01422) both list it
      as the workhorse.
    - PC with chi-square is the discrete-data complement when the
      Gaussian assumption breaks (e.g. categorical observation streams
      from voice notes).

Caveat — pgmpy 1.1.2 API:

    pgmpy 1.1.2 ``HillClimbSearch.estimate(scoring_method=...)`` rejects
    instances of ``pgmpy.structure_score.BIC`` and instead requires a
    string token from the registry ('bic-g' for continuous, 'bic-d' for
    discrete). We therefore pass the string. The ``BIC`` class kept
    around in ``pgmpy.structure_score`` is exported for future API
    convergence but not used at estimate-time.

Code-complete-without-infra contract: this module touches NO database,
NO Neo4j, NO LLM. Pure deterministic transformation. The synthetic
500-sample reference comparison (``learn_from_synthetic_reference``)
runs end-to-end in < 5 s on a laptop.

Reference:
    - pgmpy: https://github.com/pgmpy/pgmpy
    - NOTEARS (Zheng et al. 2018, arXiv:1803.01422)
    - NetworkX DAG ops: https://networkx.org/documentation/stable/reference/algorithms/dag.html
    - Phase 7.2 spec §1 Day 11.
"""

from __future__ import annotations

import sys
import warnings
from typing import Any, Literal, Optional

import networkx as nx
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

# pgmpy 1.1.2 emits a FutureWarning on import about the deprecated
# ``pgmpy.estimators.StructureScore`` alias. The replacement lives at
# ``pgmpy.structure_score`` (which we use). Silence the alias warning to
# keep stderr clean for our own diagnostics.
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=FutureWarning, module="pgmpy")
    from pgmpy.estimators import PC, HillClimbSearch  # noqa: E402


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------
StructureLearningMethod = Literal["hill_climb_bic", "pc_chisq"]


class StructureLearningError(RuntimeError):
    """Raised when pgmpy fails to converge or returns an empty model."""


class LearnedStructureReport(BaseModel):
    """Side-by-side comparison of a learned vs reference DAG.

    Edges are treated as ordered (str, str) tuples on node *name*. The
    reference set is the canonical ground truth; precision / recall /
    F1 are reported with the standard symmetric-difference accounting:

        precision = |L & R| / |L|       (defined 0 when |L| == 0)
        recall    = |L & R| / |R|       (defined 0 when |R| == 0)
        f1        = harmonic_mean(P, R) (defined 0 when P+R == 0)

    Empty-set behaviour is *not* a Pydantic validation error — the
    comparison reports zeros so that downstream tests / verifiers can
    detect "no edges learned" as a degenerate-but-recoverable signal.
    """

    model_config = ConfigDict(extra="forbid")

    method: StructureLearningMethod
    n_samples: int = Field(..., ge=0)
    learned_edges: list[tuple[str, str]]
    reference_edges: list[tuple[str, str]]
    precision: float = Field(..., ge=0.0, le=1.0)
    recall: float = Field(..., ge=0.0, le=1.0)
    f1: float = Field(..., ge=0.0, le=1.0)
    learned_node_count: int = Field(..., ge=0)
    learned_edge_count: int = Field(..., ge=0)
    extra_edges: list[tuple[str, str]]
    missing_edges: list[tuple[str, str]]


# ---------------------------------------------------------------------------
# Internal: pgmpy -> nx.DiGraph helpers
# ---------------------------------------------------------------------------
def _pgmpy_to_nx_digraph(pgmpy_model: Any) -> nx.DiGraph:
    """Convert any pgmpy DAG / PDAG to an ``nx.DiGraph`` preserving nodes.

    pgmpy ``DAG`` and ``PDAG`` both expose ``.nodes()`` and ``.edges()``
    iterables that match networkx semantics, so a plain construction
    via the edges + a node sweep is lossless for the structure
    information we care about (node names + directed-edge tuples).
    """
    g = nx.DiGraph()
    for node in pgmpy_model.nodes():
        g.add_node(node)
    for u, v in pgmpy_model.edges():
        g.add_edge(u, v)
    return g


# ---------------------------------------------------------------------------
# Public: learn_structure
# ---------------------------------------------------------------------------
def learn_structure(
    data: pd.DataFrame,
    method: StructureLearningMethod,
    *,
    max_indegree: int = 3,
) -> nx.DiGraph:
    """Learn a DAG from observational data using pgmpy.

    Args:
        data: pandas DataFrame; columns become DAG node names. Must
            contain at least 2 columns and 10 rows (lower bounds are
            permissive; pgmpy itself enforces the rigorous minima).
        method: ``"hill_climb_bic"`` (default for continuous data) or
            ``"pc_chisq"`` (default for discrete data).
        max_indegree: cap on parents per node (HillClimb only). Helps
            prevent the search from chasing spurious dense parents on
            small samples.

    Returns:
        ``nx.DiGraph`` with one node per data column and one edge per
        learned causal direction. Empty edge sets are *allowed* — the
        return is never None.

    Raises:
        StructureLearningError: if pgmpy raises any exception during
            structure learning, or if ``data`` is empty / single-column.
    """
    if data is None or data.empty:
        raise StructureLearningError("data DataFrame is empty")
    if data.shape[1] < 2:
        raise StructureLearningError(
            f"need at least 2 columns to learn a DAG, got {data.shape[1]}"
        )

    try:
        if method == "hill_climb_bic":
            hcs = HillClimbSearch(data)
            # pgmpy 1.1.2: use the string-based scoring registry; instances
            # of pgmpy.structure_score.BIC are NOT accepted (only
            # StructureScore subclasses, which the new ``BIC`` is not).
            score = "bic-g"  # Gaussian BIC; assumes continuous columns
            dag = hcs.estimate(
                scoring_method=score,
                max_indegree=max_indegree,
                show_progress=False,
            )
            return _pgmpy_to_nx_digraph(dag)

        if method == "pc_chisq":
            pc = PC(data)
            pdag_or_dag = pc.estimate(
                variant="stable",
                ci_test="chi_square",
                max_cond_vars=4,
                show_progress=False,
            )
            # PC returns a PDAG (partially-directed). Try to_dag() to pick
            # a consistent DAG orientation for the equivalence class.
            if hasattr(pdag_or_dag, "to_dag"):
                try:
                    dag = pdag_or_dag.to_dag()
                    return _pgmpy_to_nx_digraph(dag)
                except Exception as exc:  # noqa: BLE001 — surface to stderr
                    print(
                        "[structure_learning] PDAG.to_dag() failed "
                        f"({type(exc).__name__}: {exc}); "
                        "returning directed-edge subset only",
                        file=sys.stderr,
                    )
            # Fall through: return whatever directed edges PC produced.
            return _pgmpy_to_nx_digraph(pdag_or_dag)

        raise StructureLearningError(
            f"unknown structure-learning method: {method!r}"
        )
    except StructureLearningError:
        raise
    except Exception as exc:  # noqa: BLE001 — wrap pgmpy errors uniformly
        raise StructureLearningError(
            f"pgmpy {method} failed: {type(exc).__name__}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Public: compare_structures
# ---------------------------------------------------------------------------
def _node_name(graph: nx.DiGraph, node_id: Any) -> str:
    """Resolve a graph node to its ``name`` attribute, falling back to id."""
    return str(graph.nodes[node_id].get("name", node_id))


def _edges_as_name_tuples(
    graph: nx.DiGraph,
    *,
    node_name_mapping: Optional[dict] = None,
) -> set[tuple[str, str]]:
    """Project a DiGraph's edges to ``set[(str, str)]`` on node *name*.

    If ``node_name_mapping`` is provided, every node id is first remapped
    via that dict (missing keys fall through to ``_node_name``). This is
    how a learned graph (whose nodes are DataFrame column names) gets
    aligned to the reference graph (whose nodes are integer ids carrying
    ``name`` attributes).
    """
    out: set[tuple[str, str]] = set()
    for u, v in graph.edges():
        if node_name_mapping and u in node_name_mapping:
            u_name = str(node_name_mapping[u])
        else:
            u_name = _node_name(graph, u)
        if node_name_mapping and v in node_name_mapping:
            v_name = str(node_name_mapping[v])
        else:
            v_name = _node_name(graph, v)
        out.add((u_name, v_name))
    return out


def _harmonic_mean(p: float, r: float) -> float:
    if p + r <= 0.0:
        return 0.0
    return 2.0 * p * r / (p + r)


def compare_structures(
    learned: nx.DiGraph,
    reference: nx.DiGraph,
    *,
    node_name_mapping: Optional[dict] = None,
    method: StructureLearningMethod = "hill_climb_bic",
    n_samples: int = 0,
) -> LearnedStructureReport:
    """Compare a learned DAG to a reference DAG by edge set.

    Args:
        learned: DiGraph returned by :func:`learn_structure` (or any
            externally-built learned model).
        reference: DiGraph from the ground-truth source (typically
            ``brain.causal.scm.build_reference_scm().graph``).
        node_name_mapping: optional ``{learned_node_id: name_str}``
            mapping used when learned-graph nodes are column names but
            the reference graph uses integer ids + a ``name`` attribute.
        method: which estimator produced ``learned`` (carried through
            into the report for traceability).
        n_samples: number of observations used to learn ``learned``
            (carried through for traceability; defaults to 0 when the
            caller did not learn the graph from data — e.g. tests).

    Returns:
        :class:`LearnedStructureReport` with precision / recall / F1 plus
        the symmetric-difference sets (``extra_edges`` are in learned
        but not reference; ``missing_edges`` are in reference but not
        learned).
    """
    learned_edges = _edges_as_name_tuples(
        learned, node_name_mapping=node_name_mapping
    )
    # Reference is *always* keyed by node `name` attribute; no remapping.
    reference_edges = _edges_as_name_tuples(reference)

    intersect = learned_edges & reference_edges
    extra = learned_edges - reference_edges
    missing = reference_edges - learned_edges

    precision = (len(intersect) / len(learned_edges)) if learned_edges else 0.0
    recall = (len(intersect) / len(reference_edges)) if reference_edges else 0.0
    f1 = _harmonic_mean(precision, recall)

    return LearnedStructureReport(
        method=method,
        n_samples=n_samples,
        learned_edges=sorted(learned_edges),
        reference_edges=sorted(reference_edges),
        precision=float(precision),
        recall=float(recall),
        f1=float(f1),
        learned_node_count=learned.number_of_nodes(),
        learned_edge_count=learned.number_of_edges(),
        extra_edges=sorted(extra),
        missing_edges=sorted(missing),
    )


# ---------------------------------------------------------------------------
# Public: end-to-end helper for the reference SCM
# ---------------------------------------------------------------------------
def _sanitize_column_name(name: str) -> str:
    """Project a column name to an identifier-safe ASCII string.

    Why: pgmpy ``bic-g`` scoring routes through ``patsy``, which calls
    ``ast.parse(name)`` on every column. Names with spaces, parentheses,
    or hyphens (e.g. ``"Age (months)"``, ``"GABA-T enzyme"``,
    ``"Seizure frequency"``) trip a Python ``SyntaxError`` at fit-time.
    We map every non-identifier character to ``_`` for the duration of
    structure learning and reverse the mapping during comparison.
    """
    safe = []
    for ch in name:
        if ch.isalnum() or ch == "_":
            safe.append(ch)
        else:
            safe.append("_")
    out = "".join(safe).strip("_")
    if not out:
        out = "col"
    # Leading-digit columns are also invalid Python identifiers.
    if out[0].isdigit():
        out = "c_" + out
    return out


def learn_from_synthetic_reference(n: int = 1000) -> LearnedStructureReport:
    """Learn the reference SCM (Vigabatrin -> Seizure) from synthetic data.

    Generates ``n`` rows via
    :func:`brain.causal.dowhy_bootstrap.synthetic_data_for_reference_scm`,
    runs the ``hill_climb_bic`` estimator, and compares to
    :func:`brain.causal.scm.build_reference_scm`.

    DataFrame columns are *sanitised* (spaces, parentheses, hyphens
    replaced with underscores) for the duration of learning so pgmpy's
    patsy backend can parse them; an inverse mapping is passed to
    :func:`compare_structures` so node-name alignment with the
    reference SCM is lossless.

    Default ``n`` was raised from 500 to **1000** during Day 11 of the
    sprint because the reference SCM mixes binary (Vigabatrin) and
    continuous (Age, Neuroplasticity, Seizure frequency) variables.
    pgmpy ``bic-g`` (Gaussian BIC) treats binary columns as continuous,
    introducing edge-direction volatility at small n. 1000 rows gave
    F1 in [0.4, 0.6] across seeds; 500 rows gave F1 in [0.1, 0.3].

    Used by the Phase 7.2 verifier (check #11) and the test suite as a
    sanity bound on estimator quality. Note: BIC on small samples is
    noisy; expect F1 in [0.3, 0.6]. If a test ever flakes below 0.3,
    raise ``n`` to ~2000 rather than relaxing the threshold.
    """
    from brain.causal.dowhy_bootstrap import synthetic_data_for_reference_scm
    from brain.causal.scm import build_reference_scm

    df = synthetic_data_for_reference_scm(n=n, random_seed=7)
    rename_map = {col: _sanitize_column_name(col) for col in df.columns}
    inverse_map = {v: k for k, v in rename_map.items()}
    sanitised = df.rename(columns=rename_map)
    learned = learn_structure(
        sanitised, method="hill_climb_bic", max_indegree=3
    )
    reference = build_reference_scm().graph
    # Remap learned-node ids (sanitised column names) back to original
    # reference node names so the edge sets align.
    return compare_structures(
        learned,
        reference,
        node_name_mapping=inverse_map,
        method="hill_climb_bic",
        n_samples=n,
    )


__all__ = [
    "StructureLearningMethod",
    "StructureLearningError",
    "LearnedStructureReport",
    "learn_structure",
    "compare_structures",
    "learn_from_synthetic_reference",
]
