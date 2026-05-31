"use client";

// viewer/components/hypotheses/SimulationGraph.tsx — Phase 7.6 widget.
//
// Per-hypothesis expected-benefit histogram. The simulation result is
// optional; when absent the widget shows a placeholder card so the
// Hypotheses page remains structurally intact during partial rollouts.

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface Props {
  hypothesisId: string;
  benefitSamples?: number[]; // optional; placeholder rendered if absent
  meanBenefit?: number;
  locale?: "en" | "ka";
}

function formatNumber(value: number, locale: "en" | "ka"): string {
  try {
    return new Intl.NumberFormat(locale === "ka" ? "ka-GE" : "en-US", {
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return value.toFixed(2);
  }
}

export default function SimulationGraph({
  hypothesisId,
  benefitSamples,
  meanBenefit,
  locale = "en",
}: Props) {
  const t = useTranslations("SimulationGraph");

  if (!benefitSamples || benefitSamples.length === 0) {
    return (
      <div className="mt-2 flex items-center gap-2 rounded-md border border-dashed border-stone-200 bg-stone-50 px-2 py-1.5 text-[10px] text-stone-500">
        <span className="font-mono">{t("noSim")}</span>
        <span className="font-mono text-stone-400">· {hypothesisId.slice(0, 8)}</span>
      </div>
    );
  }

  return (
    <div className="mt-2 rounded-md border border-stone-200 bg-white p-2">
      <header className="flex items-baseline justify-between">
        <h4 className="text-[11px] font-semibold text-stone-700">
          {t("title")}
        </h4>
        {meanBenefit !== undefined ? (
          <span className="font-mono text-[10px] text-stone-500">
            μ = {formatNumber(meanBenefit, locale)}
          </span>
        ) : null}
      </header>
      <Plot
        data={[
          {
            x: benefitSamples,
            type: "histogram",
            nbinsx: 25,
            marker: { color: "#0891b2" },
          },
        ]}
        layout={{
          autosize: true,
          height: 90,
          margin: { l: 24, r: 6, t: 4, b: 18 },
          xaxis: { tickfont: { size: 8 } },
          yaxis: { tickfont: { size: 8 } },
          showlegend: false,
          plot_bgcolor: "rgba(0,0,0,0)",
          paper_bgcolor: "rgba(0,0,0,0)",
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%", height: "90px" }}
      />
    </div>
  );
}
