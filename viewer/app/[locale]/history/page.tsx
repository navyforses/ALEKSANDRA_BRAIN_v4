import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import HistoryFeed from "@/components/history/HistoryFeed";
import { buildPageMetadata, type Locale } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(locale, "history");
}

export default async function HistoryPage({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("History");

  return (
    <div className="space-y-8">
      <header className="u-rise max-w-2xl">
        <h1 className="font-serif text-[1.9rem] leading-tight tracking-tight text-ink">
          {t("title")}
        </h1>
        <p className="mt-3 text-[0.98rem] leading-relaxed text-muted">{t("subtitle")}</p>
        <p className="mt-2 text-xs text-faint">{t("undoNote")}</p>
      </header>

      <div className="u-rise u-rise-1">
        <HistoryFeed />
      </div>
    </div>
  );
}
