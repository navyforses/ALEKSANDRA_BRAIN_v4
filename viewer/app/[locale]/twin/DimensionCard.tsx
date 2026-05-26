"use client";

// viewer/app/[locale]/twin/DimensionCard.tsx — Phase 7.6 Client Component.
//
// Per-dimension Plotly histogram card. react-plotly.js is dynamic-imported
// with ssr:false because Plotly touches window/document during init. If the
// dimension has no continuous samples (categorical / bernoulli) we render a
// compact text-only summary card instead.
//
// The translation key for the title is Twin.dimensions.<dimName>; the i18n
// dictionary holds idiomatic KA + EN copy for each of the 13 dim names.

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface Props {
  dimName: string;
  samples: number[];
  mean: number;
  hdi80Low: number;
  hdi80High: number;
  units?: string;
  citation?: string;
  locale: "en" | "ka";
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

export default function DimensionCard({
  dimName,
  samples,
  mean,
  hdi80Low,
  hdi80High,
  units,
  citation,
  locale,
}: Props) {
  const t = useTranslations("Twin");
  const tDim = useTranslations("Twin.dimensions");

  const dimLabel = tDim.has(dimName) ? tDim(dimName) : dimName;
  const hasSamples = samples && samples.length > 0;

  return (
    <article className="rounded-md border border-stone-200 bg-white p-4 shadow-sm shadow-stone-200/40">
      <header className="flex items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold leading-5 text-stone-900">
          {dimLabel}
        </h3>
        {units ? (
          <span className="font-mono text-[10px] uppercase text-stone-500">
            {units}
          </span>
        ) : null}
      </header>

      <dl className="mt-2 grid grid-cols-3 gap-2 text-xs">
        <div>
          <dt className="font-mono uppercase text-stone-500">{t("mean")}</dt>
          <dd className="mt-0.5 font-semibold text-stone-900">
            {formatNumber(mean, locale)}
          </dd>
        </div>
        <div>
          <dt className="font-mono uppercase text-stone-500">{t("hdiLow")}</dt>
          <dd className="mt-0.5 font-semibold text-stone-900">
            {formatNumber(hdi80Low, locale)}
          </dd>
        </div>
        <div>
          <dt className="font-mono uppercase text-stone-500">{t("hdiHigh")}</dt>
          <dd className="mt-0.5 font-semibold text-stone-900">
            {formatNumber(hdi80High, locale)}
          </dd>
        </div>
      </dl>

      <div className="mt-3">
        {hasSamples ? (
          <Plot
            data={[
              {
                x: samples,
                type: "histogram",
                histfunc: "count",
                nbinsx: 40,
                marker: { color: "#0891b2" },
                hoverinfo: "x+y",
              },
            ]}
            layout={{
              autosize: true,
              height: 120,
              margin: { l: 30, r: 8, t: 8, b: 22 },
              xaxis: { showgrid: false, tickfont: { size: 9 } },
              yaxis: { showgrid: true, tickfont: { size: 9 } },
              showlegend: false,
              plot_bgcolor: "rgba(0,0,0,0)",
              paper_bgcolor: "rgba(0,0,0,0)",
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: "100%", height: "120px" }}
          />
        ) : (
          <div className="flex h-[120px] items-center justify-center rounded-sm border border-dashed border-stone-200 px-2 text-center text-xs text-stone-500">
            {t("discreteSummary")}
          </div>
        )}
      </div>

      <p className="mt-2 font-mono text-[10px] leading-4 text-stone-400">
        {t("ciAnnotation", {
          low: formatNumber(hdi80Low, locale),
          high: formatNumber(hdi80High, locale),
        })}
      </p>
      {citation ? (
        <p className="mt-1 font-mono text-[10px] leading-4 text-stone-400">
          {citation}
        </p>
      ) : null}
    </article>
  );
}
