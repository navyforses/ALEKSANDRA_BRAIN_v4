import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import AttentionList from "@/components/today/AttentionList";
import IntakeHero from "@/components/intake/IntakeHero";
import { IconBrain, IconResearch } from "@/components/shell/icons";
import { fetchToday, formatDate } from "@/lib/data";
import { buildPageMetadata, type Locale } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(locale, "home");
}

export default async function TodayPage({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Today");
  const { status, attention, brief } = await fetchToday(locale);

  const statusText = !status.configured
    ? t("statusConnecting")
    : status.scanning
      ? t("statusScanning")
      : status.lastScanAt
        ? t("statusIdle", {
            time: formatDate(status.lastScanAt, locale),
            source: status.lastScanSource || t("theLiterature"),
          })
        : t("statusReady");

  const briefLines = brief
    ? brief.sections.flatMap((s) => s.lines.map((l) => ({ ...l, label: s.label }))).slice(0, 4)
    : [];

  return (
    <div className="space-y-14">
      {/* Hero — someone is working, and one step you can take now. */}
      <section className="lamp u-rise">
        <p className="flex items-center gap-2.5 text-sm text-muted">
          <span aria-hidden className="dot-breathe h-2 w-2 rounded-full bg-signal" />
          {statusText}
        </p>

        <h1 className="mt-5 max-w-2xl font-serif text-[2rem] leading-[1.15] tracking-tight text-ink sm:text-[2.6rem]">
          {t("title")}
        </h1>
        <p className="mt-3 max-w-xl text-[0.98rem] leading-relaxed text-muted">{t("lead")}</p>

        {status.configured ? (
          <p className="mt-5 text-sm text-faint">
            {t("tracking", {
              papers: status.counts.papers,
              hypotheses: status.counts.hypotheses,
              therapies: status.counts.therapies,
            })}
          </p>
        ) : null}

        <div className="mt-8">
          <p className="mb-2.5 text-xs font-medium uppercase tracking-[0.18em] text-faint">
            {t("askLabel")}
          </p>
          <IntakeHero />
        </div>
      </section>

      {/* What needs you */}
      <section className="u-rise u-rise-1">
        <h2 className="text-lg text-ink">{t("attentionTitle")}</h2>
        {attention.length === 0 ? (
          <div className="mt-4 rounded-xl border border-line bg-surface px-5 py-8 text-center">
            <p className="text-sm text-muted">{t("attentionEmpty")}</p>
            <p className="mt-1 text-xs text-faint">{t("attentionEmptyNote")}</p>
          </div>
        ) : (
          <AttentionList items={attention} seeAllLabel={t("seeAllResearch")} />
        )}
      </section>

      {/* This week */}
      <section className="u-rise u-rise-2">
        <div className="flex items-baseline justify-between gap-4">
          <h2 className="text-lg text-ink">{t("weekTitle")}</h2>
          {brief ? (
            <Link href="/brief" className="text-sm font-medium text-accent-ink hover:underline">
              {t("openBrief")} →
            </Link>
          ) : null}
        </div>

        {briefLines.length > 0 ? (
          <ul className="mt-4 space-y-3">
            {briefLines.map((line, i) => (
              <li key={i} className="card flex gap-3 p-4">
                <span aria-hidden className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                <div className="min-w-0">
                  <p className="text-sm leading-relaxed text-ink">{line.text}</p>
                  {line.source ? (
                    <p className="mt-1 text-xs text-faint">{line.source}</p>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <div className="mt-4 rounded-xl border border-line bg-surface px-5 py-8">
            <p className="text-sm text-muted">{t("weekEmpty")}</p>
            <p className="mt-1 text-xs text-faint">{t("weekEmptyNote")}</p>
          </div>
        )}
      </section>

      {/* Quiet ways deeper */}
      <section className="u-rise u-rise-3 grid gap-3 sm:grid-cols-2">
        <Link
          href="/research"
          className="card group flex items-start gap-3 p-5 transition-colors hover:border-accent-line"
        >
          <IconResearch className="mt-0.5 h-5 w-5 text-accent" />
          <span>
            <span className="block font-serif text-base text-ink group-hover:text-accent-ink">
              {t("exploreResearch")}
            </span>
            <span className="mt-0.5 block text-xs leading-relaxed text-muted">
              {t("exploreResearchNote")}
            </span>
          </span>
        </Link>
        <Link
          href="/brain"
          className="card group flex items-start gap-3 p-5 transition-colors hover:border-accent-line"
        >
          <IconBrain className="mt-0.5 h-5 w-5 text-signal" />
          <span>
            <span className="block font-serif text-base text-ink group-hover:text-accent-ink">
              {t("exploreBrain")}
            </span>
            <span className="mt-0.5 block text-xs leading-relaxed text-muted">
              {t("exploreBrainNote")}
            </span>
          </span>
        </Link>
      </section>
    </div>
  );
}
