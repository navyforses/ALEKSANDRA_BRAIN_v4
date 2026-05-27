import { setRequestLocale, getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { reviewHypothesis } from "./actions";
import { getRows } from "@/lib/supabase";
import { displayField, type BilingualField } from "@/lib/i18n";
import {
  AssistantPanel,
  CommandCenterShell,
  CommandMetricCard,
  DarkGlassPanel,
  DemoDataNotice,
  EvidencePipeline,
  InsightCard,
  SectionHeader,
  StatusPill,
} from "@/components/prototype/PrototypeKit";

export const dynamic = "force-dynamic";

type Tone = "cyan" | "emerald" | "amber" | "rose" | "violet" | "slate" | "stone";

type Hypothesis = {
  id: string;
  title: BilingualField;
  description: BilingualField;
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

function tone(status: string | null): Tone {
  if (status === "confirmed") return "emerald";
  if (status === "promising" || status === "pursuing") return "cyan";
  if (status === "rejected") return "rose";
  if (status === "under_review") return "amber";
  return "stone";
}

export default async function HypothesesPage({ params }: { params: Promise<{ locale: "en" | "ka" }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Hypotheses");
  const tShared = await getTranslations("Shared");
  const tStatus = await getTranslations("HypothesisStatus");
  const tType = await getTranslations("HypothesisType");
  const tConf = await getTranslations("ConfidenceLevel");
  const isKa = locale === "ka";

  function score(value: number | null) {
    return value == null ? tShared("na") : value.toFixed(2);
  }

  const hypotheses = await getRows<Hypothesis>("hypotheses", {
    select: "id,title,description,hypothesis_type,confidence_level,novelty_score,feasibility_score,status,reviewed_at,outcome,recommended_action,supporting_papers",
    order: "created_at.asc",
    limit: 100,
  });

  const confirmed = hypotheses.rows.filter((h) => h.status === "confirmed").length;
  const hydrated = hypotheses.rows.filter((h) => (h.supporting_papers || []).length > 0).length;
  const reviewQueue = hypotheses.rows.filter((h) => h.status !== "confirmed" && h.status !== "rejected").length;

  return (
    <CommandCenterShell>
      <section className="grid gap-5 xl:grid-cols-[1.3fr_0.7fr]">
        <DarkGlassPanel className="p-6 sm:p-8">
          <StatusPill tone="violet" dark>{t("phaseLabel")}</StatusPill>
          <h1 className="mt-5 max-w-5xl text-4xl font-semibold tracking-[-0.055em] text-white sm:text-6xl">{t("title")}</h1>
          <p className="mt-5 max-w-4xl text-sm leading-7 text-slate-300">{t("subtitle")}</p>
        </DarkGlassPanel>
        <AssistantPanel
          title={isKa ? "Review queue inspector" : "Review queue inspector"}
          body={isKa ? "ეს გვერდიც გადმოტანილია mockup-ის command center ენაზე: hypothesis card, evidence chip, curator note და human decision gate." : "This page is also translated into the mockup command-center language: hypothesis card, evidence chip, curator note, and human decision gate."}
          items={isKa ? ["დადასტურება მხოლოდ review note-ით", "Rejected სტატუსი რჩება audit-ში", "Evidence count ჩანს card-ზე"] : ["Confirm only with review note", "Rejected status stays in audit", "Evidence count is visible on every card"]}
        />
      </section>

      {hypotheses.error ? <DemoDataNotice title={isKa ? "ჰიპოთეზების მონაცემთა არხი" : "Hypothesis data channel"} body={hypotheses.configured ? hypotheses.error : t("configWarning")} /> : null}

      <section className="grid gap-3 sm:grid-cols-3">
        <CommandMetricCard label={t("confirmedKpi")} value={confirmed} hint={isKa ? "კლინიკურად განხილული და დადასტურებული იდეები" : "Clinically reviewed and confirmed ideas"} tone="emerald" />
        <CommandMetricCard label={t("evidenceLinkedKpi")} value={`${hydrated}/${hypotheses.rows.length}`} hint={isKa ? "წყაროებთან დაკავშირებული hypotheses" : "Hypotheses connected to evidence"} tone="cyan" />
        <CommandMetricCard label={isKa ? "Review queue" : "Review queue"} value={reviewQueue} hint={isKa ? "საჭიროებს შემდგომ triage-ს" : "Needs further triage"} tone="amber" />
      </section>

      <DarkGlassPanel>
        <SectionHeader dark eyebrow={isKa ? "Hypothesis workflow" : "Hypothesis workflow"} title={isKa ? "იდეა გადადის evidence-linked decision object-ად." : "An idea becomes an evidence-linked decision object."} subtitle={isKa ? "Generated dashboard mockup-ის pipeline აქ გამოიყენება ჰიპოთეზების triage-ისთვის." : "The generated dashboard pipeline is used here for hypothesis triage."} />
        <div className="mt-6"><EvidencePipeline dark steps={[
          { label: "Draft", title: isKa ? "იდეა" : "Idea", body: isKa ? "ინიციირდება ოჯახის, კვლევის ან კლინიკური დაკვირვებიდან." : "Starts from family, research, or clinical observation.", tone: "slate" },
          { label: "Evidence", title: isKa ? "წყაროები" : "Sources", body: isKa ? "უკავშირდება papers/trials და იღებს confidence context-ს." : "Connects to papers/trials and receives confidence context.", tone: "cyan" },
          { label: "Review", title: isKa ? "Human gate" : "Human gate", body: isKa ? "curator note აფიქსირებს რატომ გადავიდა ან შეჩერდა." : "A curator note records why it moved forward or stopped.", tone: "amber" },
          { label: "Track", title: isKa ? "შემდეგი ნაბიჯი" : "Next step", body: isKa ? "recommended action გადადის team workflow-ში." : "The recommended action moves into the team workflow.", tone: "emerald" },
        ]} /></div>
      </DarkGlassPanel>

      <section className="grid gap-4 lg:grid-cols-3">
        <InsightCard dark label={isKa ? "Workflow" : "Workflow"} title={isKa ? "ჰიპოთეზა ხდება გადაწყვეტილების ობიექტი" : "A hypothesis becomes a decision object"} body={isKa ? "ყოველი იდეა იღებს status-ს, confidence-ს, novelty/feasibility ქულებს და მკაფიო რეკომენდებულ ნაბიჯს." : "Every idea receives a status, confidence, novelty/feasibility scores, and a clear recommended next step."} tone="violet" />
        <InsightCard dark label={isKa ? "Evidence" : "Evidence"} title={isKa ? "მტკიცებულება ჩანს იდეასთან ერთად" : "Evidence stays attached to the idea"} body={isKa ? "წყაროების რაოდენობა და განმარტებები ეხმარება გუნდს თავიდან აირიდოს გაუმყარებელი ინტერვენციები." : "Source counts and explanations help the team avoid unsupported interventions."} tone="cyan" />
        <InsightCard dark label={isKa ? "Boundary" : "Boundary"} title={isKa ? "Review არ ნიშნავს კლინიკურ დანიშნულებას" : "Review is not a clinical prescription"} body={isKa ? "ფორმა აფიქსირებს curator note-ს და audit trail-ს; მკურნალობის გადაწყვეტილება რჩება ექიმთან." : "The form captures curator notes and audit trail; treatment decisions remain with the clinician."} tone="amber" />
      </section>

      <DarkGlassPanel>
        <SectionHeader dark eyebrow={isKa ? "ჰიპოთეზების queue" : "Hypothesis queue"} title={isKa ? "პრიორიტეტები, evidence და review control ერთ ეკრანზე." : "Priorities, evidence, and review control on one screen."} subtitle={isKa ? "Clinical command center-ის პრინციპი: სწრაფად ჩანს რა არის ახალი, რა არის საკმარისად დასაბუთებული და სად არის სიფრთხილე საჭირო." : "The clinical command center principle: show what is new, what is sufficiently supported, and where caution is required."} />
        <div className="mt-6 grid gap-4">
          {hypotheses.rows.map((hypothesis) => (
            <article key={hypothesis.id} className="rounded-[1.75rem] border border-white/10 bg-white/[0.055] p-5 shadow-2xl shadow-slate-950/20 backdrop-blur-xl">
              <div className="grid gap-5 xl:grid-cols-[1fr_auto]">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusPill tone={tone(hypothesis.status)} compact dark>{hypothesis.status ? (tStatus.has(hypothesis.status) ? tStatus(hypothesis.status) : hypothesis.status) : t("statusNew")}</StatusPill>
                    <StatusPill tone="slate" compact dark>{hypothesis.hypothesis_type ? (tType.has(hypothesis.hypothesis_type) ? tType(hypothesis.hypothesis_type) : hypothesis.hypothesis_type) : t("typeOther")}</StatusPill>
                  </div>
                  <h2 className="mt-4 text-xl font-semibold leading-8 tracking-[-0.02em] text-white"><Link href={`/hypotheses/${hypothesis.id}`} className="hover:text-cyan-200 hover:underline focus:underline focus:outline-none">{displayField(hypothesis.title, locale)}</Link></h2>
                  <p className="mt-3 max-w-4xl text-sm leading-7 text-slate-300">{displayField(hypothesis.description, locale)}</p>
                </div>
                <dl className="grid grid-cols-3 gap-3 text-sm xl:w-96">
                  <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-3"><dt className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-slate-500">{t("confidence")}</dt><dd className="mt-2 font-semibold text-white">{hypothesis.confidence_level ? (tConf.has(hypothesis.confidence_level) ? tConf(hypothesis.confidence_level) : hypothesis.confidence_level) : tShared("na")}</dd></div>
                  <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-3"><dt className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-slate-500">{t("novelty")}</dt><dd className="mt-2 font-semibold text-white">{score(hypothesis.novelty_score)}</dd></div>
                  <div className="rounded-2xl border border-white/10 bg-slate-950/35 p-3"><dt className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-slate-500">{t("feasible")}</dt><dd className="mt-2 font-semibold text-white">{score(hypothesis.feasibility_score)}</dd></div>
                </dl>
              </div>
              <div className="mt-5 grid gap-4 border-t border-white/10 pt-5 xl:grid-cols-[1fr_auto]">
                <div><p className="font-mono text-[0.68rem] uppercase tracking-[0.16em] text-slate-500">{isKa ? "Recommended next action" : "Recommended next action"}</p><p className="mt-2 text-sm leading-7 text-slate-300">{hypothesis.recommended_action || t("noRecommendedAction")}</p>{hypothesis.outcome ? <p className="mt-3 rounded-2xl border border-white/10 bg-slate-950/35 p-3 text-xs leading-6 text-slate-400">{hypothesis.outcome}</p> : null}</div>
                <div className="flex flex-wrap items-start gap-3"><StatusPill tone="cyan" compact dark>{t("papersBadge")} {(hypothesis.supporting_papers || []).length}</StatusPill><form action={reviewHypothesis} className="flex w-full flex-col gap-2 xl:w-96"><input type="hidden" name="id" value={hypothesis.id} /><input type="hidden" name="title" value={displayField(hypothesis.title, "en")} /><textarea name="outcome" rows={2} placeholder={t("curatorNotePlaceholder")} className="w-full rounded-2xl border border-white/10 bg-slate-950/50 px-3 py-2 text-xs leading-5 text-slate-100 placeholder:text-slate-500 focus:border-cyan-300 focus:outline-none focus:ring-1 focus:ring-cyan-300" /><div className="flex flex-wrap gap-2"><button className="inline-flex min-h-10 items-center rounded-full bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-300" name="status" value="confirmed" type="submit">{t("confirm")}</button><button className="inline-flex min-h-10 items-center rounded-full bg-white/10 px-4 py-2 text-sm font-medium text-white ring-1 ring-white/15 hover:bg-white/15" name="status" value="under_review" type="submit">{t("review")}</button><button className="inline-flex min-h-10 items-center rounded-full bg-rose-300/10 px-4 py-2 text-sm font-medium text-rose-100 ring-1 ring-rose-300/30 hover:bg-rose-300/15" name="status" value="rejected" type="submit">{t("reject")}</button></div></form></div>
              </div>
            </article>
          ))}
          {hypotheses.rows.length === 0 ? <DemoDataNotice title={isKa ? "ჰიპოთეზები ჯერ არ ჩანს" : "No hypotheses yet"} body={t("emptyList")} /> : null}
        </div>
      </DarkGlassPanel>
    </CommandCenterShell>
  );
}
