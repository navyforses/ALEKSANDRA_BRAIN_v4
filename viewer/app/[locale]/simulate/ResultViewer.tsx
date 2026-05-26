"use client";

// viewer/app/[locale]/simulate/ResultViewer.tsx — Phase 7.6 Client Component.
//
// Side-by-side Plotly histograms per outcome (Scenario A vs B) plus a
// per-outcome delta card with verdict badge. Plotly is dynamic-imported
// for SSR safety.

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";

import type {
  ComparisonVerdict,
  ScenarioComparison,
} from "@/lib/api/sim";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface Props {
  comparison: ScenarioComparison | null;
  locale: "en" | "ka";
}

function verdictTone(v: ComparisonVerdict): string {
  switch (v) {
    case "A_better":
      return "border-emerald-300 bg-emerald-50 text-emerald-900";
    case "B_better":
      return "border-rose-300 bg-rose-50 text-rose-900";
    case "tie":
      return "border-stone-300 bg-stone-50 text-stone-800";
    default:
      return "border-amber-300 bg-amber-50 text-amber-900";
  }
}

function formatNumber(value: number, locale: "en" | "ka"): string {
  try {
    return new Intl.NumberFormat(locale === "ka" ? "ka-GE" : "en-US", {
      maximumFractionDigits: 3,
    }).format(value);
  } catch {
    return value.toFixed(3);
  }
}

export default function ResultViewer({ comparison, locale }: Props) {
  const t = useTranslations("Simulate");

  if (!comparison) {
    return (
      <section className="flex h-full items-center justify-center rounded-md border border-stone-200 bg-white p-4 text-sm text-stone-500">
        {t("noResultsYet")}
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-3 rounded-md border border-stone-200 bg-white p-4">
      <header className="flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-stone-900">{t("results")}</h2>
        <span className="font-mono text-[10px] text-stone-500">
          A · {comparison.scenario_a.scenario_name} vs B ·{" "}
          {comparison.scenario_b.scenario_name}
        </span>
      </header>

      {comparison.outcome_deltas.map((delta, idx) => {
        const outcomeA = comparison.scenario_a.outcomes.find(
          (o) => o.outcome_name === delta.outcome_name,
        );
        const outcomeB = comparison.scenario_b.outcomes.find(
          (o) => o.outcome_name === delta.outcome_name,
        );
        return (
          <article
            key={`${delta.outcome_name}-${idx}`}
            className="rounded-md border border-stone-200 bg-stone-50 p-3"
          >
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="text-xs font-semibold text-stone-900">
                {delta.outcome_name}
              </h3>
              <span
                className={`rounded-md border px-2 py-0.5 font-mono text-[10px] uppercase ${verdictTone(
                  delta.verdict,
                )}`}
              >
                {t(`verdict.${delta.verdict}`)}
              </span>
            </div>

            <p className="mt-1 font-mono text-[10px] text-stone-600">
              p(A &gt; B) = {formatNumber(delta.p_a_greater_b, locale)} · Δ ={" "}
              {formatNumber(delta.mean_delta, locale)}
            </p>

            {outcomeA && outcomeB ? (
              <div className="mt-2">
                <Plot
                  data={[
                    {
                      x: outcomeA.samples,
                      type: "histogram",
                      name: `A · ${comparison.scenario_a.scenario_name}`,
                      opacity: 0.55,
                      marker: { color: "#0891b2" },
                      nbinsx: 30,
                    },
                    {
                      x: outcomeB.samples,
                      type: "histogram",
                      name: `B · ${comparison.scenario_b.scenario_name}`,
                      opacity: 0.55,
                      marker: { color: "#dc2626" },
                      nbinsx: 30,
                    },
                  ]}
                  layout={{
                    autosize: true,
                    height: 220,
                    barmode: "overlay",
                    margin: { l: 40, r: 10, t: 10, b: 30 },
                    xaxis: { tickfont: { size: 10 } },
                    yaxis: { tickfont: { size: 10 } },
                    legend: { font: { size: 10 } },
                    plot_bgcolor: "rgba(0,0,0,0)",
                    paper_bgcolor: "rgba(0,0,0,0)",
                  }}
                  config={{ displayModeBar: false, responsive: true }}
                  style={{ width: "100%", height: "220px" }}
                />
              </div>
            ) : null}
          </article>
        );
      })}
    </section>
  );
}
