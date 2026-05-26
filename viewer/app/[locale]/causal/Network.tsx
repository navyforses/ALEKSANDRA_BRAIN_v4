"use client";

// viewer/app/[locale]/causal/Network.tsx — Phase 7.6 Client Component.
//
// Dynamic-import wrapper for NetworkInner. vis-network/standalone is loaded
// only when this component mounts on the client, keeping the heavy bundle
// out of SSR + out of the main client chunk. Pattern matches the Plotly
// usage in DimensionCard.tsx / Timeline.tsx.

import dynamic from "next/dynamic";

import type { CausalGraphResponse } from "@/lib/api/causal";

const NetworkInner = dynamic(
  () => import("vis-network/standalone").then(async () => {
    // Pre-warm the vis-data chunk in parallel with vis-network so the inner
    // widget mounts without a second waterfall.
    await import("vis-data/standalone");
    const mod = await import("./NetworkInner");
    return mod.default;
  }),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[500px] w-full items-center justify-center rounded-md border border-stone-200 bg-white text-sm text-stone-400">
        ...
      </div>
    ),
  },
);

interface Props {
  graph: CausalGraphResponse;
  onNodeSelect: (nodeId: number) => void;
}

export default function Network({ graph, onNodeSelect }: Props) {
  return <NetworkInner graph={graph} onNodeSelect={onNodeSelect} />;
}
