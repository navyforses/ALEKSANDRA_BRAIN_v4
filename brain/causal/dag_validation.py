"""Phase 7.2 Day 3 — DAG quality report for a loaded causal graph.

Checks: acyclicity, weakly-connected components, dangling nodes (degree=0),
edge-type distribution, citation-completeness rate, dimension_ref population.

Used as a pre-flight before any DoWhy CausalModel build — if the graph
violates DAG, DoWhy will fail with an opaque error; if the graph has many
dangling nodes, DoWhy can still run but the SCM has limited estimand
coverage. This report makes the underlying issue visible before the SCM
construction step.

Reference:
    - Pearl, _Causality_ 2nd ed., 2009, §1.2 (acyclicity is a *necessary*
      condition for an SCM to admit do-calculus identification).
    - Phase 7.1 carry-forward #2: TBD-Day-7-backfill citations are tracked
      as a separate backlog metric, not folded into the completeness rate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import networkx as nx

from brain.memory.edge_taxonomy import TBD_PLACEHOLDER


# ---------------------------------------------------------------------------
# Report dataclass
# ---------------------------------------------------------------------------
@dataclass
class DAGReport:
    """Structured DAG quality summary. All fields cheap to compute."""

    node_count: int
    edge_count: int
    is_acyclic: bool
    cycle_examples: list  # first few cycles if any, each a list of node ids
    weakly_connected_components: int
    largest_wcc_size: int
    dangling_node_count: int  # nodes with total degree == 0
    dangling_node_names: list[str]
    edge_type_counts: dict[str, int]
    citation_complete_count: int
    citation_complete_rate: float
    tbd_backlog_count: int
    dimension_ref_populated_count: int
    dimension_ref_populated_rate: float


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------
def build_dag_report(graph: nx.DiGraph) -> DAGReport:
    """Compute a full DAG quality report from a loaded causal graph."""
    total_nodes = graph.number_of_nodes()
    total_edges = graph.number_of_edges()

    # Acyclicity
    is_acyclic = nx.is_directed_acyclic_graph(graph)
    cycle_examples: list = []
    if not is_acyclic:
        try:
            # simple_cycles is a generator — take at most 5
            cycle_iter = nx.simple_cycles(graph)
            for _ in range(5):
                try:
                    cycle_examples.append(next(cycle_iter))
                except StopIteration:
                    break
        except Exception:  # pragma: no cover — defensive
            cycle_examples = []

    # Connectivity (weakly-connected — treat as undirected for component check)
    wccs = list(nx.weakly_connected_components(graph)) if total_nodes else []
    wcc_count = len(wccs)
    largest_wcc = max((len(c) for c in wccs), default=0)

    # Dangling nodes — degree 0 in *both* directions
    dangling_ids = [nid for nid in graph.nodes if graph.degree(nid) == 0]
    dangling_names = [
        graph.nodes[nid].get("name") or f"<id={nid}>"
        for nid in dangling_ids[:20]
    ]

    # Edge-type distribution + citation completeness
    edge_type_counts: dict[str, int] = {}
    citation_complete = 0
    tbd_backlog = 0
    for _, _, data in graph.edges(data=True):
        et = data.get("edge_type") or "UNKNOWN"
        edge_type_counts[et] = edge_type_counts.get(et, 0) + 1
        citation = data.get("citation") or ""
        if citation == TBD_PLACEHOLDER:
            tbd_backlog += 1
        elif citation:
            citation_complete += 1

    cite_rate = citation_complete / total_edges if total_edges else 0.0

    # dimension_ref population (Phase 7.1 belief <-> causal FK)
    dim_pop = sum(
        1
        for _, attrs in graph.nodes(data=True)
        if attrs.get("dimension_ref") is not None
    )
    dim_rate = dim_pop / total_nodes if total_nodes else 0.0

    return DAGReport(
        node_count=total_nodes,
        edge_count=total_edges,
        is_acyclic=is_acyclic,
        cycle_examples=cycle_examples,
        weakly_connected_components=wcc_count,
        largest_wcc_size=largest_wcc,
        dangling_node_count=len(dangling_ids),
        dangling_node_names=dangling_names,
        edge_type_counts=edge_type_counts,
        citation_complete_count=citation_complete,
        citation_complete_rate=cite_rate,
        tbd_backlog_count=tbd_backlog,
        dimension_ref_populated_count=dim_pop,
        dimension_ref_populated_rate=dim_rate,
    )


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
def format_report(report: DAGReport) -> str:
    """Human-readable rendering for stdout / log capture."""
    lines = [
        "=== DAG Quality Report ===",
        f"Nodes:                       {report.node_count}",
        f"Edges:                       {report.edge_count}",
        f"Acyclic:                     {report.is_acyclic}",
    ]
    if not report.is_acyclic:
        lines.append(
            f"  Cycle examples (first 5):  {report.cycle_examples}"
        )
    lines += [
        f"Weakly-connected components: {report.weakly_connected_components}",
        f"  Largest WCC size:          {report.largest_wcc_size}",
        f"Dangling nodes (deg=0):      {report.dangling_node_count}",
        f"  First 20 names:            {report.dangling_node_names[:20]}",
        f"Edge-type distribution:      {report.edge_type_counts}",
        (
            f"Citation complete:           "
            f"{report.citation_complete_count} / {report.edge_count}  "
            f"({report.citation_complete_rate:.1%})"
        ),
        f"TBD-Day-7-backfill backlog:  {report.tbd_backlog_count}",
        (
            f"dimension_ref populated:     "
            f"{report.dimension_ref_populated_count} / {report.node_count}  "
            f"({report.dimension_ref_populated_rate:.1%})"
        ),
    ]
    return "\n".join(lines)


__all__ = ["DAGReport", "build_dag_report", "format_report"]
