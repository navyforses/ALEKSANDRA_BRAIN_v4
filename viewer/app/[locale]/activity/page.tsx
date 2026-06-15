import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { buildCustomMetadata, type Locale } from "@/lib/seo";
import { fetchSystemLifeline } from "@/lib/data";
import LifelineRail from "@/components/activity/LifelineRail";
import LiveRefresher from "@/components/activity/LiveRefresher";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return buildCustomMetadata(
    locale,
    "/activity",
    locale === "ka"
      ? "სიცოცხლის ხაზი | ALEKSANDRA_BRAIN"
      : "System Lifeline | ALEKSANDRA_BRAIN",
    locale === "ka"
      ? "ყოველი ინფორმაცია, რომელიც სისტემამ შემოიტანა — როდის შემოვიდა და საიდან."
      : "Every piece of information the system has added — when it arrived and where it came from.",
  );
}

// ---------------------------------------------------------------------------
// Relative "last updated" formatter — purely in JS (server-side).
// ---------------------------------------------------------------------------

function relativeUpdated(iso: string | null, locale: Locale): string {
  if (!iso) return "";
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 60_000) return locale === "ka" ? "ახლახ" : "just now";
  if (ms < 3_600_000) {
    const m = Math.floor(ms / 60_000);
    return locale === "ka" ? `${m} წთ წინ` : `${m}m ago`;
  }
  if (ms < 86_400_000) {
    const h = Math.floor(ms / 3_600_000);
    return locale === "ka" ? `${h} სთ წინ` : `${h}h ago`;
  }
  return new Intl.DateTimeFormat(locale === "ka" ? "ka-GE" : "en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

// ---------------------------------------------------------------------------

export default async function ActivityPage({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Activity");

  const lifeline = await fetchSystemLifeline();

  const updatedLabel = lifeline.lastUpdated
    ? t("lastUpdated", { time: relativeUpdated(lifeline.lastUpdated, locale) })
    : "";

  const totalsLabel =
    lifeline.days.length > 0
      ? t("totals", {
          items: lifeline.totalItems.toLocaleString(locale === "ka" ? "ka-GE" : "en-US"),
          days: lifeline.days.length,
        })
      : "";

  const nowLabel = t("liveNow");

  return (
    <div className="space-y-8">
      {/* Auto-refresh: silently calls router.refresh() every 90s */}
      <LiveRefresher />

      {/* Page header */}
      <header className="u-rise max-w-2xl">
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="font-serif text-[1.9rem] leading-tight tracking-tight text-ink">
            {t("title")}
          </h1>
          {lifeline.configured && lifeline.lastUpdated ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-signal-soft px-3 py-1 text-xs font-medium text-signal">
              {/* Live dot */}
              <span
                aria-hidden
                className="relative flex h-2 w-2 items-center justify-center"
              >
                <span className="dot-breathe absolute h-2 w-2 rounded-full bg-signal" />
              </span>
              {t("liveNow")}
            </span>
          ) : null}
        </div>

        <p className="mt-3 text-[0.98rem] leading-relaxed text-muted">
          {t("subtitle")}
        </p>

        {/* Last updated + totals */}
        <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-faint">
          {updatedLabel ? <span>{updatedLabel}</span> : null}
          {totalsLabel ? (
            <>
              {updatedLabel ? <span aria-hidden>·</span> : null}
              <span>{totalsLabel}</span>
            </>
          ) : null}
        </div>
      </header>

      {/* Body */}
      <div className="u-rise u-rise-1">
        {!lifeline.configured ? (
          <div className="rounded-xl border border-line bg-surface px-5 py-12 text-center">
            <p className="text-sm text-muted">{t("notConfigured")}</p>
            <p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-faint">
              {t("notConfiguredNote")}
            </p>
          </div>
        ) : lifeline.days.length === 0 && lifeline.milestones.length === 0 ? (
          <div className="rounded-xl border border-line bg-surface px-5 py-12 text-center">
            <p className="text-sm text-muted">{t("noData")}</p>
            <p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-faint">
              {t("noDataNote")}
            </p>
          </div>
        ) : (
          <div className="max-w-lg">
            <LifelineRail
              days={lifeline.days}
              milestones={lifeline.milestones}
              locale={locale}
              nowLabel={nowLabel}
            />
          </div>
        )}
      </div>
    </div>
  );
}
