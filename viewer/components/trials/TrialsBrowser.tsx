"use client";

// Phase D — Country filter + sort + enriched card for the clinical trials list.
// Receives server-fetched data and all translated label strings as props so
// this component never calls useTranslations() for dynamic country names.

import { useMemo, useState } from "react";
import { Link } from "@/i18n/navigation";
import type { TrialItem } from "@/lib/data";
import { localizeCountry, sortCountries } from "@/lib/countries";
import { registryLabel, registryUrl, registryDisplayId } from "@/lib/registries";
import type { Locale } from "@/lib/seo";

// ---------------------------------------------------------------------------
// Types

interface BrowserLabels {
  // existing
  ageLabel: string;
  phaseLabel: string;
  interventionLabel: string;
  locationLabel: string;
  usBadge: string;
  intlBadge: string;
  issuesLabel: string;
  /** @deprecated kept for compat — use viewOnRegistry instead */
  viewOnCtgov: string;
  /** Phase E: "View on {registry}" template — caller interpolates registry label. */
  viewOnRegistry: string;
  detailsLink: string;
  eligibleHeading: string;
  needsReviewHeading: string;
  emptyEligible: string;
  emptyNeedsReview: string;
  // new Phase D
  filterCountry: string;
  allCountries: string;
  sortBy: string;
  sortUsFirst: string;
  sortCountryAz: string;
  sortSoonest: string;
  sortRecent: string;
  startsLabel: string;
  conductedAt: string;
  moreSites: string;
  contactLabel: string;
  noMatches: string;
}

type SortKey = "us-first" | "country-az" | "soonest" | "recent";

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

function LocationBadge({
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
    <span className="text-[0.8rem] text-muted">{parts.join(" · ") || "—"}</span>
  );
}

// ---------------------------------------------------------------------------
// Enriched card

