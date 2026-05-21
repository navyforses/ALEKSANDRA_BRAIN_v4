import { setRequestLocale, getTranslations } from "next-intl/server";
import { getRows } from "@/lib/supabase";
import { displayField, type BilingualField } from "@/lib/i18n";

export const dynamic = "force-dynamic";

type Therapy = {
  id: string;
  name: BilingualField;             // 06-08: JSONB {en, ka} post-migration-012
  therapy_type: string | null;
  mechanism_of_action: string | null;
  evidence_in_hie: string | null;
  evidence_summary: BilingualField; // 06-08: nullable JSONB
  clinical_status: string | null;
  available_locations: string[] | null;
  approximate_cost: string | null;
  aleksandra_eligible: boolean | null;
  aleksandra_status: string | null;
  aleksandra_notes: string | null;
  optimal_age_window: string | null;
  time_sensitivity: string | null;
  ai_assessment: string | null;
  confidence_level: string | null;
  created_at: string | null;
};

function tone(value: string | null) {
  if (value === "proven" || value === "receiving" || value === "completed") {
    return "border-emerald-300 bg-emerald-50 text-emerald-900";
  }
  if (value === "promising" || value === "planned" || value === "applied" || value === "evaluating") {
    return "border-cyan-300 bg-cyan-50 text-cyan-900";
  }
  if (value === "disproven" || value === "ineligible" || value === "declined") {
    return "border-rose-300 bg-rose-50 text-rose-900";
  }
  return "border-stone-200 bg-white text-stone-800";
}

// Defensive parser: some `ai_assessment` rows are stringified dossier objects
// (e.g. {"source_hypothesis_id":..., "dossier":"..."}) due to upstream pipeline
// drift. Extract the actual `dossier` text when present; otherwise hide.
function extractAssessmentText(raw: string | null): string | null {
  if (!raw) return null;
  const trimmed = raw.trim();
  if (!trimmed.startsWith("{")) return raw; // plain text — render as-is
  try {
    const parsed = JSON.parse(trimmed);
    if (parsed && typeof parsed === "object" && typeof parsed.dossier === "string") {
      return parsed.dossier;
    }
    return null; // JSON without dossier — hide rather than dump raw object
  } catch {
    return null; // malformed JSON — hide
  }
}

