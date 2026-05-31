// viewer/app/[locale]/drift/page.tsx — Phase 7.6 Belief Drift route.
//
// Server Component. Fetches 30-day posterior history for every one of the
// 13 dimensions in parallel and hands off to the client-side Timeline for
// Plotly multi-trace rendering. Feature-flag gated.

import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";

import {
  DIMENSION_NAMES,
  fetchBeliefHistory,
  type BeliefHistoryEntry,
} from "@/lib/api/belief";
import { isEnabled } from "@/lib/flags";
import Timeline from "./Timeline";

export const dynamic = "force-dynamic";

export default async function DriftPage({
  params,
}: {
  params: Promise<{ locale: "en" | "ka" }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  if (!isEnabled("DRIFT_VIEW_ENABLED")) {
    notFound();
  }

  const t = await getTranslations({ locale, namespace: "Drift" });

  // Pull 30-day history for each dim in parallel; failures fall back to mock
  // inside fetchBeliefHistory so this Promise.all never rejects.
  const allHistory: BeliefHistoryEntry[][] = await Promise.all(
    DIMENSION_NAMES.map((d) => fetchBeliefHistory(d, 30)),
  );

  const totalEvidence = allHistory.reduce(
    (acc, series) =>
      acc + series.reduce((s, e) => s + e.evidence_event_count, 0),
    0,
  );

  return (
    <main className="min-h-screen bg-stone-50 text-stone-950">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-5 py-6 sm:px-8">
        <header className="grid gap-4 lg:grid-cols-[1fr_auto]">
          <div>
            <p className="font-mono text-xs uppercase text-cyan-700">
              {t("phaseLabel")}
            </p>
            <h1 className="mt-1 text-3xl font-semibold tracking-normal sm:text-4xl">
              {t("title")}
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-stone-600">
              {t("subtitle")}
            </p>
          </div>
          <div className="grid min-w-72 grid-cols-2 gap-3">
            <div className="rounded-md border border-stone-200 bg-white p-4">
              <p className="font-mono text-xs uppercase text-stone-500">
                {t("dimensions")}
              </p>
              <p className="mt-2 text-3xl font-semibold">
                {DIMENSION_NAMES.length}
              </p>
            </div>
            <div className="rounded-md border border-stone-200 bg-white p-4">
              <p className="font-mono text-xs uppercase text-stone-500">
                {t("evidenceEvents")}
              </p>
              <p className="mt-2 text-3xl font-semibold">{totalEvidence}</p>
            </div>
          </div>
        </header>

        <section className="rounded-md border border-stone-200 bg-amber-50/40 p-4 text-xs leading-6 text-stone-700">
          {t("mockNotice")}
        </section>

        <Timeline data={allHistory} locale={locale} />

        <footer className="text-xs text-stone-500">{t("howToRead")}</footer>
      </div>
    </main>
  );
}
