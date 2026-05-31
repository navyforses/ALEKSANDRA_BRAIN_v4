"use client";

// viewer/app/[locale]/causal/CausalView.tsx — Phase 7.6 Client Component.
//
// Tiny stateful wrapper that holds the currently-selected node id and
// hands it to NodeDetail. Renders Network + NodeDetail side-by-side.

import { useState } from "react";

import type { CausalGraphResponse } from "@/lib/api/causal";
import Network from "./Network";
import NodeDetail from "./NodeDetail";

interface Props {
  graph: CausalGraphResponse;
  locale: "en" | "ka";
}

export default function CausalView({ graph, locale }: Props) {
  const [selectedId, setSelectedId] = useState<number | null>(
    graph.nodes[0]?.id ?? null,
  );

  return (
    <section className="grid gap-4 lg:grid-cols-[2fr_1fr]">
      <Network graph={graph} onNodeSelect={setSelectedId} />
      <NodeDetail graph={graph} selectedId={selectedId} locale={locale} />
    </section>
  );
}
