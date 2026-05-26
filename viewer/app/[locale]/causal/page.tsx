// viewer/app/[locale]/causal/page.tsx — Phase 7.6 Causal Graph route.
//
// Server Component. Fetches the SCM graph (reference Vigabatrin->Seizure
// pattern in mock mode) and renders the vis-network side-by-side with the
// NodeDetail panel. Feature-flag gated.

import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { fetchCausalGraph } from "@/lib/api/causal";
import { isEnabled } from "@/lib/flags";
import CausalView from "./CausalView";

export const dynamic = "force-dynamic";

export default async function CausalPage({
  params,
}: {
  params: Promise<{ locale: "en" | "ka" }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  if (!isEnabled("CAUSAL_VIEW_ENABLED")) {
    notFound();
  }

  const t = await getTranslations({ locale, namespace: "Causal" });
  const graph = await fetchCausalGraph();

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
                {t("nodes")}
              </p>
              <p className="mt-2 text-3xl font-semibold">
                {graph.nodes.length}
              </p>
            </div>
            <div className="rounded-md border border-stone-200 bg-white p-4">
              <p className="font-mono text-xs uppercase text-stone-500">
                {t("edges")}
              </p>
              <p className="mt-2 text-3xl font-semibold">
                {graph.edges.length}
              </p>
            </div>
          </div>
        </header>

        <section className="rounded-md border border-stone-200 bg-amber-50/40 p-4 text-xs leading-6 text-stone-700">
          {t("mockNotice")}
        </section>

        <CausalView graph={graph} locale={locale} />

        <footer className="text-xs text-stone-500">{t("howToRead")}</footer>
      </div>
    </main>
  );
}
