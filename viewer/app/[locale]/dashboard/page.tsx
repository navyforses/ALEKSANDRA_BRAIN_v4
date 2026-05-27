import { setRequestLocale, getTranslations } from "next-intl/server";
import { getCount, getRows } from "@/lib/supabase";
import DashboardCharts from "@/components/DashboardCharts";
import {
  AssistantPanel,
  CommandCenterShell,
  CommandMetricCard,
  DarkGlassPanel,
  EvidencePipeline,
  InsightCard,
  NeuralHeroVisual,
  SectionHeader,
  StatusPill,
} from "@/components/prototype/PrototypeKit";

export const dynamic = "force-dynamic";

type Tone = "cyan" | "emerald" | "amber" | "rose" | "violet" | "slate" | "stone";

type RunRow = { kind: string; agent_id: string | null; start_time: string; exit_status: string; token_cost: string | number | null };
type PaperRow = { title: string; pmid: string | null; ct_id: string | null; relevance_score: number | null; direct_relevance: boolean | null; cross_disease_source: string | null; ingested_at?: string };
type HypothesisRow = { status: string | null };

const metricSpecs = [
  ["evidence_ledger", "metricEvidenceLedger", "cyan"],
  ["papers", "metricPapers", "violet"],
  ["paper_chunks", "metricChunks", "slate"],
  ["hypotheses", "metricHypotheses", "emerald"],
] as const;

function statusTone(status: string | null): Tone {
  if (status === "confirmed") return "emerald";
  if (status === "promising" || status === "pursuing") return "cyan";
  if (status === "rejected") return "rose";
  if (status === "under_review") return "amber";
  return "stone";
}

function formatMoney(value: string | number | null) {
  const n = Number(value ?? 0);
  return `$${n.toFixed(6)}`;
}

