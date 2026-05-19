import { getRows } from "@/lib/supabase";

export const dynamic = "force-dynamic";

type Paper = {
  id: string;
  title: string;
  pmid: string | null;
  doi: string | null;
  ct_id: string | null;
  journal: string | null;
  publication_date: string | null;
  publication_year: number | null;
  paper_type: string | null;
  evidence_level: number | null;
  relevance_score: number | null;
  relevance_tags: string[] | null;
  direct_relevance: boolean | null;
  cross_disease_relevance: boolean | null;
  cross_disease_source: string | null;
  ai_summary: string | null;
  confidence_level: string | null;
  source: string | null;
  source_url: string | null;
  ingested_at: string | null;
};

function formatDate(value: string | null) {
  if (!value) return "date pending";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toISOString().slice(0, 10);
}

function formatScore(value: number | null) {
  return value == null ? "n/a" : value.toFixed(2);
}

function identifier(paper: Paper) {
  if (paper.pmid) return `PMID ${paper.pmid}`;
  if (paper.ct_id) return paper.ct_id;
  if (paper.doi) return `DOI ${paper.doi}`;
  return paper.source || "source pending";
}

function sourceLabel(paper: Paper) {
  const parts = [
    paper.journal,
    paper.publication_date
      ? formatDate(paper.publication_date)
      : paper.publication_year?.toString(),
    paper.paper_type,
  ].filter(Boolean);
  return parts.length > 0 ? parts.join(" | ") : "metadata pending";
}

function relevanceLabel(paper: Paper) {
  if (paper.direct_relevance) return "direct HIE";
  if (paper.cross_disease_relevance) {
    return paper.cross_disease_source || "cross-disease";
  }
  return paper.cross_disease_source || "unclassified";
}

export default async function PapersPage() {
  const papers = await getRows<Paper>("papers", {
    select:
      "id,title,pmid,doi,ct_id,journal,publication_date,publication_year,paper_type,evidence_level,relevance_score,relevance_tags,direct_relevance,cross_disease_relevance,cross_disease_source,ai_summary,confidence_level,source,source_url,ingested_at",
    order: "relevance_score.desc.nullslast,publication_date.desc.nullslast",
    limit: 100,
  });

  const highRelevance = papers.rows.filter((p) => (p.relevance_score ?? 0) >= 0.7).length;
  const direct = papers.rows.filter((p) => p.direct_relevance).length;
  const trials = papers.rows.filter((p) => p.ct_id || p.paper_type === "clinical_trial").length;

  return (
    <main className="min-h-screen bg-stone-50 text-stone-950">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-5 py-6 sm:px-8">
        <header className="grid gap-4 lg:grid-cols-[1fr_auto]">
          <div>
            <p className="font-mono text-xs uppercase text-cyan-700">Research corpus</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-normal sm:text-4xl">
              Papers
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-stone-600">
              Read-only view of ingested literature and trial records ranked by relevance to Aleksandra&apos;s research context.
            </p>
          </div>
          <div className="grid min-w-72 grid-cols-3 gap-3">
            <div className="rounded-md border border-stone-200 bg-white p-4">
              <p className="font-mono text-xs uppercase text-stone-500">Shown</p>
              <p className="mt-2 text-2xl font-semibold">{papers.rows.length}</p>
            </div>
            <div className="rounded-md border border-stone-200 bg-white p-4">
              <p className="font-mono text-xs uppercase text-stone-500">High</p>
              <p className="mt-2 text-2xl font-semibold">{highRelevance}</p>
            </div>
            <div className="rounded-md border border-stone-200 bg-white p-4">
              <p className="font-mono text-xs uppercase text-stone-500">Direct</p>
              <p className="mt-2 text-2xl font-semibold">{direct}</p>
            </div>
          </div>
        </header>

        {papers.error ? (
          <section className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
            {papers.error}
          </section>
        ) : null}

        <section className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-md border border-stone-200 bg-white p-4">
            <p className="font-mono text-xs uppercase text-stone-500">Clinical trials</p>
            <p className="mt-2 text-xl font-semibold">{trials}</p>
          </div>
          <div className="rounded-md border border-stone-200 bg-white p-4">
            <p className="font-mono text-xs uppercase text-stone-500">Top score</p>
            <p className="mt-2 text-xl font-semibold">{formatScore(papers.rows[0]?.relevance_score ?? null)}</p>
          </div>
          <div className="rounded-md border border-stone-200 bg-white p-4">
            <p className="font-mono text-xs uppercase text-stone-500">Latest ingest</p>
            <p className="mt-2 text-xl font-semibold">{formatDate(papers.rows[0]?.ingested_at ?? null)}</p>
          </div>
        </section>

        <section className="rounded-md border border-stone-200 bg-white">
          <div className="border-b border-stone-200 p-4">
            <h2 className="text-base font-semibold">Literature rows</h2>
          </div>
          <div className="divide-y divide-stone-100">
            {papers.rows.map((paper) => (
              <article key={paper.id} className="grid gap-4 p-4 lg:grid-cols-[7rem_1fr]">
                <div>
                  <p className="font-mono text-lg font-semibold text-cyan-700">
                    {formatScore(paper.relevance_score)}
                  </p>
                  <p className="mt-1 text-xs text-stone-500">
                    evidence {paper.evidence_level ?? "n/a"}
                  </p>
                </div>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-md bg-stone-100 px-2 py-1 font-mono text-xs text-stone-700">
                      {relevanceLabel(paper)}
                    </span>
                    {paper.confidence_level ? (
                      <span className="rounded-md bg-white px-2 py-1 font-mono text-xs text-stone-600 ring-1 ring-stone-200">
                        {paper.confidence_level}
                      </span>
                    ) : null}
                  </div>
                  <h3 className="mt-3 text-base font-semibold leading-7">{paper.title}</h3>
                  <p className="mt-1 text-xs text-stone-500">
                    {identifier(paper)} | {sourceLabel(paper)}
                  </p>
                  {paper.ai_summary ? (
                    <p className="mt-3 max-w-5xl text-sm leading-6 text-stone-700">
                      {paper.ai_summary}
                    </p>
                  ) : null}
                  {(paper.relevance_tags || []).length > 0 ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {(paper.relevance_tags || []).slice(0, 8).map((tag) => (
                        <span key={tag} className="rounded-md bg-stone-50 px-2 py-1 font-mono text-xs text-stone-600 ring-1 ring-stone-200">
                          {tag}
                        </span>
                      ))}
                    </div>
                  ) : null}
                  {paper.source_url ? (
                    <a
                      href={paper.source_url}
                      className="mt-3 inline-block text-sm font-medium text-cyan-700 hover:underline"
                      rel="noreferrer"
                      target="_blank"
                    >
                      Open source record
                    </a>
                  ) : null}
                </div>
              </article>
            ))}
            {papers.rows.length === 0 ? (
              <p className="p-4 text-sm text-stone-500">No paper rows returned.</p>
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}
