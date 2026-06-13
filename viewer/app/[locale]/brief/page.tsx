import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import PrintButton from "@/components/brief/PrintButton";
import { fetchBrief, formatDate } from "@/lib/data";
import { buildPageMetadata, type Locale } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(locale, "brief");
}

export default async function BriefPage({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Brief");
  const brief = await fetchBrief(locale);

  return (
    <div className="space-y-8">
      <header className="no-print u-rise flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="max-w-2xl">
          <h1 className="font-serif text-[1.9rem] leading-tight tracking-tight text-ink">
            {t("title")}
          </h1>
          <p className="mt-3 text-[0.98rem] leading-relaxed text-muted">{t("subtitle")}</p>
        </div>
        {brief ? <PrintButton /> : null}
      </header>

      {brief ? (
        <article className="reader-sheet u-rise u-rise-1 mx-auto">
          {/* Self-contained header so the printed PDF stands on its own. */}
          <div className="border-b border-line pb-5">
            <p className="text-xs font-medium uppercase tracking-[0.22em] text-faint">
              ALEKSANDRA_BRAIN
            </p>
            <h2 className="mt-2 font-serif text-2xl leading-tight text-ink">{t("forName")}</h2>
            <p className="mt-1.5 text-sm text-muted">
              {brief.weekLabel ? t("weekOf", { week: brief.weekLabel }) : t("title")}
              {brief.generatedAt
                ? ` · ${t("generatedOn", { date: formatDate(brief.generatedAt, locale) })}`
                : ""}
            </p>
          </div>

          <div className="mt-6 space-y-8">
            {brief.sections.map((section, si) => (
              <section key={si}>
                <h3 className="font-serif text-lg text-ink">{section.label}</h3>
                <ul className="mt-3 space-y-3">
                  {section.lines.map((line, li) => (
                    <li key={li} className="flex gap-3">
                      <span
                        aria-hidden
                        className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent"
                      />
                      <div className="min-w-0">
                        <p className="text-[0.95rem] leading-relaxed text-ink/90">{line.text}</p>
                        {line.source ? (
                          <p className="mt-1 text-xs text-faint">
                            {t("source")}: {line.source}
                          </p>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>

          <p className="mt-8 border-t border-line pt-4 text-xs leading-relaxed text-faint">
            {t("footer")}
          </p>
        </article>
      ) : (
        <div className="u-rise u-rise-1 rounded-xl border border-line bg-surface px-6 py-12 text-center">
          <p className="text-sm text-muted">{t("empty")}</p>
          <p className="mx-auto mt-2 max-w-md text-xs leading-relaxed text-faint">
            {t("emptyNote")}
          </p>
        </div>
      )}
    </div>
  );
}
