import type { Metadata } from "next";
import { buildCustomMetadata, type Locale } from "@/lib/seo";
import { notFound } from "next/navigation";
import { setRequestLocale, getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { reviewHypothesis } from "../actions";
import { getRows } from "@/lib/supabase";
import { displayField, type BilingualField } from "@/lib/i18n";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale; id: string }>;
}): Promise<Metadata> {
  const { locale, id } = await params;
  const hypotheses = await getRows<HypothesisDetail>("hypotheses", {
    select: "id,title,description",
    id: `eq.${id}`,
    limit: 1,
  });
  const hypothesis = hypotheses.rows[0];
  const path = `/hypotheses/${id}`;
  const fallbackTitle = locale === "ka" ? "ჰიპოთეზის დეტალი | ALEKSANDRA_BRAIN" : "Hypothesis Detail | ALEKSANDRA_BRAIN";
  const title = hypothesis ? `${displayField(hypothesis.title, locale)} | ALEKSANDRA_BRAIN` : fallbackTitle;
  const description = hypothesis
    ? `ჰიპოთეზის დეტალური გვერდი აჩვენებს evidence-ს, კლინიკური განხილვის კონტექსტს და next action-ს: ${displayField(hypothesis.description, locale).slice(0, 120)}`
    : "ჰიპოთეზის დეტალური გვერდი აჩვენებს evidence-ს, კლინიკური განხილვის კონტექსტს და next action-ს.";

  return buildCustomMetadata(locale, path, title, description);
}


type HypothesisDetail = {
  id: string;
  title: BilingualField;          // 06-08: JSONB {en, ka} post-migration-012
  description: BilingualField;    // 06-08: JSONB {en, ka} post-migration-012
  hypothesis_type: string | null;
  confidence_level: string | null;
  novelty_score: number | null;
  feasibility_score: number | null;
  urgency: string | null;
  status: string | null;
  reviewed_at: string | null;
  outcome: string | null;
  recommended_action: string | null;
  ai_reasoning: string | null;
  discovery_method: string | null;
  supporting_papers: string[] | null;
  contradicting_papers: string[] | null;
  related_therapies: string[] | null;
  generated_by: string | null;
  created_at: string;
};

type SupportingPaper = {
  id: string;
  title: string | null;
  pmid: string | null;
  ct_id: string | null;
  doi: string | null;
  source: string | null;
  relevance_score: number | null;
  direct_relevance: boolean | null;
  cross_disease_source: string | null;
};

type RelatedTherapy = {
  id: string;
  name: BilingualField;           // 06-08: JSONB {en, ka} post-migration-012
  therapy_type: string | null;
  evidence_in_hie: string | null;
  aleksandra_status: string | null;
};

function tone(status: string | null) {
  if (status === "confirmed")
    return "border-emerald-300 bg-emerald-50 text-emerald-900";
  if (status === "promising" || status === "pursuing")
    return "border-cyan-300 bg-cyan-50 text-cyan-900";
  if (status === "rejected")
    return "border-rose-300 bg-rose-50 text-rose-900";
  return "border-stone-200 bg-white text-stone-900";
}

// PostgREST `in.(...)` filter needs comma-separated UUIDs. Empty array
// → emit a sentinel UUID that will never match, so getRows returns [].
function inFilter(ids: string[] | null | undefined): string {
  const safe = (ids ?? []).filter(Boolean);
  if (safe.length === 0) {
    return "in.(00000000-0000-0000-0000-000000000000)";
  }
  return `in.(${safe.join(",")})`;
}

