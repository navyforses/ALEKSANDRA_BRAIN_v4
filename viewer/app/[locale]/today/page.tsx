// Phase 5 placeholder. Today's full clinical view ships in a later phase.
// BRAIN panel mounts via root layout.
import { setRequestLocale, getTranslations } from "next-intl/server";

export default async function TodayPage({
  params,
}: {
  params: Promise<{ locale: "en" | "ka" }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Today");
  return (
    <div className="flex flex-col h-full space-y-4">
      <header className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{t("title")}</h1>
        <p className="mt-2 text-sm text-slate-500">{t("comingSoon")}</p>
      </header>
      <section className="flex-1 flex items-center justify-center text-sm text-slate-400">
        <p>{t("fallback")}</p>
      </section>
    </div>
  )
}
