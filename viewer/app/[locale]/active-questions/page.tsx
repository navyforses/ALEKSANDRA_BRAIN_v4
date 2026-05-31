// viewer/app/[locale]/active-questions/page.tsx — Phase 7.4 widget route.
//
// Server Component wrapper for the Phase 7.4 Active Questions widget.
// Created during the Manus AI portal reconciliation merge (2026-05-30):
// the widget originally mounted inside /[locale]/today/page.tsx but Manus
// rewrote today/ to <PortalTopicPage pageKey="today"/> which exposes no
// children slot. Routing the widget to its own URL keeps it surfaceable
// (linked from the /[locale]/dashboard hub) without forking PortalContent.
//
// Flag gating: ACTIVE_QUESTION_OUTBOUND (viewer/lib/flags.ts:38).
// NO-GO action: flip flag to false → route 404s; in-app responses still
// parse to keep the audit chain warm per Phase 7.7 §5.2.

import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";

import ActiveQuestionsSection from "@/components/inbox/ActiveQuestionsSection";
import { isEnabled } from "@/lib/flags";

export const dynamic = "force-dynamic";

export default async function ActiveQuestionsPage({
  params,
}: {
  params: Promise<{ locale: "en" | "ka" }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  if (!isEnabled("ACTIVE_QUESTION_OUTBOUND")) {
    notFound();
  }

  const t = await getTranslations({ locale, namespace: "ActiveQuestionsSection" });

  return (
    <main className="min-h-screen bg-stone-50 text-stone-950">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-5 py-6 sm:px-8">
        <header>
          <p className="font-mono text-xs uppercase text-cyan-700">
            Phase 7.4
          </p>
          <h1 className="mt-1 text-3xl font-semibold tracking-normal sm:text-4xl">
            {t("title")}
          </h1>
        </header>

        <ActiveQuestionsSection locale={locale} />
      </div>
    </main>
  );
}