export default async function HypothesisDetailPage({
  params,
}: {
  params: Promise<{ locale: "en" | "ka"; id: string }>;
}) {
  const { locale, id } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Hypotheses");
  const tNav = await getTranslations("Navigation");
  const tPapers = await getTranslations("Papers");
  const tTherapies = await getTranslations("Therapies");
  const tShared = await getTranslations("Shared");
  const tStatus = await getTranslations("HypothesisStatus");
  const tType = await getTranslations("HypothesisType");
  const tConf = await getTranslations("ConfidenceLevel");

  function score(value: number | null) {
    return value == null ? tShared("na") : value.toFixed(2);
  }

  const hypotheses = await getRows<HypothesisDetail>("hypotheses", {
    select:
      "id,title,description,hypothesis_type,confidence_level,novelty_score,feasibility_score,urgency,status,reviewed_at,outcome,recommended_action,ai_reasoning,discovery_method,supporting_papers,contradicting_papers,related_therapies,generated_by,created_at",
    id: `eq.${id}`,
    limit: 1,
  });

  const hypothesis = hypotheses.rows[0];
  if (hypotheses.error) {
    return (
      <main className="min-h-screen bg-stone-50 px-6 py-10 text-stone-900">
        <p className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm">
          {hypotheses.error}
        </p>
      </main>
    );
  }
  if (!hypothesis) {
    notFound();
  }

  const [papers, therapies] = await Promise.all([
    getRows<SupportingPaper>("papers", {
      select:
        "id,title,pmid,ct_id,doi,source,relevance_score,direct_relevance,cross_disease_source",
      id: inFilter(hypothesis.supporting_papers),
      order: "relevance_score.desc.nullslast",
      limit: 50,
    }),
    getRows<RelatedTherapy>("therapies", {
      select: "id,name,therapy_type,evidence_in_hie,aleksandra_status",
      id: inFilter(hypothesis.related_therapies),
      limit: 50,
    }),
  ]);

  return (
    <main className="min-h-screen bg-stone-50 text-stone-950">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-5 py-6 sm:px-8">
        <nav className="flex flex-wrap items-center justify-between gap-3 border-b border-stone-200 pb-4">
          <Link
            href="/"
            className="font-mono text-sm font-semibold tracking-normal"
          >
            ALEKSANDRA_BRAIN
          </Link>
          <div className="flex items-center gap-2 text-sm">
            <Link
              className="rounded-md px-3 py-2 text-stone-700 hover:bg-white"
              href="/dashboard"
            >
              {tNav("dashboard")}
            </Link>
            <Link
              className="rounded-md px-3 py-2 text-stone-700 hover:bg-white"
              href="/hypotheses"
            >
              {tNav("hypotheses")}
            </Link>
          </div>
        </nav>

        <header className="grid gap-3">
          <Link
            href="/hypotheses"
            className="font-mono text-xs uppercase text-cyan-700 hover:underline"
          >
            ← {t("backToList")}
          </Link>
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-md border px-2 py-1 font-mono text-xs ${tone(hypothesis.status)}`}
            >
              {hypothesis.status ? (tStatus.has(hypothesis.status) ? tStatus(hypothesis.status) : hypothesis.status) : t("statusNew")}
            </span>
            <span className="font-mono text-xs text-stone-500">
              {hypothesis.hypothesis_type ? (tType.has(hypothesis.hypothesis_type) ? tType(hypothesis.hypothesis_type) : hypothesis.hypothesis_type) : t("typeOther")}
            </span>
            {hypothesis.urgency ? (
              <span className="font-mono text-xs text-stone-500">
                · {t("urgencyPrefix")}: {hypothesis.urgency}
              </span>
            ) : null}
            {hypothesis.generated_by ? (
              <span className="font-mono text-xs text-stone-500">
                · {t("genPrefix")}: {hypothesis.generated_by}
              </span>
            ) : null}
          </div>
          <h1 className="text-2xl font-semibold tracking-normal sm:text-3xl">
            {displayField(hypothesis.title, locale)}
          </h1>
          <p className="max-w-4xl text-sm leading-6 text-stone-700">
            {displayField(hypothesis.description, locale)}
          </p>
        </header>

        <section className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-md border border-stone-200 bg-white p-4">
            <p className="font-mono text-xs uppercase text-stone-500">
              {t("confidence")}
            </p>
            <p className="mt-2 text-xl font-semibold">
              {hypothesis.confidence_level ? (tConf.has(hypothesis.confidence_level) ? tConf(hypothesis.confidence_level) : hypothesis.confidence_level) : tShared("na")}
            </p>
          </div>
          <div className="rounded-md border border-stone-200 bg-white p-4">
            <p className="font-mono text-xs uppercase text-stone-500">
              {t("novelty")}
            </p>
            <p className="mt-2 text-xl font-semibold">
              {score(hypothesis.novelty_score)}
            </p>
          </div>
          <div className="rounded-md border border-stone-200 bg-white p-4">
            <p className="font-mono text-xs uppercase text-stone-500">
              {t("feasibility")}
            </p>
            <p className="mt-2 text-xl font-semibold">
              {score(hypothesis.feasibility_score)}
            </p>
          </div>
        </section>

        {hypothesis.recommended_action ? (
          <section className="rounded-md border border-stone-200 bg-white p-4">
            <p className="font-mono text-xs uppercase text-stone-500">
              {t("recommendedAction")}
            </p>
            <p className="mt-2 text-sm leading-6 text-stone-800">
              {hypothesis.recommended_action}
            </p>
          </section>
        ) : null}

        {hypothesis.ai_reasoning ? (
          <section className="rounded-md border border-stone-200 bg-white p-4">
            <p className="font-mono text-xs uppercase text-stone-500">
              {t("reasoning")}
              {hypothesis.discovery_method ? (
                <span className="ml-2 text-stone-400">
                  · {hypothesis.discovery_method}
                </span>
              ) : null}
            </p>
            <pre className="mt-2 whitespace-pre-wrap font-sans text-sm leading-6 text-stone-800">
              {hypothesis.ai_reasoning}
            </pre>
          </section>
        ) : null}

        <section className="rounded-md border border-stone-200 bg-white">
          <div className="border-b border-stone-200 p-4">
            <h2 className="text-base font-semibold">
              {t("supportingPapers")} ({papers.rows.length})
            </h2>
            {papers.error ? (
              <p className="mt-1 text-xs text-amber-700">{papers.error}</p>
            ) : null}
          </div>
          <div className="divide-y divide-stone-100">
            {papers.rows.map((p) => (
              <article
                key={p.id}
                className="grid gap-2 p-4 md:grid-cols-[auto_1fr]"
              >
                <div className="font-mono text-sm text-cyan-700">
                  {p.relevance_score == null
                    ? tShared("na")
                    : p.relevance_score.toFixed(2)}
                </div>
                <div>
                  <h3 className="text-sm font-medium leading-6">
                    {p.title || "(untitled)"}
                  </h3>
                  <p className="mt-1 text-xs text-stone-500">
                    {p.pmid
                      ? `PMID ${p.pmid}`
                      : p.ct_id
                        ? `Trial ${p.ct_id}`
                        : p.doi
                          ? `DOI ${p.doi}`
                          : p.source || tPapers("sourcePending")}
                    {" · "}
                    {p.direct_relevance
                      ? tPapers("directHie")
                      : p.cross_disease_source || "cross-source"}
                  </p>
                </div>
              </article>
            ))}
            {papers.rows.length === 0 ? (
              <p className="p-4 text-sm text-stone-500">
                {t("emptySupportingPapers")}
              </p>
            ) : null}
          </div>
        </section>

        {therapies.rows.length > 0 ? (
          <section className="rounded-md border border-stone-200 bg-white">
            <div className="border-b border-stone-200 p-4">
              <h2 className="text-base font-semibold">
                {t("relatedTherapies")} ({therapies.rows.length})
              </h2>
            </div>
            <div className="divide-y divide-stone-100">
              {therapies.rows.map((th) => (
                <article key={th.id} className="grid gap-1 p-4">
                  <h3 className="text-sm font-medium leading-6">
                    {displayField(th.name, locale)}
                  </h3>
                  <p className="text-xs text-stone-500">
                    {th.therapy_type || tTherapies("typePending")} ·{" "}
                    {tTherapies("evidenceLabel")}{" "}
                    {th.evidence_in_hie || tTherapies("evidenceUnknown")} ·{" "}
                    {tTherapies("aleksandraFor")}:{" "}
                    {th.aleksandra_status || tTherapies("statusNotConsidered")}
                  </p>
                </article>
              ))}
            </div>
          </section>
        ) : null}

        {hypothesis.outcome ? (
          <section className="rounded-md border border-stone-200 bg-stone-100 p-4">
            <p className="font-mono text-xs uppercase text-stone-500">
              {t("currentOutcome")}
            </p>
            <p className="mt-2 text-sm leading-6 text-stone-700">
              {hypothesis.outcome}
            </p>
            {hypothesis.reviewed_at ? (
              <p className="mt-1 text-xs text-stone-500">
                {t("reviewedAt")}: {new Date(hypothesis.reviewed_at).toLocaleString()}
              </p>
            ) : null}
          </section>
        ) : null}

        <section
          className={`rounded-md border p-4 shadow-sm shadow-stone-200/40 ${tone(hypothesis.status)}`}
        >
          <p className="font-mono text-xs uppercase text-stone-500">
            {t("curatorAction")}
          </p>
          <p className="mt-2 text-xs leading-5 text-stone-600">
            {t("curatorActionBody")}
          </p>
          <form
            action={reviewHypothesis}
            className="mt-3 grid gap-3 lg:grid-cols-[1fr_auto]"
          >
            <input type="hidden" name="id" value={hypothesis.id} />
            <input
              type="hidden"
              name="title"
              value={displayField(hypothesis.title, "en")}
            />
            <textarea
              name="outcome"
              rows={3}
              placeholder={t("detailReasoningPlaceholder")}
              className="w-full rounded-md border border-stone-300 bg-white/90 px-3 py-2 text-sm leading-6 text-stone-800 placeholder:text-stone-400 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-300"
            />
            <div className="flex flex-col gap-2 lg:w-44">
              <button
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md bg-emerald-700 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-800"
                name="status"
                value="confirmed"
                type="submit"
              >
                <span aria-hidden="true">✓</span> {t("confirm")}
              </button>
              <button
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-medium text-stone-800 ring-1 ring-stone-300 hover:bg-stone-100"
                name="status"
                value="under_review"
                type="submit"
              >
                <span aria-hidden="true">?</span> {t("underReview")}
              </button>
              <button
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-medium text-rose-800 ring-1 ring-rose-300 hover:bg-rose-50"
                name="status"
                value="rejected"
                type="submit"
              >
                <span aria-hidden="true">×</span> {t("reject")}
              </button>
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}
