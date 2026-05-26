// viewer/app/[locale]/simulate/page.tsx — Phase 7.6 Simulation Studio route.
//
// Server Component. Eagerly fetches a default scenario comparison so the
// route renders something meaningful on first load; ScenarioBuilder lets
// the user re-submit. Feature-flag gated.

import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { compareScenarios, listScenarios } from "@/lib/api/sim";
import { isEnabled } from "@/lib/flags";
import SimulateStudio from "./SimulateStudio";

export const dynamic = "force-dynamic";

export default async function SimulatePage({
  params,
}: {
  params: Promise<{ locale: "en" | "ka" }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  if (!isEnabled("SIM_VIEW_ENABLED")) {
    notFound();
  }

  const t = await getTranslations({ locale, namespace: "Simulate" });

  const scenarios = await listScenarios();
  const initialComparison =
    scenarios.length >= 2
      ? await compareScenarios(scenarios[0].scenario_id, scenarios[1].scenario_id)
      : null;

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
                {t("scenariosSaved")}
              </p>
              <p className="mt-2 text-3xl font-semibold">{scenarios.length}</p>
            </div>
            <div className="rounded-md border border-stone-200 bg-white p-4">
              <p className="font-mono text-xs uppercase text-stone-500">
                {t("defaultScm")}
              </p>
              <p className="mt-2 truncate text-sm font-semibold text-stone-700">
                {scenarios[0]?.scm_id ?? "—"}
              </p>
            </div>
          </div>
        </header>

        <section className="rounded-md border border-stone-200 bg-amber-50/40 p-4 text-xs leading-6 text-stone-700">
          {t("mockNotice")}
        </section>

        <SimulateStudio
          initialComparison={initialComparison}
          locale={locale}
        />

        <footer className="text-xs text-stone-500">
          {t("decisionFooter")}
        </footer>
      </div>
    </main>
  );
}
