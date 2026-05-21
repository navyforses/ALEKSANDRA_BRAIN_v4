import Link from "next/link";
import { getCount, getRows } from "@/lib/supabase";
import DashboardCharts from "@/components/DashboardCharts";

export const dynamic = "force-dynamic";

type RunRow = {
  kind: string;
  agent_id: string | null;
  start_time: string;
  exit_status: string;
  token_cost: string | number | null;
};

type PaperRow = {
  title: string;
  pmid: string | null;
  ct_id: string | null;
  relevance_score: number | null;
  direct_relevance: boolean | null;
  cross_disease_source: string | null;
  ingested_at?: string;
};

type HypothesisRow = {
  status: string | null;
};

const metricSpecs = [
  ["evidence_ledger", "Evidence ledger"],
  ["papers", "Papers"],
  ["paper_chunks", "Chunks"],
  ["hypotheses", "Hypotheses"],
] as const;

function statusTone(status: string | null) {
  if (status === "confirmed") return "bg-emerald-50 text-emerald-800 ring-emerald-200";
  if (status === "promising" || status === "pursuing") return "bg-cyan-50 text-cyan-800 ring-cyan-200";
  if (status === "rejected") return "bg-rose-50 text-rose-800 ring-rose-200";
  return "bg-stone-100 text-stone-700 ring-stone-200";
}

function formatMoney(value: string | number | null) {
  const n = Number(value ?? 0);
  return `$${n.toFixed(6)}`;
}

