import Link from "next/link";
import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import { reviewHypothesis } from "../actions";
import { getRows } from "@/lib/supabase";

export const dynamic = "force-dynamic";

type HypothesisDetail = {
  id: string;
  title: string;
  description: string;
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
  name: string;
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

function score(value: number | null) {
  return value == null ? "n/a" : value.toFixed(2);
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
              Dashboard
            </Link>
            <Link
              className="rounded-md px-3 py-2 text-stone-700 hover:bg-white"
              href="/hypotheses"
            >
              Hypotheses
            </Link>
          </div>
        </nav>

        <header className="grid gap-3">
          <Link
            href="/hypotheses"
            className="font-mono text-xs uppercase text-cyan-700 hover:underline"
          >
            ← Back to hypotheses
          </Link>
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-md border px-2 py-1 font-mono text-xs ${tone(hypothesis.status)}`}
            >
              {hypothesis.status || "new"}
            </span>
            <span className="font-mono text-xs text-stone-500">
              {hypothesis.hypothesis_type || "other"}
            </span>
            {hypothesis.urgency ? (
              <span className="font-mono text-xs text-stone-500">
                · urgency: {hypothesis.urgency}
              </span>
            ) : null}
            {hypothesis.generated_by ? (
              <span className="font-mono text-xs text-stone-500">
                · gen: {hypothesis.generated_by}
              </span>
            ) : null}
          </div>
          <h1 className="text-2xl font-semibold tracking-normal sm:text-3xl">
            {hypothesis.title}
          </h1>
          <p className="max-w-4xl text-sm leading-6 text-stone-700">
            {hypothesis.description}
          </p>
        </header>

        <section className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-md border border-stone-200 bg-white p-4">
            <p className="font-mono text-xs uppercase text-stone-500">
              Confidence
            </p>
            <p className="mt-2 text-xl font-semibold">
              {hypothesis.confidence_level || "n/a"}
            </p>
          </div>
          <div className="rounded-md border border-stone-200 bg-white p-4">
            <p className="font-mono text-xs uppercase text-stone-500">
              Novelty
            </p>
            <p className="mt-2 text-xl font-semibold">
              {score(hypothesis.novelty_score)}
            </p>
          </div>
          <div className="rounded-md border border-stone-200 bg-white p-4">
            <p className="font-mono text-xs uppercase text-stone-500">
              Feasibility
            </p>
            <p className="mt-2 text-xl font-semibold">
              {score(hypothesis.feasibility_score)}
            </p>
          </div>
        </section>

        {hypothesis.recommended_action ? (
          <section className="rounded-md border border-stone-200 bg-white p-4">
            <p className="font-mono text-xs uppercase text-stone-500">
              Recommended action
            </p>
            <p className="mt-2 text-sm leading-6 text-stone-800">
              {hypothesis.recommended_action}
            </p>
          </section>
        ) : null}

        {hypothesis.ai_reasoning ? (
          <section className="rounded-md border border-stone-200 bg-white p-4">
            <p className="font-mono text-xs uppercase text-stone-500">
              AI reasoning
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
              Supporting papers ({papers.rows.length})
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
                    ? "n/a"
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
                          : p.source || "source pending"}
                    {" · "}
                    {p.direct_relevance
                      ? "direct HIE"
                      : p.cross_disease_source || "cross-source"}
                  </p>
                </div>
              </article>
            ))}
            {papers.rows.length === 0 ? (
              <p className="p-4 text-sm text-stone-500">
                No supporting papers linked yet. The pipeline cites these in
                ai_reasoning; `backfill_supporting_papers.py` populates the
                UUID array.
              </p>
            ) : null}
          </div>
        </section>

        {therapies.rows.length > 0 ? (
          <section className="rounded-md border border-stone-200 bg-white">
            <div className="border-b border-stone-200 p-4">
              <h2 className="text-base font-semibold">
                Related therapies ({therapies.rows.length})
              </h2>
            </div>
            <div className="divide-y divide-stone-100">
              {therapies.rows.map((t) => (
                <article key={t.id} className="grid gap-1 p-4">
                  <h3 className="text-sm font-medium leading-6">{t.name}</h3>
                  <p className="text-xs text-stone-500">
                    {t.therapy_type || "type pending"} · evidence{" "}
                    {t.evidence_in_hie || "unknown"} · for Aleksandra:{" "}
                    {t.aleksandra_status || "not_considered"}
                  </p>
                </article>
              ))}
            </div>
          </section>
        ) : null}

        {hypothesis.outcome ? (
          <section className="rounded-md border border-stone-200 bg-stone-100 p-4">
            <p className="font-mono text-xs uppercase text-stone-500">
              Current outcome (last curator note)
            </p>
            <p className="mt-2 text-sm leading-6 text-stone-700">
              {hypothesis.outcome}
            </p>
            {hypothesis.reviewed_at ? (
              <p className="mt-1 text-xs text-stone-500">
                reviewed_at: {new Date(hypothesis.reviewed_at).toLocaleString()}
              </p>
            ) : null}
          </section>
        ) : null}

        <section
          className={`rounded-md border p-4 shadow-sm shadow-stone-200/40 ${tone(hypothesis.status)}`}
        >
          <p className="font-mono text-xs uppercase text-stone-500">
            Curator action
          </p>
          <p className="mt-2 text-xs leading-5 text-stone-600">
            Confirmation marks the evidence link curated for research
            follow-up. It is not a clinical treatment recommendation.
          </p>
          <form
            action={reviewHypothesis}
            className="mt-3 grid gap-3 lg:grid-cols-[1fr_auto]"
          >
            <input type="hidden" name="id" value={hypothesis.id} />
            <input type="hidden" name="title" value={hypothesis.title} />
            <textarea
              name="outcome"
              rows={3}
              placeholder="Why this verdict? Which paper carries the weight? What is the next step?"
              className="w-full rounded-md border border-stone-300 bg-white/90 px-3 py-2 text-sm leading-6 text-stone-800 placeholder:text-stone-400 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-300"
            />
            <div className="flex flex-col gap-2 lg:w-44">
              <button
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md bg-emerald-700 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-800"
                name="status"
                value="confirmed"
                type="submit"
              >
                <span aria-hidden="true">✓</span> Confirm
              </button>
              <button
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-medium text-stone-800 ring-1 ring-stone-300 hover:bg-stone-100"
                name="status"
                value="under_review"
                type="submit"
              >
                <span aria-hidden="true">?</span> Under review
              </button>
              <button
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-medium text-rose-800 ring-1 ring-rose-300 hover:bg-rose-50"
                name="status"
                value="rejected"
                type="submit"
              >
                <span aria-hidden="true">×</span> Reject
              </button>
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}
