import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import ResearchStream from "@/components/research/ResearchStream";
import { fetchResearch, formatDate } from "@/lib/data";
import { buildPageMetadata, type Locale } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(locale, "research");
}

export default async function ResearchPage({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Research");
  const { items, updated } = await fetchResearch(locale);

  return (
    <div className="space-y-8">
      <header className="u-rise max-w-2xl">
        <h1 className="font-serif text-[1.9rem] leading-tight tracking-tight text-ink">
          {t("title")}
        </h1>
        <p className="mt-3 text-[0.98rem] leading-relaxed text-muted">{t("subtitle")}</p>
      </header>

      <div className="u-rise u-rise-1">
        <ResearchStream
          items={items}
          updatedLabel={updated ? formatDate(updated, locale) : undefined}
        />
      </div>
    </div>
  );
}