export default async function DashboardPage() {
  const [counts, runs, papers, hypotheses, runsForSpend, papersForIngestion] = await Promise.all([
    Promise.all(metricSpecs.map(([path]) => getCount(path))),
    getRows<RunRow>("runs", {
      select: "kind,agent_id,start_time,exit_status,token_cost",
      order: "start_time.desc",
      limit: 8,
    }),
    getRows<PaperRow>("papers", {
      select: "title,pmid,ct_id,relevance_score,direct_relevance,cross_disease_source",
      order: "relevance_score.desc.nullslast",
      limit: 6,
    }),
    getRows<HypothesisRow>("hypotheses", {
      select: "status",
      limit: 200,
    }),
    getRows<RunRow>("runs", {
      select: "start_time,token_cost",
      order: "start_time.desc",
      limit: 300,
    }),
    getRows<PaperRow & { ingested_at: string }>("papers", {
      select: "ingested_at,relevance_score",
      order: "ingested_at.desc",
      limit: 200,
    }),
  ]);

  const configured = counts.some((c) => c.configured) || runs.configured;
  const statusCounts = hypotheses.rows.reduce<Record<string, number>>((acc, row) => {
    const key = row.status || "unknown";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  // Group spends and ingestion over the last 30 days
  const dates = Array.from({ length: 30 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (29 - i));
    return d.toISOString().split("T")[0]; // YYYY-MM-DD
  });

  const dailySpends = dates.map((date) => {
    const dayRuns = (runsForSpend?.rows || []).filter((r) => r.start_time?.startsWith(date));
    const cost = dayRuns.reduce((sum, r) => sum + Number(r.token_cost ?? 0), 0);
    return { date, cost, tokens: 0 };
  });

  const dailyIngestion = dates.map((date) => {
    const dayPapers = (papersForIngestion?.rows || []).filter(
      (p) => p.ingested_at && p.ingested_at.startsWith(date)
    );
    const count = dayPapers.length;
    const avgRelevance =
      count > 0
        ? dayPapers.reduce((sum, p) => sum + (p.relevance_score ?? 0), 0) / count
        : 0;
    return { date, count, avgRelevance };
  });

  const hypothesisCounts = Object.entries(statusCounts).map(([status, count]) => ({
    status,
    count,
  }));

  return (
    <main className="min-h-screen bg-stone-50 text-stone-950">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-5 py-6 sm:px-8">
        <nav className="flex flex-wrap items-center justify-between gap-3 border-b border-stone-200 pb-4">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <Link href="/" className="font-mono text-sm font-semibold tracking-normal hover:text-stone-700 transition-colors">
              ALEKSANDRA_BRAIN
            </Link>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Link className="rounded-md bg-white px-3 py-2 text-stone-900 ring-1 ring-stone-200 shadow-sm transition-all" href="/dashboard">
              Dashboard
            </Link>
            <Link className="rounded-md px-3 py-2 text-stone-700 hover:bg-white transition-all" href="/hypotheses">
              Hypotheses
            </Link>
            <Link className="rounded-md px-3 py-2 text-stone-700 hover:bg-white transition-all" href="/papers">
              Papers
            </Link>
            <Link className="rounded-md px-3 py-2 text-stone-700 hover:bg-white transition-all" href="/therapies">
              Therapies
            </Link>
            <Link className="rounded-md px-3 py-2 text-stone-700 hover:bg-white transition-all" href="/timeline">
              Timeline
            </Link>
          </div>
        </nav>

        <header className="grid gap-4 lg:grid-cols-[1.3fr_0.7fr]">
          <div>
            <p className="font-mono text-xs uppercase text-cyan-700">Phase II.5C</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-normal sm:text-4xl">
              Family-visible operations dashboard
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-stone-600">
              A compact family view of ingestion, memory growth, alerts, and validation status.
              Clinical decisions stay with Aleksandra&apos;s doctors; this view tracks research workflow state.
            </p>
          </div>
          <div className="rounded-md border border-stone-200 bg-white p-4 shadow-sm transition-all hover:shadow-md duration-300">
            <p className="font-mono text-xs uppercase text-stone-500">Access posture</p>
            <p className="mt-2 text-sm leading-6 text-stone-700">
              Server-rendered data only. Service credentials remain on the server, and MRI data is never fetched here.
            </p>
            <p className="mt-3 text-sm font-medium text-emerald-700 flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              RLS smoke: covered by Phase 2.5 verifier C.2.
            </p>
          </div>
        </header>

        {!configured ? (
          <section className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
            Supabase environment is not configured for the viewer runtime. The page shell is ready; live counts
            appear after `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set on the server.
          </section>
        ) : null}

        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {metricSpecs.map(([, label], index) => (
            <div key={label} className="rounded-md border border-stone-200 bg-white p-4 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-md hover:border-stone-300">
              <p className="font-mono text-xs uppercase text-stone-500">{label}</p>
              <p className="mt-2 text-3xl font-semibold tracking-normal">
                {counts[index]?.count.toLocaleString() ?? 0}
              </p>
              <p className="mt-1 text-xs text-stone-500">{counts[index]?.error || "Live Supabase count"}</p>
            </div>
          ))}
        </section>

        {/* Dynamic Analytics Charts Component */}
        {configured && (
          <section className="rounded-md border border-stone-200 bg-stone-100/30 p-5">
            <DashboardCharts
              hypothesisCounts={hypothesisCounts}
              dailySpends={dailySpends}
              dailyIngestion={dailyIngestion}
              totalSpendLimitDaily={10.0}
              totalSpendLimitMonthly={60.0}
            />
          </section>
        )}

        <section className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-md border border-stone-200 bg-white">
            <div className="border-b border-stone-200 p-4">
              <h2 className="text-base font-semibold">Hypothesis status</h2>
            </div>
            <div className="flex flex-wrap gap-2 p-4">
              {Object.entries(statusCounts).length > 0 ? (
                Object.entries(statusCounts).map(([status, count]) => (
                  <span
                    key={status}
                    className={`rounded-md px-3 py-2 text-sm ring-1 ${statusTone(status)}`}
                  >
                    {status}: <span className="font-semibold">{count}</span>
                  </span>
                ))
              ) : (
                <p className="text-sm text-stone-500">No hypothesis rows returned.</p>
              )}
            </div>
          </div>

          <div className="rounded-md border border-stone-200 bg-white">
            <div className="border-b border-stone-200 p-4">
              <h2 className="text-base font-semibold">Latest workflow events</h2>
            </div>
            <div className="divide-y divide-stone-100">
              {runs.rows.map((run) => (
                <div key={`${run.kind}-${run.start_time}`} className="grid gap-2 p-4 sm:grid-cols-[1fr_auto]">
                  <div>
                    <p className="font-medium">{run.kind}</p>
                    <p className="text-xs text-stone-500">
                      {run.agent_id || "system"} · {new Date(run.start_time).toLocaleString()}
                    </p>
                  </div>
                  <div className="text-left sm:text-right">
                    <p className="text-sm">{run.exit_status}</p>
                    <p className="font-mono text-xs text-stone-500">{formatMoney(run.token_cost)}</p>
                  </div>
                </div>
              ))}
              {runs.rows.length === 0 ? <p className="p-4 text-sm text-stone-500">No recent runs.</p> : null}
            </div>
          </div>
        </section>

        <section className="rounded-md border border-stone-200 bg-white">
          <div className="border-b border-stone-200 p-4">
            <h2 className="text-base font-semibold">Top papers by relevance</h2>
          </div>
          <div className="divide-y divide-stone-100">
            {papers.rows.map((paper) => (
              <article key={`${paper.pmid || paper.ct_id || paper.title}`} className="grid gap-2 p-4 md:grid-cols-[auto_1fr]">
                <div className="font-mono text-sm text-cyan-700">
                  {paper.relevance_score == null ? "n/a" : paper.relevance_score.toFixed(2)}
                </div>
                <div>
                  <h3 className="text-sm font-medium leading-6">{paper.title}</h3>
                  <p className="mt-1 text-xs text-stone-500">
                    {paper.pmid ? `PMID ${paper.pmid}` : paper.ct_id || "source pending"} ·{" "}
                    {paper.direct_relevance ? "direct HIE" : paper.cross_disease_source || "cross-source"}
                  </p>
                </div>
              </article>
            ))}
            {papers.rows.length === 0 ? <p className="p-4 text-sm text-stone-500">No paper rows returned.</p> : null}
          </div>
        </section>
      </div>
    </main>
  );
}
