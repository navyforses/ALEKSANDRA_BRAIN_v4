import { setRequestLocale, getTranslations } from "next-intl/server";
import { getRows } from "@/lib/supabase";
import { displayField, type BilingualField } from "@/lib/i18n";

export const dynamic = "force-dynamic";

type TimelineEvent = {
  id: string;
  event_date: string;
  event_type: string;
  title: BilingualField;         // 06-08: JSONB {en, ka} post-migration-012
  description: BilingualField;   // 06-08: nullable JSONB
  institution: string | null;
  location: string | null;
  created_at: string;
  updated_at: string;
};

function typeCounts(events: TimelineEvent[]) {
  return events.reduce<Record<string, number>>((acc, event) => {
    acc[event.event_type] = (acc[event.event_type] || 0) + 1;
    return acc;
  }, {});
}

export default async function TimelinePage({
  params,
}: {
  params: Promise<{ locale: "en" | "ka" }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Timeline");
  const tShared = await getTranslations("Shared");

  function formatDate(value: string | null) {
    if (!value) return tShared("notListed");
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toISOString().slice(0, 10);
  }

  const events = await getRows<TimelineEvent>("aleksandra_timeline", {
    select: "id,event_date,event_type,title,description,institution,location,created_at,updated_at",
    order: "event_date.desc",
    limit: 100,
  });
  const counts = typeCounts(events.rows);

  return (
    <main className="min-h-screen bg-stone-50 text-stone-950">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-5 py-6 sm:px-8">
        <header className="grid gap-4 lg:grid-cols-[1fr_auto]">
          <div>
            <p className="font-mono text-xs uppercase text-cyan-700">{t("phaseLabel")}</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-normal sm:text-4xl">
              {t("title")}
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-stone-600">
              {t("subtitle")}
            </p>
          </div>
          <div className="grid min-w-64 grid-cols-2 gap-3">
            <div className="rounded-md border border-stone-200 bg-white p-4">
              <p className="font-mono text-xs uppercase text-stone-500">{t("shown")}</p>
              <p className="mt-2 text-2xl font-semibold">{events.rows.length}</p>
            </div>
            <div className="rounded-md border border-stone-200 bg-white p-4">
              <p className="font-mono text-xs uppercase text-stone-500">{t("latest")}</p>
              <p className="mt-2 text-2xl font-semibold">{formatDate(events.rows[0]?.event_date ?? null)}</p>
            </div>
          </div>
        </header>

        {events.error ? (
          <section className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
            {events.error}
          </section>
        ) : null}

        {Object.keys(counts).length > 0 ? (
          <section className="flex flex-wrap gap-2">
            {Object.entries(counts).map(([type, count]) => (
              <span key={type} className="rounded-md bg-white px-3 py-2 text-sm text-stone-700 ring-1 ring-stone-200">
                <span className="font-mono text-xs uppercase text-stone-500">{type}</span>{" "}
                <span className="font-semibold">{count}</span>
              </span>
            ))}
          </section>
        ) : null}

        <section className="rounded-md border border-stone-200 bg-white">
          <div className="border-b border-stone-200 p-4">
            <h2 className="text-base font-semibold">{t("events")}</h2>
          </div>
          <div className="divide-y divide-stone-100">
            {events.rows.map((event) => (
              <article key={event.id} className="grid gap-4 p-4 md:grid-cols-[9rem_1fr]">
                <div>
                  <p className="font-mono text-sm font-semibold text-cyan-700">
                    {formatDate(event.event_date)}
                  </p>
                  <p className="mt-1 font-mono text-xs uppercase text-stone-500">
                    {event.event_type}
                  </p>
                </div>
                <div>
                  <h3 className="text-base font-semibold leading-7">
                    {displayField(event.title, locale)}
                  </h3>
                  {event.description ? (
                    <p className="mt-2 max-w-4xl text-sm leading-6 text-stone-700">
                      {displayField(event.description, locale)}
                    </p>
                  ) : null}
                  <p className="mt-2 text-xs text-stone-500">
                    {[event.institution, event.location].filter(Boolean).join(" | ") || t("locationPending")}
                  </p>
                </div>
              </article>
            ))}
            {events.rows.length === 0 ? (
              <p className="p-4 text-sm text-stone-500">{t("emptyList")}</p>
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}
