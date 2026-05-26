"use client";

// viewer/app/[locale]/drift/Timeline.tsx — Phase 7.6 Client Component.
//
// 13-trace Plotly time series with overlay markers for evidence events.
// Per-dim toggle controls dim visibility; default keeps all traces ON.
// react-plotly.js is dynamic-imported (ssr:false) for SSR safety.

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";

import type { BeliefHistoryEntry } from "@/lib/api/belief";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface Props {
  data: BeliefHistoryEntry[][];
  locale: "en" | "ka";
}

// Stable palette of 13 distinguishable colors. Tailwind-aligned tones.
const PALETTE: readonly string[] = [
  "#0ea5e9",
  "#f97316",
  "#16a34a",
  "#dc2626",
  "#9333ea",
  "#0891b2",
  "#f59e0b",
  "#10b981",
  "#ef4444",
  "#6366f1",
  "#14b8a6",
  "#eab308",
  "#a855f7",
] as const;

export default function Timeline({ data, locale }: Props) {
  const t = useTranslations("Drift");
  const tDim = useTranslations("Twin.dimensions");

  const allDimNames = useMemo(
    () => data.map((series) => series[0]?.dim_name ?? "").filter(Boolean),
    [data],
  );

  const [visible, setVisible] = useState<Record<string, boolean>>(() =>
    allDimNames.reduce<Record<string, boolean>>(
      (acc, name) => ({ ...acc, [name]: true }),
      {},
    ),
  );

  function toggleDim(name: string) {
    setVisible((v) => ({ ...v, [name]: !v[name] }));
  }

  const traces = useMemo(() => {
    const out: Record<string, unknown>[] = [];
    data.forEach((series, idx) => {
      if (series.length === 0) return;
      const dim = series[0].dim_name;
      if (!visible[dim]) return;
      const color = PALETTE[idx % PALETTE.length];
      const dimLabel = tDim.has(dim) ? tDim(dim) : dim;
      out.push({
        x: series.map((s) => s.date),
        y: series.map((s) => s.posterior_mean),
        type: "scatter",
        mode: "lines",
        name: dimLabel,
        line: { color, width: 1.5 },
        hovertemplate: `${dimLabel}: %{y:.2f}<br>%{x}<extra></extra>`,
      });
      // Evidence-event markers overlay.
      const evX: string[] = [];
      const evY: number[] = [];
      series.forEach((s) => {
        if (s.evidence_event_count > 0) {
          evX.push(s.date);
          evY.push(s.posterior_mean);
        }
      });
      if (evX.length > 0) {
        out.push({
          x: evX,
          y: evY,
          type: "scatter",
          mode: "markers",
          name: `${dimLabel} · ${t("evidence")}`,
          marker: { color, size: 8, symbol: "diamond" },
          hovertemplate: `${dimLabel} · ${t("evidence")}<extra></extra>`,
          showlegend: false,
        });
      }
    });
    return out;
  }, [data, visible, t, tDim]);

  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2 border-b border-stone-200 pb-3">
        <h2 className="mr-auto text-lg font-semibold text-stone-900">
          {t("timelineHeading")}
        </h2>
        <span className="font-mono text-xs text-stone-500">
          {locale === "ka" ? "30 დღე" : "30 days"}
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        {allDimNames.map((name, idx) => {
          const on = visible[name];
          const color = PALETTE[idx % PALETTE.length];
          const dimLabel = tDim.has(name) ? tDim(name) : name;
          return (
            <button
              key={name}
              type="button"
              onClick={() => toggleDim(name)}
              className={`rounded-md border px-2 py-1 text-xs font-medium ${
                on
                  ? "border-stone-300 bg-white text-stone-900"
                  : "border-stone-200 bg-stone-100 text-stone-400 line-through"
              }`}
              style={on ? { borderLeftColor: color, borderLeftWidth: 3 } : {}}
            >
              {dimLabel}
            </button>
          );
        })}
      </div>

      <div className="rounded-md border border-stone-200 bg-white p-3">
        <Plot
          data={traces as never}
          layout={{
            autosize: true,
            height: 420,
            margin: { l: 50, r: 18, t: 18, b: 40 },
            xaxis: {
              title: { text: t("xAxis"), font: { size: 11 } },
              showgrid: true,
              gridcolor: "#f5f5f4",
              tickfont: { size: 10 },
            },
            yaxis: {
              title: { text: t("yAxis"), font: { size: 11 } },
              showgrid: true,
              gridcolor: "#f5f5f4",
              tickfont: { size: 10 },
            },
            legend: { font: { size: 10 }, orientation: "h", y: -0.18 },
            plot_bgcolor: "rgba(0,0,0,0)",
            paper_bgcolor: "rgba(0,0,0,0)",
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: "100%", height: "420px" }}
        />
      </div>
    </section>
  );
}