export default async function DashboardPage({ params }: { params: Promise<{ locale: "en" | "ka" }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Dashboard");
  const tShared = await getTranslations("Shared");
  const isKa = locale === "ka";

  const [counts, runs, papers, hypotheses, runsForSpend, papersForIngestion] = await Promise.all([
    Promise.all(metricSpecs.map(([path]) => getCount(path))),
    getRows<RunRow>("runs", { select: "kind,agent_id,start_time,exit_status,token_cost", order: "start_time.desc", limit: 8 }),
    getRows<PaperRow>("papers", { select: "title,pmid,ct_id,relevance_score,direct_relevance,cross_disease_source", order: "relevance_score.desc.nullslast", limit: 6 }),
    getRows<HypothesisRow>("hypotheses", { select: "status", limit: 200 }),
    getRows<RunRow>("runs", { select: "start_time,token_cost", order: "start_time.desc", limit: 300 }),
    getRows<PaperRow & { ingested_at: string }>("papers", { select: "ingested_at,relevance_score", order: "ingested_at.desc", limit: 200 }),
  ]);

  const configured = counts.some((c) => c.configured) || runs.configured;
  const statusCounts = hypotheses.rows.reduce<Record<string, number>>((acc, row) => {
    const key = row.status || "unknown";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const dates = Array.from({ length: 30 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (29 - i));
    return d.toISOString().split("T")[0];
  });
  const dailySpends = dates.map((date) => {
    const dayRuns = (runsForSpend?.rows || []).filter((r) => r.start_time?.startsWith(date));
    const cost = dayRuns.reduce((sum, r) => sum + Number(r.token_cost ?? 0), 0);
    return { date, cost, tokens: 0 };
  });
  const dailyIngestion = dates.map((date) => {
    const dayPapers = (papersForIngestion?.rows || []).filter((p) => p.ingested_at && p.ingested_at.startsWith(date));
    const count = dayPapers.length;
    const avgRelevance = count > 0 ? dayPapers.reduce((sum, p) => sum + (p.relevance_score ?? 0), 0) / count : 0;
    return { date, count, avgRelevance };
  });
  const hypothesisCounts = Object.entries(statusCounts).map(([status, count]) => ({ status, count }));

  return (
    <CommandCenterShell>
      <section className="grid gap-5 xl:grid-cols-[0.82fr_1.42fr_0.86fr]">
        <DarkGlassPanel className="self-start">
          <StatusPill tone="cyan" dark>{t("phaseLabel")}</StatusPill>
          <h1 className="mt-5 text-4xl font-semibold tracking-[-0.055em] text-white sm:text-5xl">{t("title")}</h1>
          <p className="mt-5 text-sm leading-7 text-slate-300">{t("subtitle")}</p>
          {!configured ? <div className="mt-5 rounded-2xl border border-amber-300/20 bg-amber-300/10 p-4 text-sm leading-6 text-amber-100">{t("configWarning")}</div> : null}
        </DarkGlassPanel>

        <NeuralHeroVisual
          title={isKa ? "Clinical command center" : "Clinical command center"}
          subtitle={isKa ? "გენერირებული Concept A mockup-ის ცენტრალური brain/network ვიზუალი ახლა რეალურ frontend-შია." : "The generated Concept A brain/network visual is now implemented as a real frontend surface."}
        />

        <AssistantPanel
          title={isKa ? "ოპერაციული შეჯამება" : "Operational brief"}
          body={isKa ? "მარჯვენა პანელი იმეორებს mockup-ის assistant card-ს: რას უნდა შეხედოს გუნდმა ახლა." : "The right panel mirrors the mockup assistant card: what the team should inspect now."}
          items={isKa ? ["Evidence ingestion ჯანმრთელია?", "რომელი ჰიპოთეზა ელოდება review-ს?", "ხარჯი კონტროლის ქვეშაა?", "რომელი წყაროა ყველაზე relevant?"] : ["Is evidence ingestion healthy?", "Which hypothesis awaits review?", "Is spend under control?", "Which source is most relevant?"]}
        />
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {metricSpecs.map(([, labelKey, tone], index) => (
          <CommandMetricCard
            key={labelKey}
            label={t(labelKey)}
            value={counts[index]?.count.toLocaleString() ?? "0"}
            hint={counts[index]?.configured ? t("liveSupabaseCount") : t("configurationPending")}
            tone={tone}
          />
        ))}
      </section>

      <DarkGlassPanel>
        <SectionHeader dark eyebrow={isKa ? "Research-to-care pipeline" : "Research-to-care pipeline"} title={isKa ? "Concept A pipeline: ingest → map → triage → track." : "Concept A pipeline: ingest → map → triage → track."} subtitle={isKa ? "Dashboard აღარ არის ცხრილების გროვა; იგი აჩვენებს workflow-ს, რომელიც clinical review-მდე მიდის." : "The dashboard is no longer a pile of tables; it shows a workflow that leads into clinical review."} />
        <div className="mt-6">
          <EvidencePipeline dark steps={[
            { label: "Ingest", title: isKa ? "წყაროების მიღება" : "Source intake", body: isKa ? "paper, trial და audit data შედის evidence queue-ში." : "Papers, trials, and audit data enter the evidence queue.", tone: "cyan" },
            { label: "Map", title: isKa ? "მექანიზმების რუკა" : "Mechanism map", body: isKa ? "სიგნალები უკავშირდება HIE recovery მექანიზმებს." : "Signals link to HIE recovery mechanisms.", tone: "violet" },
            { label: "Triage", title: isKa ? "კლინიკური triage" : "Clinical triage", body: isKa ? "ჰიპოთეზები იღებს priority და confidence სტატუსს." : "Hypotheses receive priority and confidence status.", tone: "amber" },
            { label: "Track", title: isKa ? "პროგრესის დროითი ხაზი" : "Progress timeline", body: isKa ? "შემდეგი review ინიშნება timeline-ში." : "Next review is scheduled into the timeline.", tone: "emerald" },
          ]} />
        </div>
      </DarkGlassPanel>

      {configured ? <DarkGlassPanel><DashboardCharts hypothesisCounts={hypothesisCounts} dailySpends={dailySpends} dailyIngestion={dailyIngestion} totalSpendLimitDaily={10.0} totalSpendLimitMonthly={60.0} /></DarkGlassPanel> : null}

      <section className="grid gap-4 xl:grid-cols-[0.82fr_1.18fr]">
        <DarkGlassPanel>
          <SectionHeader dark eyebrow={isKa ? "ჰიპოთეზების მდგომარეობა" : "Hypothesis state"} title={t("hypothesisStatus")} subtitle={isKa ? "Mockup-ის status chips აჩვენებს რომელ იდეას სჭირდება მოძრაობა." : "Mockup-style status chips show which ideas need movement."} />
          <div className="mt-5 flex flex-wrap gap-2">
            {Object.entries(statusCounts).length > 0 ? Object.entries(statusCounts).map(([status, count]) => <StatusPill key={status} tone={statusTone(status)} dark>{status}: {count}</StatusPill>) : <p className="text-sm leading-7 text-slate-400">{t("emptyHypotheses")}</p>}
          </div>
        </DarkGlassPanel>
        <DarkGlassPanel>
          <SectionHeader dark eyebrow={isKa ? "ბოლო აქტივობა" : "Latest activity"} title={t("latestEvents")} subtitle={isKa ? "კლინიკური command center-ის ქვედა activity rail." : "The lower activity rail of the clinical command center."} />
          <div className="mt-5 grid gap-3">
            {runs.rows.map((run) => (
              <div key={`${run.kind}-${run.start_time}`} className="grid gap-2 rounded-2xl border border-white/10 bg-white/[0.055] p-4 sm:grid-cols-[1fr_auto]">
                <div><p className="font-medium text-white">{run.kind}</p><p className="mt-1 text-xs text-slate-400">{run.agent_id || t("system")} · {new Date(run.start_time).toLocaleString()}</p></div>
                <div className="text-left sm:text-right"><p className="text-sm text-slate-200">{run.exit_status}</p><p className="font-mono text-xs text-slate-500">{formatMoney(run.token_cost)}</p></div>
              </div>
            ))}
            {runs.rows.length === 0 ? <p className="text-sm text-slate-400">{t("emptyRuns")}</p> : null}
          </div>
        </DarkGlassPanel>
      </section>

      <DarkGlassPanel>
        <SectionHeader dark eyebrow="Evidence intelligence" title={t("topPapers")} subtitle={isKa ? "Top relevance sources რჩება live data-ით, მაგრამ უკვე ჯდება command center-ის ვიზუალში." : "Top relevance sources remain live data, now inside the command-center visual system."} />
        <div className="mt-5 grid gap-3">
          {papers.rows.map((paper) => (
            <article key={`${paper.pmid || paper.ct_id || paper.title}`} className="grid gap-3 rounded-2xl border border-white/10 bg-white/[0.055] p-4 md:grid-cols-[5rem_1fr]">
              <div className="font-mono text-sm font-semibold text-cyan-200">{paper.relevance_score == null ? tShared("na") : paper.relevance_score.toFixed(2)}</div>
              <div><h3 className="text-sm font-medium leading-6 text-white">{paper.title}</h3><p className="mt-1 text-xs text-slate-400">{paper.pmid ? `PMID ${paper.pmid}` : paper.ct_id || tShared("sourcePending")} · {paper.direct_relevance ? "direct HIE" : paper.cross_disease_source || "cross-source"}</p></div>
            </article>
          ))}
          {papers.rows.length === 0 ? <p className="text-sm text-slate-400">{t("emptyPapers")}</p> : null}
        </div>
      </DarkGlassPanel>
    </CommandCenterShell>
  );
}
