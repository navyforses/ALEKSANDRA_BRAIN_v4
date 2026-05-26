"use client";

// viewer/app/[locale]/twin/DimensionGrid.tsx — Phase 7.6 Client Component.
//
// Tailwind grid of 13 DimensionCard widgets. Receives the snapshot from the
// server-rendered TwinPage; passes the per-dim metadata to DimensionCard for
// Plotly rendering. Header carries the snapshot timestamp formatted to the
// active locale.

import { useTranslations } from "next-intl";

import type { BeliefSnapshot } from "@/lib/api/belief";
import DimensionCard from "./DimensionCard";

interface Props {
  snapshot: BeliefSnapshot;
  locale: "en" | "ka";
}

function formatTimestamp(iso: string, locale: "en" | "ka"): string {
  try {
    const d = new Date(iso);
    return new Intl.DateTimeFormat(locale === "ka" ? "ka-GE" : "en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "UTC",
    }).format(d);
  } catch {
    return iso;
  }
}

export default function DimensionGrid({ snapshot, locale }: Props) {
  const t = useTranslations("Twin");

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-stone-200 pb-3">
        <h2 className="text-lg font-semibold text-stone-900">
          {t("posteriorOverview")}
        </h2>
        <p className="font-mono text-xs text-stone-500">
          {t("lastUpdated")}: {formatTimestamp(snapshot.generated_at, locale)}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {snapshot.dimensions.map((dim) => (
          <DimensionCard
            key={dim.name}
            dimName={dim.name}
            samples={dim.samples}
            mean={dim.posterior_mean}
            hdi80Low={dim.hdi_80_low}
            hdi80High={dim.hdi_80_high}
            units={dim.units}
            citation={dim.citation}
            locale={locale}
          />
        ))}
      </div>
    </section>
  );
}
