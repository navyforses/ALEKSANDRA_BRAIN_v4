import Link from "next/link";
import { reviewHypothesis } from "./actions";
import { getRows } from "@/lib/supabase";

export const dynamic = "force-dynamic";

type Hypothesis = {
  id: string;
  title: string;
  description: string;
  hypothesis_type: string | null;
  confidence_level: string | null;
  novelty_score: number | null;
  feasibility_score: number | null;
  status: string | null;
  reviewed_at: string | null;
  outcome: string | null;
  recommended_action: string | null;
  supporting_papers: string[] | null;
};

function tone(status: string | null) {
  if (status === "confirmed") return "border-emerald-300 bg-emerald-50 text-emerald-900";
  if (status === "promising" || status === "pursuing") return "border-cyan-300 bg-cyan-50 text-cyan-900";
  if (status === "rejected") return "border-rose-300 bg-rose-50 text-rose-900";
  return "border-stone-200 bg-white text-stone-900";
}

function score(value: number | null) {
  return value == null ? "n/a" : value.toFixed(2);
}

export default async function HypothesesPage() {
  const hypotheses = await getRows<Hypothesis>("hypotheses", {
    select:
      "id,title,description,hypothesis_type,confidence_level,novelty_score,feasibility_score,status,reviewed_at,outcome,recommended_action,supporting_papers",
    order: "created_at.asc",
    limit: 100,
  });

  const confirmed = hypotheses.rows.filter((h) => h.status === "confirmed").length;
  const hydrated = hypotheses.rows.filter((h) => (h.supporting_papers || []).length > 0).length;

  return (
    <main className="min-h-screen bg-stone-50 text-stone-950">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-5 py-6 sm:px-8">
        <nav className="flex flex-wrap items-center justify-between gap-3 border-b border-stone-200 pb-4">
          <Link href="/" className="font-mono text-sm font-semibold tracking-normal">
            ALEKSANDRA_BRAIN
          </Link>
          <div className="flex items-center gap-2 text-sm">
            <Link className="rounded-md px-3 py-2 text-stone-700 hover:bg-white" href="/dashboard">
              Dashboard
            </Link>
            <Link className="rounded-md px-3 py-2 text-stone-700 hover:bg-white" href="/hypotheses">
              Hypotheses
            </Link>
          </div>
        </nav>

        <header className="grid gap-4 lg:grid-cols-[1fr_auto]">
          <div>
            <p className="font-mono text-xs uppercase text-cyan-700">Phase II.5D</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-normal sm:text-4xl">
              Validation workflow
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-stone-600">
              Research hypotheses can be confirmed for follow-up, held under review, or rejected.
              Confirmation here means evidence links were curated; it does not mean treatment approval.
            </p>
          </div>
          <div className="grid min-w-64 grid-cols-2 gap-3">
            <div className="rounded-md border border-stone-200 bg-white p-4">
              <p className="font-mono text-xs uppercase text-stone-500">Confirmed</p>
              <p className="mt-2 text-3xl font-semibold">{confirmed}</p>
            </div>
            <div className="rounded-md border border-stone-200 bg-white p-4">
              <p className="font-mono text-xs uppercase text-stone-500">Evidence-linked</p>
              <p className="mt-2 text-3xl font-semibold">
                {hydrated}/{hypotheses.rows.length}
              </p>
            </div>
          </div>
        </header>

        {hypotheses.error ? (
          <section className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
            {hypotheses.error}
          </section>
        ) : null}

        <section className="grid gap-4">
          {hypotheses.rows.map((hypothesis) => (
            <article
              key={hypothesis.id}
              className={`rounded-md border p-4 shadow-sm shadow-stone-200/40 ${tone(hypothesis.status)}`}
            >
              <div className="grid gap-4 lg:grid-cols-[1fr_auto]">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-md border border-current/20 px-2 py-1 font-mono text-xs">
                      {hypothesis.status || "new"}
                    </span>
                    <span className="font-mono text-xs text-stone-500">
                      {hypothesis.hypothesis_type || "other"}
                    </span>
                  </div>
                  <h2 className="mt-3 text-lg font-semibold leading-7">{hypothesis.title}</h2>
                  <p className="mt-2 max-w-4xl text-sm leading-6 text-stone-700">
                    {hypothesis.description}
                  </p>
                </div>
                <dl className="grid grid-cols-3 gap-3 text-sm lg:w-80">
                  <div>
                    <dt className="font-mono text-xs uppercase text-stone-500">Confidence</dt>
                    <dd className="mt-1 font-semibold">{hypothesis.confidence_level || "n/a"}</dd>
                  </div>
                  <div>
                    <dt className="font-mono text-xs uppercase text-stone-500">Novelty</dt>
                    <dd className="mt-1 font-semibold">{score(hypothesis.novelty_score)}</dd>
                  </div>
                  <div>
                    <dt className="font-mono text-xs uppercase text-stone-500">Feasible</dt>
                    <dd className="mt-1 font-semibold">{score(hypothesis.feasibility_score)}</dd>
                  </div>
                </dl>
              </div>

              <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_auto]">
                <p className="text-sm leading-6 text-stone-700">
                  {hypothesis.recommended_action || "No recommended action captured."}
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-md bg-white/80 px-3 py-2 font-mono text-xs text-stone-700 ring-1 ring-stone-200">
                    papers {(hypothesis.supporting_papers || []).length}
                  </span>
                  <form action={reviewHypothesis} className="flex flex-wrap gap-2">
                    <input type="hidden" name="id" value={hypothesis.id} />
                    <input type="hidden" name="title" value={hypothesis.title} />
                    <button
                      className="inline-flex min-h-10 items-center gap-2 rounded-md bg-emerald-700 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-800"
                      name="status"
                      value="confirmed"
                      type="submit"
                    >
                      <span aria-hidden="true">✓</span>
                      Confirm
                    </button>
                    <button
                      className="inline-flex min-h-10 items-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-medium text-stone-800 ring-1 ring-stone-300 hover:bg-stone-100"
                      name="status"
                      value="under_review"
                      type="submit"
                    >
                      <span aria-hidden="true">?</span>
                      Review
                    </button>
                    <button
                      className="inline-flex min-h-10 items-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-medium text-rose-800 ring-1 ring-rose-300 hover:bg-rose-50"
                      name="status"
                      value="rejected"
                      type="submit"
                    >
                      <span aria-hidden="true">×</span>
                      Reject
                    </button>
                  </form>
                </div>
              </div>

              {hypothesis.outcome ? (
                <p className="mt-3 border-t border-current/10 pt-3 text-xs leading-5 text-stone-600">
                  {hypothesis.outcome}
                </p>
              ) : null}
            </article>
          ))}
          {hypotheses.rows.length === 0 ? (
            <div className="rounded-md border border-stone-200 bg-white p-6 text-sm text-stone-500">
              No hypotheses returned.
            </div>
          ) : null}
        </section>
      </div>
    </main>
  );
}
