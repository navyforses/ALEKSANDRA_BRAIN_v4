import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { fetchTrialDetail, formatDate } from "@/lib/data";
import type { TrialDetail, TrialLocation } from "@/lib/data";
import { registryLabel, registryUrl, registryDisplayId } from "@/lib/registries";
import { buildCustomMetadata, type Locale } from "@/lib/seo";

// ---------------------------------------------------------------------------
// Metadata

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale; nctId: string }>;
}): Promise<Metadata> {
  const { locale, nctId } = await params;
  const { trial } = await fetchTrialDetail(locale, nctId);
  const title = trial
    ? `${trial.title} | ALEKSANDRA_BRAIN`
    : locale === "ka"
      ? "კვლევა ვერ მოიძებნა | ALEKSANDRA_BRAIN"
      : "Trial not found | ALEKSANDRA_BRAIN";
  const description =
    trial?.briefSummary ||
    (locale === "ka" ? "სამედიცინო კვლევის დეტალები" : "Clinical trial details");

  return buildCustomMetadata(locale, `/research/trials/${nctId}`, title, description);
}

// ---------------------------------------------------------------------------
// Pure helpers

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

function Chip({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center rounded-full bg-paper px-2.5 py-0.5 text-[0.72rem] text-muted">
      {label}
    </span>
  );
}

function SectionCard({
  heading,
  children,
}: {
  heading: string;
  children: React.ReactNode;
}) {
  return (
    <section className="card p-5 space-y-3">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-faint">{heading}</h2>
      {children}
    </section>
  );
}

