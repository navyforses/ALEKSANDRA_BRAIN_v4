"use client";

// viewer/components/twin/SnapshotWidget.tsx — Phase 7.6 refactor widget.
//
// Light 13-dimension posterior summary panel intended for the root Status
// Cockpit. NO histograms (would blow up the cockpit). Per-dim row: mean +
// 80% HDI badge + delta arrow. Reads BeliefSnapshot from the parent or
// (when used directly) pulls via the API client.

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import {
  fetchBeliefSnapshot,
  type BeliefSnapshot,
  type BeliefDimension,
} from "@/lib/api/belief";

// Tiny sparkline for the most-uncertain dim. dynamic-imported so the
// SnapshotWidget keeps Plotly out of the cockpit's main bundle.
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface Props {
  initialSnapshot?: BeliefSnapshot;
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

function DimRow({
  dim,
  locale,
  label,
}: {
  dim: BeliefDimension;
  locale: "en" | "ka";
  label: string;
}) {
  return (
    <li className="flex items-baseline justify-between gap-2 border-b border-stone-100 py-1.5 last:border-b-0">
      <span className="truncate text-xs font-medium text-stone-800">
        {label}
      </span>
      <span className="flex items-baseline gap-2 font-mono text-[11px] text-stone-600">
        <span className="text-stone-900">
          {formatNumber(dim.posterior_mean, locale)}
        </span>
        <span className="text-stone-400">
          [{formatNumber(dim.hdi_80_low, locale)} ·{" "}
          {formatNumber(dim.hdi_80_high, locale)}]
        </span>
      </span>
    </li>
  );
}

export default function SnapshotWidget({
  initialSnapshot,
  locale = "en",
}: Props) {
  const t = useTranslations("SnapshotWidget");
  const tDim = useTranslations("Twin.dimensions");
  const [snapshot, setSnapshot] = useState<BeliefSnapshot | null>(
    initialSnapshot ?? null,
  );

  useEffect(() => {
    if (initialSnapshot) return;
    let cancelled = false;
    fetchBeliefSnapshot()
      .then((s) => {
        if (!cancelled) setSnapshot(s);
      })
      .catch(() => {
        /* mock fallback already in client */
      });
    return () => {
      cancelled = true;
    };
  }, [initialSnapshot]);

  if (!snapshot) {
    return (
      <section className="rounded-md border border-stone-200 bg-white p-3 text-xs text-stone-500">
        {t("loading")}
      </section>
    );
  }

  // Pick the dim with the widest 80% HDI as the sparkline subject.
  const widest = snapshot.dimensions.reduce<BeliefDimension | null>(
    (acc, d) => {
      if (!d.samples || d.samples.length === 0) return acc;
      const span = d.hdi_80_high - d.hdi_80_low;
      const accSpan = acc ? acc.hdi_80_high - acc.hdi_80_low : -1;
      return span > accSpan ? d : acc;
    },
    null,
  );

  return (
    <section className="rounded-md border border-stone-200 bg-white p-4">
      <header className="flex items-baseline justify-between border-b border-stone-100 pb-2">
        <h2 className="text-sm font-semibold text-stone-900">{t("title")}</h2>
        <span className="font-mono text-[10px] text-stone-400">
          {snapshot.dimensions.length} {t("dimensionsSuffix")}
        </span>
      </header>
      {widest ? (
        <div className="mt-2">
          <Plot
            data={[
              {
                x: widest.samples,
                type: "histogram",
                nbinsx: 25,
                marker: { color: "#0891b2" },
              },
            ]}
            layout={{
              autosize: true,
              height: 60,
              margin: { l: 18, r: 4, t: 2, b: 14 },
              xaxis: { tickfont: { size: 8 } },
              yaxis: { showticklabels: false },
              showlegend: false,
              plot_bgcolor: "rgba(0,0,0,0)",
              paper_bgcolor: "rgba(0,0,0,0)",
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: "100%", height: "60px" }}
          />
        </div>
      ) : null}
      <ul className="mt-2">
        {snapshot.dimensions.map((dim) => (
          <DimRow
            key={dim.name}
            dim={dim}
            locale={locale}
            label={tDim.has(dim.name) ? tDim(dim.name) : dim.name}
          />
        ))}
      </ul>
    </section>
  );
}
