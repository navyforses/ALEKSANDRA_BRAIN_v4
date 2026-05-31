"use client";

// viewer/app/[locale]/causal/NetworkInner.tsx — Phase 7.6 inner client widget.
//
// This file holds the actual vis-network instantiation; the parent
// Network.tsx wrapper dynamic-imports it via next/dynamic so the
// vis-network code lands in a code-split chunk (NOT the main bundle).
//
// Edge color map mirrors Network.tsx documentation.

import { useEffect, useRef } from "react";
import { Network as VisNetwork } from "vis-network/standalone";
import { DataSet } from "vis-data/standalone";

import type {
  CausalEdgeType,
  CausalGraphResponse,
} from "@/lib/api/causal";

interface Props {
  graph: CausalGraphResponse;
  onNodeSelect: (nodeId: number) => void;
}

const EDGE_COLOR: Record<CausalEdgeType, string> = {
  CAUSES: "#16a34a",
  INHIBITS: "#dc2626",
  MEDIATES: "#3b82f6",
  CONFOUNDS: "#f59e0b",
  MODERATES: "#a855f7",
};

export default function NetworkInner({ graph, onNodeSelect }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const nodes = new DataSet(
      graph.nodes.map((n) => ({
        id: n.id,
        label: n.name,
        title: n.dimension_ref ?? n.name,
      })),
    );

    const edges = new DataSet(
      graph.edges.map((e, idx) => ({
        id: idx,
        from: e.source,
        to: e.target,
        color: { color: EDGE_COLOR[e.edge_type] ?? "#6b7280" },
        arrows: "to",
        title: `${e.edge_type} · ${e.mechanism ?? ""} · ${e.citation}`,
        width: 1.5,
      })),
    );

    const options = {
      physics: {
        enabled: true,
        solver: "forceAtlas2Based",
        stabilization: { iterations: 100 },
      },
      nodes: {
        shape: "dot",
        size: 16,
        font: { size: 12, color: "#1c1917" },
        color: { background: "#e7e5e4", border: "#78716c" },
      },
      edges: {
        arrows: { to: { enabled: true, scaleFactor: 0.6 } },
        smooth: { enabled: true, type: "dynamic", roundness: 0.4 },
      },
      interaction: { hover: true, tooltipDelay: 200 },
    };

    const network = new VisNetwork(
      containerRef.current,
      { nodes, edges },
      options,
    );
    network.on("selectNode", (params: { nodes: number[] }) => {
      if (params.nodes && params.nodes.length > 0) {
        onNodeSelect(params.nodes[0]);
      }
    });

    return () => {
      network.destroy();
    };
  }, [graph, onNodeSelect]);

  return (
    <div
      ref={containerRef}
      className="h-[500px] w-full rounded-md border border-stone-200 bg-white"
      aria-label="Causal graph"
    />
  );
}
