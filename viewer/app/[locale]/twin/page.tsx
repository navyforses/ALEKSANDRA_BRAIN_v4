// viewer/app/[locale]/twin/page.tsx — Phase 7.6 Twin Status route.
//
// Server Component. Pulls the 13-dimension posterior snapshot from the
// Belief API (mock mode in this build) and hands off to the client-side
// DimensionGrid for Plotly rendering. Feature-flag gated per Phase 7.7
// 5.2 NO-GO contract: when TWIN_VIEW_ENABLED is false the route 404s.

import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { fetchBeliefSnapshot } from "@/lib/api/belief";
import { isEnabled } from "@/lib/flags";
import DimensionGrid from "./DimensionGrid";
import TwinImpactFilter from "@/components/research/TwinImpactFilter";

export const dynamic = "force-dynamic";

export default async function TwinPage({
  params,
}: {
  params: Promise<{ locale: "en" | "ka" }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  if (!isEnabled("TWIN_VIEW_ENABLED")) {
    notFound();
  }

  const t = await getTranslations({ locale, namespace: "Twin" });
  const snapshot = await fetchBeliefSnapshot();

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
                {t("dimensionsCount")}
              </p>
              <p className="mt-2 text-3xl font-semibold">
                {snapshot.dimensions.length}
              </p>
            </div>
            <div className="rounded-md border border-stone-200 bg-white p-4">
              <p className="font-mono text-xs uppercase text-stone-500">
                {t("evidence30d")}
              </p>
              <p className="mt-2 text-3xl font-semibold">
                {snapshot.evidence_count_30d}
              </p>
            </div>
          </div>
        </header>

        <section className="rounded-md border border-stone-200 bg-amber-50/40 p-4 text-xs leading-6 text-stone-700">
          {t("mockNotice")}
        </section>

        {/* TwinImpactFilter folded in during the Manus AI portal merge
            (2026-05-30). Originally sat above the Research Pulse list on
            /[locale]/papers (which Manus rewrote to PortalTopicPage);
            surfacing here so the KL-divergence sort stays reachable. */}
        <TwinImpactFilter />

        <DimensionGrid snapshot={snapshot} locale={locale} />

        <footer className="text-xs text-stone-500">
          {t("privacyFooter")}
        </footer>
      </div>
    </main>
  );
}
