import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { fetchClinicalTrials } from "@/lib/data";
import type { TrialItem } from "@/lib/data";
import { buildCustomMetadata, type Locale } from "@/lib/seo";

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
// Small pure helpers — no client interactivity needed for this surface.

function StatusBadge({ status }: { status: string }) {
  const upper = status.toUpperCase();
  const isActive =
    upper === "RECRUITING" ||
    upper === "ENROLLING_BY_INVITATION" ||
    upper === "NOT_YET_RECRUITING";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[0.72rem] font-medium ${
        isActive
          ? "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300"
          : "bg-paper text-muted"
      }`}
    >
      {status || "—"}
    </span>
  );
}

function LocationLine({
  item,
  usBadge,
  intlBadge,
}: {
  item: TrialItem;
  usBadge: string;
  intlBadge: string;
}) {
  const parts: string[] = [];
  if (item.isUs) parts.push(`\u{1F1FA}\u{1F1F8} ${usBadge}`);
  if (item.isInternational) parts.push(`\u{1F30D} ${intlBadge}`);
  if (parts.length === 0 && item.locations.length > 0) {
    parts.push(item.locations[0]);
  }
  return (
    <span className="text-[0.8rem] text-muted">
      {parts.join(" · ") || "—"}
    </span>
  );
}

function TrialCard({
  item,
  labels,
  showIssues,
}: {
  item: TrialItem;
  labels: {
    ageLabel: string;
    phaseLabel: string;
    interventionLabel: string;
    locationLabel: string;
    usBadge: string;
    intlBadge: string;
    issuesLabel: string;
    viewOnCtgov: string;
    detailsLink: string;
  };
  showIssues: boolean;
}) {
  return (
    <div className="card p-5 space-y-3">
      {/* Header row */}
      <div className="flex flex-wrap items-start gap-2">
        <StatusBadge status={item.status} />
        {item.phase ? (
          <span className="inline-flex items-center rounded-full bg-paper px-2.5 py-0.5 text-[0.72rem] text-muted">
            {labels.phaseLabel}: {item.phase}
          </span>
        ) : null}
      </div>

      {/* Title — links to internal detail page */}
      {item.nctId ? (
        <Link
          href={`/research/trials/${item.nctId}`}
          className="block group"
        >
          <h3 className="font-serif text-lg leading-snug text-ink group-hover:text-accent group-hover:underline underline-offset-2">
            {item.title}
          </h3>
        </Link>
      ) : (
        <h3 className="font-serif text-lg leading-snug text-ink">{item.title}</h3>
      )}

      {/* Summary */}
      {item.summary ? (
        <p className="line-clamp-3 text-sm leading-relaxed text-muted">{item.summary}</p>
      ) : null}

      {/* Meta grid */}
      <dl className="grid grid-cols-[auto_1fr] items-baseline gap-x-3 gap-y-1 text-sm">
        {item.minAge || item.maxAge ? (
          <>
            <dt className="text-faint">{labels.ageLabel}</dt>
            <dd className="text-muted">
              {item.minAge || "?"} – {item.maxAge || "?"}
            </dd>
          </>
        ) : null}
        {item.intervention ? (
          <>
            <dt className="text-faint">{labels.interventionLabel}</dt>
            <dd className="text-muted">{item.intervention}</dd>
          </>
        ) : null}
        <dt className="text-faint">{labels.locationLabel}</dt>
        <dd>
          <LocationLine item={item} usBadge={labels.usBadge} intlBadge={labels.intlBadge} />
        </dd>
      </dl>

      {/* Issues (needs-review only) */}
      {showIssues && item.issues.length > 0 ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 dark:border-amber-800 dark:bg-amber-950">
          <p className="mb-1 text-[0.72rem] font-medium text-amber-700 dark:text-amber-300">
            {labels.issuesLabel}
          </p>
          <ul className="space-y-0.5">
            {item.issues.map((issue, i) => (
              <li key={i} className="text-[0.8rem] text-amber-800 dark:text-amber-200">
                {issue}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {/* Links row */}
      {item.nctId ? (
        <div className="flex flex-wrap items-center gap-4">
          <Link
            href={`/research/trials/${item.nctId}`}
            className="inline-flex items-center gap-1 text-sm text-ink hover:text-accent hover:underline"
          >
            {labels.detailsLink}
            <span aria-hidden="true">→</span>
          </Link>
          <a
            href={`https://clinicaltrials.gov/study/${item.nctId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-accent hover:text-accent-ink hover:underline"
          >
            {labels.viewOnCtgov}
            <span aria-hidden="true">↗</span>
          </a>
        </div>
      ) : null}
    </div>
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

  const cardLabels = {
    ageLabel: t("ageLabel"),
    phaseLabel: t("phaseLabel"),
    interventionLabel: t("interventionLabel"),
    locationLabel: t("locationLabel"),
    usBadge: t("usBadge"),
    intlBadge: t("intlBadge"),
    issuesLabel: t("issuesLabel"),
    viewOnCtgov: t("viewOnCtgov"),
    detailsLink: t("detailsLink"),
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
        <>
          {/* Eligible section */}
          <section className="space-y-4">
            <h2 className="text-base font-semibold text-ink">{t("eligibleHeading")}</h2>
            {eligible.length === 0 ? (
              <div className="rounded-xl border border-line bg-surface px-5 py-8 text-center">
                <p className="text-sm text-muted">{t("emptyEligible")}</p>
              </div>
            ) : (
              <ul className="space-y-3">
                {eligible.map((item) => (
                  <li key={item.nctId}>
                    <TrialCard item={item} labels={cardLabels} showIssues={false} />
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Needs-review section */}
          <section className="space-y-4">
            <div className="border-t border-line pt-8">
              <h2 className="text-base font-semibold text-muted">{t("needsReviewHeading")}</h2>
            </div>
            {needsReview.length === 0 ? (
              <div className="rounded-xl border border-line bg-surface px-5 py-6 text-center">
                <p className="text-sm text-faint">{t("emptyNeedsReview")}</p>
              </div>
            ) : (
              <ul className="space-y-3 opacity-80">
                {needsReview.map((item) => (
                  <li key={item.nctId}>
                    <TrialCard item={item} labels={cardLabels} showIssues={true} />
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
