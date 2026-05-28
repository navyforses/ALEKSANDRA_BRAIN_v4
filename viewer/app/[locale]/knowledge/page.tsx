import { buildPageMetadata, type Locale } from "@/lib/seo";
import type { Metadata } from "next";
// Phase 5 placeholder. Knowledge surfaces papers, graph, hypotheses,
// and the perception pipeline in a later phase.
// BRAIN panel mounts via root layout.
import { setRequestLocale, getTranslations } from "next-intl/server";


export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(locale, "knowledge");
}

export default async function KnowledgePage({
  params,
}: {
  params: Promise<{ locale: "en" | "ka" }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Knowledge");
  return (
    <div className="flex flex-col h-full space-y-4">
      <header className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{t("title")}</h1>
        <p className="mt-2 text-sm text-slate-500">
          {t("subtitle")}
        </p>
      </header>
      <section className="flex-1 flex items-center justify-center text-sm text-slate-400">
        <p>{t("fallback")}</p>
      </section>
    </div>
  )
}
