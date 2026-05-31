// viewer/app/[locale]/snapshot/page.tsx — Phase 7.6 widget route.
//
// Server Component wrapper for the SnapshotWidget (13-dimension posterior
// summary). Created during the Manus AI portal reconciliation merge
// (2026-05-30): the widget originally mounted inside the root home
// /[locale]/page.tsx but Manus rewrote home to <PortalHomeDashboard/>
// which has no children slot. Surfacing here keeps it accessible (linked
// from /[locale]/dashboard hub).
//
// Flag gating: STATUS_COCKPIT_TWIN_WIDGET (viewer/lib/flags.ts:33).
// NO-GO action: flip flag to false → route 404s; Status Cockpit reverts
// to v6.1 layout (no twin widget).

import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { fetchBeliefSnapshot } from "@/lib/api/belief";
import SnapshotWidget from "@/components/twin/SnapshotWidget";
import { isEnabled } from "@/lib/flags";

export const dynamic = "force-dynamic";

export default async function SnapshotPage({
  params,
}: {
  params: Promise<{ locale: "en" | "ka" }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  if (!isEnabled("STATUS_COCKPIT_TWIN_WIDGET")) {
    notFound();
  }

  const t = await getTranslations({ locale, namespace: "SnapshotWidget" });
  const snapshot = await fetchBeliefSnapshot();

  return (
    <main className="min-h-screen bg-stone-50 text-stone-950">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-5 py-6 sm:px-8">
        <header>
          <p className="font-mono text-xs uppercase text-cyan-700">
            Phase 7.6
          </p>
          <h1 className="mt-1 text-3xl font-semibold tracking-normal sm:text-4xl">
            {t("title")}
          </h1>
        </header>

        <SnapshotWidget initialSnapshot={snapshot} locale={locale} />
      </div>
    </main>
  );
}
