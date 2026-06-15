import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { fetchClinicalTrials } from "@/lib/data";
import { buildCustomMetadata, type Locale } from "@/lib/seo";
import TrialsBrowser from "@/components/trials/TrialsBrowser";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return buildCustomMetadata(
    locale,
    "/research/trials",
    locale === "ka" ? "სამედიცინო კვლევები | ALEKSANDRA_BRAIN" : "Clinical Trials | ALEKSANDRA_BRAIN",
    locale === "ka"
      ? "აქტიური კვლევები, რომლებშიც ალექსანდრას ჩართვა შესაძლებელია"
      : "Active trials Aleksandra may be eligible to join",
  );
}

// --------------------------------------------------------------------------

export default async function ClinicalTrialsPage({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Trials");
  const { configured, eligible, needsReview } = await fetchClinicalTrials(locale);

  const browserLabels = {
    // existing card labels
    ageLabel: t("ageLabel"),
    phaseLabel: t("phaseLabel"),
    interventionLabel: t("interventionLabel"),
    locationLabel: t("locationLabel"),
    usBadge: t("usBadge"),
    intlBadge: t("intlBadge"),
    issuesLabel: t("issuesLabel"),
    viewOnCtgov: t("viewOnCtgov"),
    detailsLink: t("detailsLink"),
    eligibleHeading: t("eligibleHeading"),
    needsReviewHeading: t("needsReviewHeading"),
    emptyEligible: t("emptyEligible"),
    emptyNeedsReview: t("emptyNeedsReview"),
    // Phase D
    filterCountry: t("filterCountry"),
    allCountries: t("allCountries"),
    sortBy: t("sortBy"),
    sortUsFirst: t("sortUsFirst"),
    sortCountryAz: t("sortCountryAz"),
    sortSoonest: t("sortSoonest"),
    sortRecent: t("sortRecent"),
    startsLabel: t("startsLabel"),
    conductedAt: t("conductedAt"),
    moreSites: t("moreSites"),
    contactLabel: t("contactLabel"),
    noMatches: t("noMatches"),
  };

  return (
    <div className="space-y-10">
      {/* Page header */}
      <header className="u-rise max-w-2xl space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-serif text-[1.9rem] leading-tight tracking-tight text-ink">
            {t("title")}
          </h1>
          <span className="rounded-full bg-accent-soft px-3 py-1 text-sm font-medium text-accent-ink">
            {t("eligibleCount", { n: eligible.length })}
          </span>
        </div>
        <p className="text-[0.98rem] leading-relaxed text-muted">{t("subtitle")}</p>
        <Link
          href="/research"
          className="inline-flex items-center gap-1 text-sm text-muted hover:text-ink"
        >
          <span aria-hidden="true">←</span>
          {t("backToResearch")}
        </Link>
      </header>

      {/* Not configured banner */}
      {!configured ? (
        <div className="rounded-xl border border-line bg-surface px-5 py-8 text-center">
          <p className="text-sm text-muted">{t("notConfigured")}</p>
        </div>
      ) : (
        <TrialsBrowser
          eligible={eligible}
          needsReview={needsReview}
          labels={browserLabels}
          locale={locale}
        />
      )}
    </div>
  );
}