function AssessmentCard({
  trial,
  statusLabel,
  issuesLabel,
}: {
  trial: TrialDetail;
  statusLabel: string;
  issuesLabel: string;
}) {
  const isEligible = trial.aleksandraStatus === "identified";
  const hasIssues = trial.eligibilityIssues.length > 0;

  return (
    <div
      className={`rounded-xl border px-5 py-4 space-y-3 ${
        isEligible
          ? "border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950"
          : "border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950"
      }`}
    >
      <p
        className={`text-sm font-semibold ${
          isEligible
            ? "text-green-700 dark:text-green-300"
            : "text-amber-700 dark:text-amber-300"
        }`}
      >
        {statusLabel}
      </p>
      {hasIssues ? (
        <div>
          <p
            className={`mb-1 text-[0.72rem] font-medium ${
              isEligible
                ? "text-green-600 dark:text-green-400"
                : "text-amber-600 dark:text-amber-400"
            }`}
          >
            {issuesLabel}
          </p>
          <ul className="space-y-0.5">
            {trial.eligibilityIssues.map((issue, i) => (
              <li
                key={i}
                className={`text-[0.8rem] ${
                  isEligible
                    ? "text-green-800 dark:text-green-200"
                    : "text-amber-800 dark:text-amber-200"
                }`}
              >
                {issue}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function LocationItem({ loc }: { loc: TrialLocation }) {
  const parts = [loc.facility, loc.city, loc.state, loc.country].filter(Boolean);
  const flag = loc.isUs ? "\u{1F1FA}\u{1F1F8}" : "\u{1F30D}";
  return (
    <li className="flex items-start gap-2 text-sm text-muted">
      <span className="mt-0.5 shrink-0">{flag}</span>
      <span>
        {parts.join(", ")}
        {loc.status ? (
          <span className="ml-2 inline-flex items-center rounded-full bg-paper px-2 py-0.5 text-[0.7rem] text-faint">
            {loc.status}
          </span>
        ) : null}
      </span>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Page component

export default async function TrialDetailPage({
  params,
}: {
  params: Promise<{ locale: Locale; nctId: string }>;
}) {
  const { locale, nctId } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Trials");

  const { configured, trial } = await fetchTrialDetail(locale, nctId);

  // --- not-found / not-configured states ---

  if (!configured || !trial) {
    return (
      <div className="space-y-6">
        <Link
          href="/research/trials"
          className="inline-flex items-center gap-1 text-sm text-muted hover:text-ink"
        >
          <span aria-hidden="true">←</span>
          {t("backToList")}
        </Link>
        <div className="rounded-xl border border-line bg-surface px-5 py-10 text-center">
          <p className="font-serif text-lg text-ink">{t("notFound")}</p>
          <p className="mt-2 text-sm text-muted">{t("notFoundNote")}</p>
        </div>
      </div>
    );
  }

  const aleksandraStatusLabel =
    trial.aleksandraStatus === "identified"
      ? t("statusEligible")
      : trial.aleksandraStatus === "evaluating"
        ? t("statusNeedsReview")
        : t("statusUnknown");

  const hasDetailedDesc = Boolean(trial.detailedDescription?.trim());
  const hasEligibilityCriteria = Boolean(trial.eligibilityCriteria?.trim());
  const hasLocations = trial.locations.length > 0;
  const hasContacts =
    Boolean(trial.piName) ||
    Boolean(trial.piEmail) ||
    Boolean(trial.coordinatorName) ||
    Boolean(trial.coordinatorEmail);
  const hasDates =
    Boolean(trial.startDate) ||
    Boolean(trial.estimatedCompletion) ||
    Boolean(trial.lastUpdated) ||
    Boolean(trial.lastChecked);

  return (
    <div className="space-y-8">
      {/* ------------------------------------------------------------------ */}
      {/* Header block                                                         */}
      {/* ------------------------------------------------------------------ */}
      <header className="u-rise max-w-3xl space-y-4">
        {/* Back link */}
        <Link
          href="/research/trials"
          className="inline-flex items-center gap-1 text-sm text-muted hover:text-ink"
        >
          <span aria-hidden="true">←</span>
          {t("backToList")}
        </Link>

        {/* Title */}
        <h1 className="font-serif text-[1.7rem] leading-snug tracking-tight text-ink">
          {trial.title}
        </h1>

        {/* Meta chips row */}
        <div className="flex flex-wrap items-center gap-2">
          {trial.status ? <StatusBadge status={trial.status} /> : null}
          {trial.phase ? <Chip label={`${t("phaseLabel")}: ${trial.phase}`} /> : null}
          {trial.studyType ? <Chip label={trial.studyType} /> : null}
          {trial.isUs ? (
            <span className="text-[0.8rem] text-muted">{"\u{1F1FA}\u{1F1F8}"} {t("usBadge")}</span>
          ) : null}
          {trial.isInternational ? (
            <span className="text-[0.8rem] text-muted">{"\u{1F30D}"} {t("intlBadge")}</span>
          ) : null}
          {/* Phase E: registry badge + id */}
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-flex items-center rounded-full bg-paper px-2.5 py-0.5 text-[0.72rem] font-medium text-muted">
              {registryLabel(trial.registry)}
            </span>
            <span className="font-mono text-[0.72rem] text-faint">
              {registryDisplayId(trial)}
            </span>
          </span>
        </div>

        {/* Phase E: registry-aware external link */}
        <div className="flex flex-wrap items-center gap-4">
          <a
            href={registryUrl(trial)}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-accent hover:text-accent-ink hover:underline"
          >
            {t("viewOnRegistry").replace("__REGISTRY__", registryLabel(trial.registry))}
            <span aria-hidden="true">↗</span>
          </a>
          {/* Cross-registry secondary ids — "Also listed as" */}
          {trial.secondaryIds.length > 0 ? (
            <span className="text-[0.8rem] text-faint">
              {t("alsoListedAs")}: {trial.secondaryIds.join(" · ")}
            </span>
          ) : null}
        </div>
      </header>

      {/* ------------------------------------------------------------------ */}
      {/* Eligibility-for-Aleksandra block (most important — placed first)     */}
      {/* ------------------------------------------------------------------ */}
      {trial.aleksandraStatus ? (
        <div className="max-w-3xl">
          <p className="mb-2 text-sm font-semibold text-ink">{t("sectionAssessment")}</p>
          <AssessmentCard
            trial={trial}
            statusLabel={aleksandraStatusLabel}
            issuesLabel={t("issuesLabel")}
          />
        </div>
      ) : null}

      {/* ------------------------------------------------------------------ */}
      {/* Summary block                                                        */}
      {/* ------------------------------------------------------------------ */}
      {trial.briefSummary ? (
        <div className="max-w-3xl">
          <SectionCard heading={t("sectionSummary")}>
            <p className="text-[0.95rem] leading-relaxed text-ink/90">{trial.briefSummary}</p>
          </SectionCard>
        </div>
      ) : null}

      {/* ------------------------------------------------------------------ */}
      {/* Detailed description block                                           */}
      {/* ------------------------------------------------------------------ */}
      {hasDetailedDesc ? (
        <div className="max-w-3xl">
          <SectionCard heading={t("sectionDescription")}>
            <div className="space-y-3">
              {trial.detailedDescription
                .split(/\n{2,}/)
                .filter(Boolean)
                .map((para, i) => (
                  <p key={i} className="text-[0.93rem] leading-relaxed text-ink/90">
                    {para}
                  </p>
                ))}
            </div>
          </SectionCard>
        </div>
      ) : null}

      {/* ------------------------------------------------------------------ */}
      {/* Eligibility criteria block                                           */}
      {/* ------------------------------------------------------------------ */}
      {hasEligibilityCriteria ? (
        <div className="max-w-3xl">
          <SectionCard heading={t("sectionEligibility")}>
            {/* Age + conditions sub-row */}
            {(trial.minAge || trial.maxAge || trial.conditions.length > 0) ? (
              <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2 pb-1 border-b border-line mb-3">
                {(trial.minAge || trial.maxAge) ? (
                  <dl className="flex items-baseline gap-1.5 text-sm">
                    <dt className="text-faint">{t("ageRange")}:</dt>
                    <dd className="text-muted">
                      {trial.minAge || "?"} – {trial.maxAge || "?"}
                    </dd>
                  </dl>
                ) : null}
                {trial.conditions.length > 0 ? (
                  <div className="flex flex-wrap items-center gap-1">
                    <span className="text-sm text-faint">{t("conditions")}:</span>
                    {trial.conditions.map((c, i) => (
                      <Chip key={i} label={c} />
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}

            {/* Full criteria text — preserve line structure */}
            <pre className="whitespace-pre-line text-[0.85rem] leading-relaxed text-muted font-sans">
              {trial.eligibilityCriteria}
            </pre>
          </SectionCard>
        </div>
      ) : null}

      {/* ------------------------------------------------------------------ */}
      {/* Locations block                                                      */}
      {/* ------------------------------------------------------------------ */}
      {hasLocations ? (
        <div className="max-w-3xl">
          <SectionCard heading={t("sectionLocations")}>
            <ul className="space-y-2">
              {trial.locations.map((loc, i) => (
                <LocationItem key={i} loc={loc} />
              ))}
            </ul>
          </SectionCard>
        </div>
      ) : null}

      {/* ------------------------------------------------------------------ */}
      {/* Contacts block                                                       */}
      {/* ------------------------------------------------------------------ */}
      {hasContacts ? (
        <div className="max-w-3xl">
          <SectionCard heading={t("sectionContacts")}>
            <dl className="space-y-2 text-sm">
              {(trial.piName || trial.piEmail) ? (
                <div className="flex flex-wrap gap-x-3 gap-y-0.5">
                  <dt className="text-faint">{t("principalInvestigator")}:</dt>
                  <dd className="text-muted">
                    {trial.piName || ""}
                    {trial.piEmail ? (
                      <>
                        {trial.piName ? " · " : ""}
                        <a
                          href={`mailto:${trial.piEmail}`}
                          className="text-accent hover:underline"
                        >
                          {trial.piEmail}
                        </a>
                      </>
                    ) : null}
                  </dd>
                </div>
              ) : null}
              {(trial.coordinatorName || trial.coordinatorEmail) ? (
                <div className="flex flex-wrap gap-x-3 gap-y-0.5">
                  <dt className="text-faint">{t("coordinator")}:</dt>
                  <dd className="text-muted">
                    {trial.coordinatorName || ""}
                    {trial.coordinatorEmail ? (
                      <>
                        {trial.coordinatorName ? " · " : ""}
                        <a
                          href={`mailto:${trial.coordinatorEmail}`}
                          className="text-accent hover:underline"
                        >
                          {trial.coordinatorEmail}
                        </a>
                      </>
                    ) : null}
                  </dd>
                </div>
              ) : null}
            </dl>
          </SectionCard>
        </div>
      ) : null}

      {/* ------------------------------------------------------------------ */}
      {/* Dates block                                                          */}
      {/* ------------------------------------------------------------------ */}
      {hasDates ? (
        <div className="max-w-3xl">
          <SectionCard heading={t("sectionDates")}>
            <dl className="grid grid-cols-[auto_1fr] items-baseline gap-x-4 gap-y-1.5 text-sm">
              {trial.startDate ? (
                <>
                  <dt className="text-faint">{t("startDate")}:</dt>
                  <dd className="text-muted">{formatDate(trial.startDate, locale)}</dd>
                </>
              ) : null}
              {trial.estimatedCompletion ? (
                <>
                  <dt className="text-faint">{t("completionDate")}:</dt>
                  <dd className="text-muted">{formatDate(trial.estimatedCompletion, locale)}</dd>
                </>
              ) : null}
              {trial.lastUpdated ? (
                <>
                  <dt className="text-faint">{t("lastUpdated")}:</dt>
                  <dd className="text-muted">{formatDate(trial.lastUpdated, locale)}</dd>
                </>
              ) : null}
              {trial.lastChecked ? (
                <>
                  <dt className="text-faint">{t("asOf")}:</dt>
                  <dd className="text-muted">{formatDate(trial.lastChecked, locale)}</dd>
                </>
              ) : null}
            </dl>
          </SectionCard>
        </div>
      ) : null}
    </div>
  );
}
