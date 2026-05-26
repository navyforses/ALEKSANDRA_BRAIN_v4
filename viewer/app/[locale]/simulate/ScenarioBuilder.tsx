"use client";

// viewer/app/[locale]/simulate/ScenarioBuilder.tsx — Phase 7.6 Client wrapper.
//
// react-flow drag-and-drop scenario canvas with palette + validation +
// submit button. The heavy @xyflow/react bundle is dynamic-imported via
// next/dynamic so it lands in a code-split chunk; the inner widget that
// owns the actual ReactFlow JSX lives in ScenarioBuilderInner.tsx.
//
// Validation:
//   - n_samples 10 .. 10000
//   - horizon_days 1 .. 2000
//   - at least 1 intervention node

import dynamic from "next/dynamic";

import type { Scenario } from "@/lib/api/sim";

const Inner = dynamic(() => import("./ScenarioBuilderInner"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[420px] w-full items-center justify-center rounded-md border border-stone-200 bg-white text-sm text-stone-400">
      ...
    </div>
  ),
});

interface Props {
  onSubmit: (scenario: Scenario) => void;
  busy?: boolean;
}

export default function ScenarioBuilder({ onSubmit, busy }: Props) {
  return <Inner onSubmit={onSubmit} busy={!!busy} />;
}