function TrialCard({
  item,
  labels,
  showIssues,
  locale,
}: {
  item: TrialItem;
  labels: BrowserLabels;
  showIssues: boolean;
  locale: Locale;
}) {
  // Primary location display: "{city}, {country}" with +N hint
  const extraSites = item.locationStructs.length - 1;
  const primaryDisplay = item.primaryLocation
    ? [item.primaryLocation.city, localizeCountry(item.primaryLocation.country, locale)]
        .filter(Boolean)
        .join(", ")
    : null;

  // Contact: prefer coordinator, fall back to PI
  const contactName = item.coordinatorName || item.piName || null;
  const contactEmail = item.coordinatorEmail || item.piEmail || null;

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

      {/* Title — internal link uses registryId (the universal per-registry id) */}
      {item.registryId ? (
        <Link href={`/research/trials/${item.registryId}`} className="block group">
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
        {/* Age */}
        {item.minAge || item.maxAge ? (
          <>
            <dt className="text-faint">{labels.ageLabel}</dt>
            <dd className="text-muted">
              {item.minAge || "?"} – {item.maxAge || "?"}
            </dd>
          </>
        ) : null}

        {/* Intervention */}
        {item.intervention ? (
          <>
            <dt className="text-faint">{labels.interventionLabel}</dt>
            <dd className="text-muted">{item.intervention}</dd>
          </>
        ) : null}

        {/* Location (legacy flag badges) */}
        <dt className="text-faint">{labels.locationLabel}</dt>
        <dd>
          <LocationBadge item={item} usBadge={labels.usBadge} intlBadge={labels.intlBadge} />
        </dd>

        {/* Phase D: where conducted */}
        {primaryDisplay ? (
          <>
            <dt className="text-faint">{labels.conductedAt}</dt>
            <dd className="text-muted">
              {primaryDisplay}
              {extraSites > 0 ? (
                <span className="ml-1.5 text-faint">
                  +{extraSites} {labels.moreSites}
                </span>
              ) : null}
            </dd>
          </>
        ) : null}

        {/* Phase D: start date */}
        {item.startDate ? (
          <>
            <dt className="text-faint">{labels.startsLabel}</dt>
            <dd className="text-muted">{item.startDate}</dd>
          </>
        ) : null}

        {/* Phase D: contact */}
        {contactName || contactEmail ? (
          <>
            <dt className="text-faint">{labels.contactLabel}</dt>
            <dd className="text-muted">
              {contactEmail ? (
                <a
                  href={`mailto:${contactEmail}`}
                  className="hover:text-accent hover:underline underline-offset-2"
                >
                  {contactName || contactEmail}
                </a>
              ) : (
                contactName
              )}
            </dd>
          </>
        ) : null}
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

      {/* Links row — registry-aware (Phase E) */}
      {item.registryId ? (
        <div className="flex flex-wrap items-center gap-4">
          {/* Registry badge + displayed id */}
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-flex items-center rounded-full bg-paper px-2.5 py-0.5 text-[0.72rem] font-medium text-muted">
              {registryLabel(item.registry)}
            </span>
            <span className="font-mono text-[0.72rem] text-faint">
              {registryDisplayId(item)}
            </span>
          </span>

          <Link
            href={`/research/trials/${item.registryId}`}
            className="inline-flex items-center gap-1 text-sm text-ink hover:text-accent hover:underline"
          >
            {labels.detailsLink}
            <span aria-hidden="true">→</span>
          </Link>
          <a
            href={registryUrl(item)}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-sm text-accent hover:text-accent-ink hover:underline"
          >
            {labels.viewOnRegistry.replace("__REGISTRY__", registryLabel(item.registry))}
            <span aria-hidden="true">↗</span>
          </a>
        </div>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Filter + sort logic

const US_CANONICAL = "United States";

function sortItems(items: TrialItem[], key: SortKey): TrialItem[] {
  const copy = [...items];
  switch (key) {
    case "us-first":
      return copy.sort((a, b) => {
        const aUs = a.isUs ? 0 : 1;
        const bUs = b.isUs ? 0 : 1;
        return aUs - bUs;
      });
    case "country-az":
      return copy.sort((a, b) => {
        const aC = a.primaryLocation?.country ?? "";
        const bC = b.primaryLocation?.country ?? "";
        return aC.localeCompare(bC, "en-US");
      });
    case "soonest":
      return copy.sort((a, b) => {
        if (!a.startDate && !b.startDate) return 0;
        if (!a.startDate) return 1; // nulls last
        if (!b.startDate) return -1;
        return new Date(a.startDate).getTime() - new Date(b.startDate).getTime();
      });
    case "recent":
      return copy.sort((a, b) => {
        const aD = a.lastChecked ?? "";
        const bD = b.lastChecked ?? "";
        return bD.localeCompare(aD);
      });
    default:
      return copy;
  }
}

function filterByCountry(items: TrialItem[], selected: Set<string>): TrialItem[] {
  if (selected.has("__all__")) return items;
  return items.filter((item) =>
    item.countries.some((c) => selected.has(c)),
  );
}

// ---------------------------------------------------------------------------
// TrialsBrowser

export default function TrialsBrowser({
  eligible,
  needsReview,
  labels,
  locale,
}: {
  eligible: TrialItem[];
  needsReview: TrialItem[];
  labels: BrowserLabels;
  locale: Locale;
}) {
  const allItems = useMemo(() => [...eligible, ...needsReview], [eligible, needsReview]);

  // Build the union of all unique countries, US first then A–Z.
  const allCountries = useMemo(() => {
    const seen = new Set<string>();
    for (const item of allItems) {
      for (const c of item.countries) {
        if (c) seen.add(c);
      }
    }
    return sortCountries(Array.from(seen), locale);
  }, [allItems, locale]);

  // Country counts (for the chip labels).
  const countryCounts = useMemo(() => {
    const map = new Map<string, number>();
    for (const item of allItems) {
      for (const c of item.countries) {
        if (c) map.set(c, (map.get(c) ?? 0) + 1);
      }
    }
    return map;
  }, [allItems]);

  const [selectedCountries, setSelectedCountries] = useState<Set<string>>(
    new Set(["__all__"]),
  );
  const [sortKey, setSortKey] = useState<SortKey>("us-first");

  function toggleCountry(country: string) {
    setSelectedCountries((prev) => {
      const next = new Set(prev);
      if (country === "__all__") {
        return new Set(["__all__"]);
      }
      next.delete("__all__");
      if (next.has(country)) {
        next.delete(country);
        if (next.size === 0) return new Set(["__all__"]);
      } else {
        next.add(country);
      }
      return next;
    });
  }

  const filteredEligible = useMemo(
    () => sortItems(filterByCountry(eligible, selectedCountries), sortKey),
    [eligible, selectedCountries, sortKey],
  );
  const filteredNeedsReview = useMemo(
    () => sortItems(filterByCountry(needsReview, selectedCountries), sortKey),
    [needsReview, selectedCountries, sortKey],
  );

  const sortOptions: { key: SortKey; label: string }[] = [
    { key: "us-first", label: labels.sortUsFirst },
    { key: "country-az", label: labels.sortCountryAz },
    { key: "soonest", label: labels.sortSoonest },
    { key: "recent", label: labels.sortRecent },
  ];

  return (
    <div className="space-y-8">
      {/* Controls bar */}
      {allCountries.length > 0 ? (
        <div className="space-y-4">
          {/* Country filter */}
          <fieldset>
            <legend className="mb-2 text-sm font-medium text-ink">
              {labels.filterCountry}
            </legend>
            <div className="flex flex-wrap gap-2">
              {/* All chip */}
              <button
                type="button"
                aria-pressed={selectedCountries.has("__all__")}
                onClick={() => toggleCountry("__all__")}
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm transition-colors ${
                  selectedCountries.has("__all__")
                    ? "bg-ink text-paper"
                    : "border border-line text-muted hover:text-ink"
                }`}
              >
                {labels.allCountries}
              </button>
              {allCountries.map((country) => {
                const active = selectedCountries.has(country);
                const count = countryCounts.get(country) ?? 0;
                const label = localizeCountry(country, locale);
                return (
                  <button
                    key={country}
                    type="button"
                    aria-pressed={active}
                    onClick={() => toggleCountry(country)}
                    className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm transition-colors ${
                      active
                        ? "bg-ink text-paper"
                        : "border border-line text-muted hover:text-ink"
                    }`}
                  >
                    {country.toLowerCase() === "united states" ||
                    country.toLowerCase() === "usa"
                      ? `\u{1F1FA}\u{1F1F8} ${label}`
                      : label}
                    <span className={active ? "text-paper/70" : "text-faint"}>
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>
          </fieldset>

          {/* Sort control */}
          <div className="flex items-center gap-3">
            <label
              htmlFor="trials-sort"
              className="whitespace-nowrap text-sm text-muted"
            >
              {labels.sortBy}
            </label>
            <select
              id="trials-sort"
              value={sortKey}
              onChange={(e) => setSortKey(e.target.value as SortKey)}
              className="rounded-lg border border-line bg-surface px-3 py-1.5 text-sm text-ink focus:border-accent-line focus:outline-none"
            >
              {sortOptions.map((opt) => (
                <option key={opt.key} value={opt.key}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      ) : null}

      {/* Eligible section */}
      <section className="space-y-4">
        <h2 className="text-base font-semibold text-ink">
          {labels.eligibleHeading}
          <span className="ml-2 text-sm font-normal text-muted">
            ({filteredEligible.length})
          </span>
        </h2>
        {filteredEligible.length === 0 ? (
          <div className="rounded-xl border border-line bg-surface px-5 py-8 text-center">
            <p className="text-sm text-muted">
              {selectedCountries.has("__all__")
                ? labels.emptyEligible
                : labels.noMatches}
            </p>
          </div>
        ) : (
          <ul className="space-y-3">
            {filteredEligible.map((item) => (
              <li key={item.registryId || item.nctId}>
                <TrialCard
                  item={item}
                  labels={labels}
                  showIssues={false}
                  locale={locale}
                />
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Needs-review section */}
      <section className="space-y-4">
        <div className="border-t border-line pt-8">
          <h2 className="text-base font-semibold text-muted">
            {labels.needsReviewHeading}
            <span className="ml-2 text-sm font-normal text-faint">
              ({filteredNeedsReview.length})
            </span>
          </h2>
        </div>
        {filteredNeedsReview.length === 0 ? (
          <div className="rounded-xl border border-line bg-surface px-5 py-6 text-center">
            <p className="text-sm text-faint">
              {selectedCountries.has("__all__")
                ? labels.emptyNeedsReview
                : labels.noMatches}
            </p>
          </div>
        ) : (
          <ul className="space-y-3 opacity-80">
            {filteredNeedsReview.map((item) => (
              <li key={item.registryId || item.nctId}>
                <TrialCard
                  item={item}
                  labels={labels}
                  showIssues={true}
                  locale={locale}
                />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
