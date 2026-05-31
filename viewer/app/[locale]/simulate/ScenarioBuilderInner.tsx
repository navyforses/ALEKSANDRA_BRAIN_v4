"use client";

// viewer/app/[locale]/simulate/ScenarioBuilderInner.tsx — Phase 7.6.
//
// The actual ReactFlow canvas. Code-split via ScenarioBuilder.tsx's
// next/dynamic wrapper. Provides:
//   - a palette of 4 node types (Intervention, Outcome, Confounder, Mediator)
//   - drag-and-drop to the canvas
//   - n_samples + horizon_days controls with bounds validation
//   - submit emits the Scenario JSON to the parent

import { useCallback, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type {
  Intervention,
  InterventionType,
  Scenario,
} from "@/lib/api/sim";

type PaletteKind = "Intervention" | "Outcome" | "Confounder" | "Mediator";

interface PaletteEntry {
  kind: PaletteKind;
  color: string;
}

const PALETTE: readonly PaletteEntry[] = [
  { kind: "Intervention", color: "#16a34a" },
  { kind: "Outcome", color: "#dc2626" },
  { kind: "Confounder", color: "#f59e0b" },
  { kind: "Mediator", color: "#3b82f6" },
] as const;

const DEFAULT_NODES: Node[] = [
  {
    id: "n_int_1",
    position: { x: 80, y: 80 },
    data: { label: "Vigabatrin", kind: "Intervention" as PaletteKind },
    type: "default",
  },
  {
    id: "n_out_1",
    position: { x: 380, y: 200 },
    data: { label: "Seizure frequency", kind: "Outcome" as PaletteKind },
    type: "default",
  },
];

const DEFAULT_EDGES: Edge[] = [
  { id: "e_int_out", source: "n_int_1", target: "n_out_1", animated: true },
];

interface Props {
  onSubmit: (scenario: Scenario) => void;
  busy: boolean;
}

export default function ScenarioBuilderInner({ onSubmit, busy }: Props) {
  const t = useTranslations("Simulate");
  const [nodes, setNodes, onNodesChange] = useNodesState(DEFAULT_NODES);
  const [edges, setEdges, onEdgesChange] = useEdgesState(DEFAULT_EDGES);
  const [name, setName] = useState("Vigabatrin 50 mg/kg/day");
  const [nSamples, setNSamples] = useState(1000);
  const [horizonDays, setHorizonDays] = useState(90);
  const [error, setError] = useState<string | null>(null);

  const onConnect = useCallback(
    (conn: Connection) => setEdges((eds) => addEdge(conn, eds)),
    [setEdges],
  );

  const handleAddNode = useCallback(
    (kind: PaletteKind) => {
      setNodes((cur) => [
        ...cur,
        {
          id: `n_${kind.toLowerCase()}_${cur.length + 1}`,
          position: { x: 80 + Math.random() * 280, y: 80 + Math.random() * 200 },
          data: { label: kind, kind },
          type: "default",
        },
      ]);
    },
    [setNodes],
  );

  const interventions = useMemo<Intervention[]>(() => {
    return nodes
      .filter((n) => (n.data as { kind?: PaletteKind }).kind === "Intervention")
      .map((n) => ({
        node_name: (n.data as { label: string }).label,
        intervention_type: "treatment" as InterventionType,
        value: 1,
      }));
  }, [nodes]);

  function validate(): string | null {
    if (nSamples < 10 || nSamples > 10000) return t("errSamplesRange");
    if (horizonDays < 1 || horizonDays > 2000) return t("errHorizonRange");
    if (interventions.length < 1) return t("errMinIntervention");
    if (!name.trim()) return t("errNameRequired");
    return null;
  }

  function handleSubmit() {
    const v = validate();
    if (v) {
      setError(v);
      return;
    }
    setError(null);
    const scenario: Scenario = {
      name: name.trim(),
      scm_id: "reference_vigabatrin_seizure",
      interventions,
      n_samples: nSamples,
      horizon_days: horizonDays,
    };
    onSubmit(scenario);
  }

  return (
    <section className="flex flex-col gap-3 rounded-md border border-stone-200 bg-white p-4">
      <header className="flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-stone-900">{t("builder")}</h2>
        <span className="font-mono text-[10px] text-stone-500">react-flow</span>
      </header>

      <div className="flex flex-wrap gap-2">
        {PALETTE.map((p) => (
          <button
            key={p.kind}
            type="button"
            onClick={() => handleAddNode(p.kind)}
            className="rounded-md border border-stone-200 bg-stone-50 px-2 py-1 text-xs font-medium text-stone-700 hover:bg-stone-100"
            style={{ borderLeftColor: p.color, borderLeftWidth: 3 }}
          >
            + {t(`palette.${p.kind}`)}
          </button>
        ))}
      </div>

      <div className="h-[300px] rounded-md border border-stone-200">
        <ReactFlowProvider>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            fitView
          >
            <Background gap={16} />
            <Controls position="bottom-right" />
          </ReactFlow>
        </ReactFlowProvider>
      </div>

      <div className="grid gap-2 sm:grid-cols-3">
        <label className="flex flex-col gap-1">
          <span className="font-mono text-[10px] uppercase text-stone-500">
            {t("scenarioName")}
          </span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="rounded-md border border-stone-300 px-2 py-1 text-xs"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-mono text-[10px] uppercase text-stone-500">
            {t("nSamples")}
          </span>
          <input
            type="number"
            value={nSamples}
            min={10}
            max={10000}
            onChange={(e) => setNSamples(Number(e.target.value))}
            className="rounded-md border border-stone-300 px-2 py-1 text-xs"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-mono text-[10px] uppercase text-stone-500">
            {t("horizonDays")}
          </span>
          <input
            type="number"
            value={horizonDays}
            min={1}
            max={2000}
            onChange={(e) => setHorizonDays(Number(e.target.value))}
            className="rounded-md border border-stone-300 px-2 py-1 text-xs"
          />
        </label>
      </div>

      {error ? (
        <p className="rounded-md border border-rose-200 bg-rose-50 px-2 py-1 text-xs text-rose-900">
          {error}
        </p>
      ) : null}

      <button
        type="button"
        onClick={handleSubmit}
        disabled={busy}
        className="rounded-md bg-cyan-700 px-3 py-2 text-sm font-medium text-white disabled:opacity-60 hover:bg-cyan-800"
      >
        {busy ? t("running") : t("runSimulation", { samples: nSamples })}
      </button>
    </section>
  );
}

// Note: NodeProps import is retained for future custom-node typing; the
// default node renderer is used in the current MVP.
export type _NodePropsRef = NodeProps;