export default async function TherapiesPage({
  params,
}: {
  params: Promise<{ locale: "en" | "ka" }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Therapies");
  const tShared = await getTranslations("Shared");

  function yesNo(value: boolean | null) {
    if (value == null) return tShared("unknown");
    return value ? tShared("yes") : tShared("no");
  }

  function listValue(values: string[] | null) {
    return values && values.length > 0 ? values.join(", ") : tShared("notListed");
  }

  const therapies = await getRows<Therapy>("therapies", {
    select:
      "id,name,therapy_type,mechanism_of_action,evidence_in_hie,evidence_summary,clinical_status,available_locations,approximate_cost,aleksandra_eligible,aleksandra_status,aleksandra_notes,optimal_age_window,time_sensitivity,ai_assessment,confidence_level,created_at",
    order: "name.asc",
    limit: 100,
  });

  const active = therapies.rows.filter((tr) => tr.aleksandra_status === "receiving").length;
  const watching = therapies.rows.filter((tr) =>
    ["planned", "applied", "evaluating"].includes(tr.aleksandra_status || ""),
  ).length;
  const promising = therapies.rows.filter((tr) => tr.evidence_in_hie === "promising").length;

  return (
    <main className="min-h-screen bg-stone-50 text-stone-950">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-5 py-6 sm:px-8">
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
          <div className="grid min-w-72 grid-cols-3 gap-3">
            <div className="rounded-md border border-stone-200 bg-white p-4">
              <p className="font-mono text-xs uppercase text-stone-500">{t("shown")}</p>
              <p className="mt-2 text-2xl font-semibold">{therapies.rows.length}</p>
            </div>
            <div className="rounded-md border border-stone-200 bg-white p-4">
              <p className="font-mono text-xs uppercase text-stone-500">{t("active")}</p>
              <p className="mt-2 text-2xl font-semibold">{active}</p>
            </div>
            <div className="rounded-md border border-stone-200 bg-white p-4">
              <p className="font-mono text-xs uppercase text-stone-500">{t("watching")}</p>
              <p className="mt-2 text-2xl font-semibold">{watching}</p>
            </div>
          </div>
        </header>

        {therapies.error ? (
          <section className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
            {therapies.error}
          </section>
        ) : null}

        <section className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-md border border-stone-200 bg-white p-4">
            <p className="font-mono text-xs uppercase text-stone-500">{t("promisingEvidence")}</p>
            <p className="mt-2 text-xl font-semibold">{promising}</p>
          </div>
          <div className="rounded-md border border-stone-200 bg-white p-4">
            <p className="font-mono text-xs uppercase text-stone-500">{t("eligibleYes")}</p>
            <p className="mt-2 text-xl font-semibold">
              {therapies.rows.filter((tr) => tr.aleksandra_eligible).length}
            </p>
          </div>
          <div className="rounded-md border border-stone-200 bg-white p-4">
            <p className="font-mono text-xs uppercase text-stone-500">{t("timeCritical")}</p>
            <p className="mt-2 text-xl font-semibold">
              {therapies.rows.filter((tr) => tr.time_sensitivity === "critical").length}
            </p>
          </div>
        </section>

        <section className="grid gap-4">
          {therapies.rows.map((therapy) => (
            <article key={therapy.id} className="rounded-md border border-stone-200 bg-white p-4">
              <div className="grid gap-4 lg:grid-cols-[1fr_auto]">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-md border px-2 py-1 font-mono text-xs ${tone(therapy.aleksandra_status)}`}>
                      {therapy.aleksandra_status || t("statusNotConsidered")}
                    </span>
                    <span className={`rounded-md border px-2 py-1 font-mono text-xs ${tone(therapy.evidence_in_hie)}`}>
                      {t("evidenceLabel")} {therapy.evidence_in_hie || t("evidenceUnknown")}
                    </span>
                    <span className="font-mono text-xs text-stone-500">
                      {therapy.therapy_type || t("typePending")}
                    </span>
                  </div>
                  <h2 className="mt-3 text-lg font-semibold leading-7">
                    {displayField(therapy.name, locale)}
                  </h2>
                  {therapy.mechanism_of_action ? (
                    <p className="mt-2 max-w-4xl text-sm leading-6 text-stone-700">
                      {therapy.mechanism_of_action}
                    </p>
                  ) : null}
                </div>
                <dl className="grid gap-3 text-sm sm:grid-cols-3 lg:w-96">
                  <div>
                    <dt className="font-mono text-xs uppercase text-stone-500">{t("eligible")}</dt>
                    <dd className="mt-1 font-semibold">{yesNo(therapy.aleksandra_eligible)}</dd>
                  </div>
                  <div>
                    <dt className="font-mono text-xs uppercase text-stone-500">{t("ageWindow")}</dt>
                    <dd className="mt-1 font-semibold">{therapy.optimal_age_window || tShared("na")}</dd>
                  </div>
                  <div>
                    <dt className="font-mono text-xs uppercase text-stone-500">{t("timing")}</dt>
                    <dd className="mt-1 font-semibold">{therapy.time_sensitivity || tShared("na")}</dd>
                  </div>
                </dl>
              </div>

              <div className="mt-4 grid gap-4 border-t border-stone-100 pt-4 lg:grid-cols-3">
                <div>
                  <p className="font-mono text-xs uppercase text-stone-500">{t("clinicalStatus")}</p>
                  <p className="mt-1 text-sm text-stone-700">{therapy.clinical_status || tShared("unknown")}</p>
                </div>
                <div>
                  <p className="font-mono text-xs uppercase text-stone-500">{t("locations")}</p>
                  <p className="mt-1 text-sm text-stone-700">{listValue(therapy.available_locations)}</p>
                </div>
                <div>
                  <p className="font-mono text-xs uppercase text-stone-500">{t("cost")}</p>
                  <p className="mt-1 text-sm text-stone-700">{therapy.approximate_cost || t("costUnknown")}</p>
                </div>
              </div>

              {(() => {
                const assessment = extractAssessmentText(therapy.ai_assessment);
                // 06-08: evidence_summary is JSONB; resolve to a string before truthiness gate
                const evidence = displayField(therapy.evidence_summary, locale);
                const hasAny = evidence || assessment || therapy.aleksandra_notes;
                if (!hasAny) return null;
                return (
                  <div className="mt-4 grid gap-3 border-t border-stone-100 pt-4">
                    {evidence ? (
                      <p className="text-sm leading-6 text-stone-700">{evidence}</p>
                    ) : null}
                    {assessment ? (
                      <p className="text-sm leading-6 text-stone-700">{assessment}</p>
                    ) : null}
                    {therapy.aleksandra_notes ? (
                      <p className="text-sm leading-6 text-stone-700">{therapy.aleksandra_notes}</p>
                    ) : null}
                  </div>
                );
              })()}
            </article>
          ))}
          {therapies.rows.length === 0 ? (
            <div className="rounded-md border border-stone-200 bg-white p-6 text-sm text-stone-500">
              {t("emptyList")}
            </div>
          ) : null}
        </section>
      </div>
    </main>
  );
}
