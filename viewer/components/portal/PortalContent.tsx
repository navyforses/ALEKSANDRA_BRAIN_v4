"use client";

import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Brain,
  Database,
  FileText,
  FlaskConical,
  Layers3,
  Library,
  LifeBuoy,
  MessageSquareText,
  Network,
  Scale,
  Search,
  ShieldCheck,
  Stethoscope,
  UsersRound,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import type { Locale } from "@/lib/seo";

type PageKey =
  | "today"
  | "dashboard"
  | "brain"
  | "hypotheses"
  | "therapies"
  | "timeline"
  | "evidence-map"
  | "cohorts"
  | "data-integrations"
  | "papers"
  | "alerts"
  | "resources"
  | "how-it-works"
  | "support"
  | "settings"
  | "audit"
  | "knowledge";

type Tone = "sky" | "emerald" | "amber" | "violet" | "slate";
type DataCategory = "metrics" | "evidence" | "uncertainty" | "risks" | "doctorQuestions" | "briefItems";

type VerifiedItem = {
  text: string;
  sourceTitle: string;
  sourceUrl?: string;
  reviewedAt?: string;
};

type VerifiedMetric = {
  label: string;
  value: string;
  sourceTitle: string;
  sourceUrl?: string;
  reviewedAt?: string;
};

type VerifiedData = {
  metrics: VerifiedMetric[];
  evidence: VerifiedItem[];
  uncertainty: VerifiedItem[];
  risks: VerifiedItem[];
  doctorQuestions: VerifiedItem[];
  briefItems: VerifiedItem[];
};

type TopicModel = {
  eyebrow: string;
  title: string;
  purpose: string;
  icon: LucideIcon;
  data: VerifiedData;
};

const emptyVerifiedData = (): VerifiedData => ({
  metrics: [],
  evidence: [],
  uncertainty: [],
  risks: [],
  doctorQuestions: [],
  briefItems: [],
});

const toneStyles: Record<Tone, { border: string; bg: string; text: string; icon: string }> = {
  sky: { border: "border-sky-300/18", bg: "bg-sky-300/[0.055]", text: "text-sky-100", icon: "text-sky-200" },
  emerald: { border: "border-emerald-300/18", bg: "bg-emerald-300/[0.055]", text: "text-emerald-100", icon: "text-emerald-200" },
  amber: { border: "border-amber-200/18", bg: "bg-amber-200/[0.055]", text: "text-amber-100", icon: "text-amber-100" },
  violet: { border: "border-violet-300/18", bg: "bg-violet-300/[0.055]", text: "text-violet-100", icon: "text-violet-200" },
  slate: { border: "border-white/10", bg: "bg-white/[0.035]", text: "text-slate-200", icon: "text-slate-300" },
};

const dataCategories: Record<DataCategory, { icon: LucideIcon; tone: Tone }> = {
  metrics: { icon: Database, tone: "slate" },
  evidence: { icon: BookOpen, tone: "sky" },
  uncertainty: { icon: Search, tone: "amber" },
  risks: { icon: ShieldCheck, tone: "violet" },
  doctorQuestions: { icon: MessageSquareText, tone: "emerald" },
  briefItems: { icon: FileText, tone: "emerald" },
};

const kaCopy = {
  noData: "მონაცემი არ არის",
  noVerifiedData: "ამ სექციისთვის წყაროთი დადასტურებული რეალური მონაცემი ჯერ არ არის დამატებული.",
  policyLabel: "რეალური მონაცემის წესი",
  policyText: "საიტი აჩვენებს მხოლოდ იმ ინფორმაციას, რომელსაც აქვს რეალური წყარო ან დადასტურებული მონაცემთა ჩანაწერი. თუ მონაცემი არ არსებობს, ვაჩვენებთ ტექსტს: „მონაცემი არ არის“.",
  sourceLabel: "წყარო",
  notMedicalAdvice: "ეს პორტალი არ სვამს დიაგნოზს და არ იძლევა სამედიცინო რეკომენდაციას.",
  verifiedOnly: "მხოლოდ წყაროთი დადასტურებული მონაცემი",
  unavailable: "ჯერ ვერ გენერირდება, რადგან რეალური მონაცემი არ არის.",
  disabledAction: "ბრიფი მიუწვდომელია",
  briefTitle: "ექიმთან წასაღები ბრიფი",
  briefDescription: "ბრიფი შეიქმნება მხოლოდ მაშინ, როცა ამ გვერდზე იქნება წყაროთი დადასტურებული evidence, risk და doctor question მონაცემები.",
  metricLabels: ["წყარო", "მტკიცებულება", "რისკი", "ექიმთან კითხვა"],
  flow: {
    evidence: { label: "1. მტკიცებულება", title: "რა ვიცით" },
    risk: { label: "2. რისკი", title: "რა არის გაურკვეველი" },
    question: { label: "3. კითხვა", title: "რა ვკითხოთ ექიმს" },
  },
  sections: {
    evidence: "მტკიცებულების დეტალი",
    uncertainty: "გაურკვევლობა",
    risks: "საზღვარი და რისკი",
    doctorQuestions: "ექიმთან კითხვები",
  },
};

const enCopy = {
  noData: "No data available",
  noVerifiedData: "No source-backed real data has been added for this section yet.",
  policyLabel: "Real-data rule",
  policyText: "The site shows only information with a real source or verified data record. If data does not exist, the interface says: “No data available.”",
  sourceLabel: "Source",
  notMedicalAdvice: "This portal does not diagnose or provide medical advice.",
  verifiedOnly: "Only source-backed verified data",
  unavailable: "Not generated yet because no real data is available.",
  disabledAction: "Brief unavailable",
  briefTitle: "Doctor brief",
  briefDescription: "The brief will be generated only after source-backed evidence, risk, and doctor-question data exists for this page.",
  metricLabels: ["Sources", "Evidence", "Risks", "Doctor questions"],
  flow: {
    evidence: { label: "1. Evidence", title: "What we know" },
    risk: { label: "2. Risk", title: "What is uncertain" },
    question: { label: "3. Question", title: "What to ask" },
  },
  sections: {
    evidence: "Evidence detail",
    uncertainty: "Uncertainty",
    risks: "Boundary and risk",
    doctorQuestions: "Doctor questions",
  },
};

const pageShellKa: Record<PageKey, Omit<TopicModel, "data">> = {
  today: { eyebrow: "დღის მოკლე სურათი", title: "დღის ხედვა რეალური მონაცემებით", purpose: "აქ გამოჩნდება მხოლოდ დადასტურებული წყაროებიდან მიღებული დღიური შეჯამება.", icon: Layers3 },
  dashboard: { eyebrow: "კვლევის პანელი", title: "კვლევის პანელი რეალური მონაცემებით", purpose: "პანელი გამოიყენება წყაროების, რისკებისა და ექიმთან კითხვების საჩვენებლად მხოლოდ მაშინ, როცა მონაცემი არსებობს.", icon: Layers3 },
  brain: { eyebrow: "ტვინის რუკა", title: "ტვინის რუკა", purpose: "რუკა შეივსება მხოლოდ რეალური imaging, observation ან source-backed ჩანაწერებით.", icon: Brain },
  hypotheses: { eyebrow: "ჰიპოთეზები", title: "ჰიპოთეზები", purpose: "ჰიპოთეზა გამოჩნდება მხოლოდ მაშინ, როცა მას აქვს წყარო, საზღვარი და გადამოწმების სტატუსი.", icon: FlaskConical },
  therapies: { eyebrow: "თერაპიის კანდიდატები", title: "თერაპიის კანდიდატები", purpose: "თერაპიის შესახებ ჩანაწერი გამოჩნდება მხოლოდ წყაროთი დადასტურებული სტატუსით და უსაფრთხოების საზღვრით.", icon: Stethoscope },
  timeline: { eyebrow: "დროითი ხაზი", title: "დროითი ხაზი", purpose: "ქრონოლოგია შეივსება მხოლოდ რეალური თარიღებით, წყაროებით და review ჩანაწერებით.", icon: FileText },
  "evidence-map": { eyebrow: "მტკიცებულების რუკა", title: "მტკიცებულების რუკა", purpose: "წყარო, claim და შეზღუდვა გამოჩნდება მხოლოდ მაშინ, როცა მონაცემი რეალურად არსებობს.", icon: Network },
  cohorts: { eyebrow: "კოჰორტები", title: "კოჰორტები", purpose: "კოჰორტის მონაცემი გამოჩნდება მხოლოდ source-backed population metadata-ს არსებობისას.", icon: UsersRound },
  "data-integrations": { eyebrow: "მონაცემთა ინტეგრაციები", title: "მონაცემთა ინტეგრაციები", purpose: "ინტეგრაციის სტატუსი გამოჩნდება მხოლოდ რეალური connector ან ingestion ჩანაწერის არსებობისას.", icon: Database },
  papers: { eyebrow: "პუბლიკაციები", title: "პუბლიკაციები", purpose: "პუბლიკაცია გამოჩნდება მხოლოდ სრული citation, წყაროს ბმულის ან დადასტურებული ჩანაწერის არსებობისას.", icon: BookOpen },
  alerts: { eyebrow: "გაფრთხილებები", title: "გაფრთხილებები", purpose: "გაფრთხილება გამოჩნდება მხოლოდ რეალურ risk, safety ან review ჩანაწერზე დაყრდნობით.", icon: AlertTriangle },
  resources: { eyebrow: "რესურსები", title: "ექიმთან წასაღები რესურსები", purpose: "რესურსი და ბრიფი შეიქმნება მხოლოდ დადასტურებული evidence, risk და question მონაცემებიდან.", icon: FileText },
  "how-it-works": { eyebrow: "როგორ მუშაობს", title: "როგორ მუშაობს რეალური მონაცემის რეჟიმი", purpose: "ეს გვერდი ხსნის წესს: ფაქტი გამოჩნდება მხოლოდ წყაროთი; მონაცემის არქონისას ჩანს no-data მდგომარეობა.", icon: Scale },
  support: { eyebrow: "მხარდაჭერა", title: "მხარდაჭერა", purpose: "მხარდაჭერის მასალა გამოჩნდება მხოლოდ დადასტურებული help ან policy ჩანაწერებიდან.", icon: LifeBuoy },
  settings: { eyebrow: "პარამეტრები", title: "პარამეტრები", purpose: "პარამეტრები მართავს ჩვენების რეჟიმს, მაგრამ არ ქმნის სამედიცინო დასკვნას ან გამოგონილ მონაცემს.", icon: Scale },
  audit: { eyebrow: "აუდიტის კვალი", title: "აუდიტის კვალი", purpose: "აუდიტის ჩანაწერი გამოჩნდება მხოლოდ მაშინ, როცა არსებობს რეალური provenance ან review event.", icon: FileText },
  knowledge: { eyebrow: "ცოდნის ბაზა", title: "ცოდნის ბაზა", purpose: "ტერმინი და განმარტება გამოჩნდება მხოლოდ წყაროს ან curated ჩანაწერის არსებობისას.", icon: Library },
};

const pageShellEn: Record<PageKey, Omit<TopicModel, "data">> = {
  today: { eyebrow: "Today", title: "Today’s view with real data", purpose: "This page shows a daily summary only when verified source-backed data exists.", icon: Layers3 },
  dashboard: { eyebrow: "Research panel", title: "Research panel with real data", purpose: "The panel displays sources, risks, and clinician questions only when the underlying data exists.", icon: Layers3 },
  brain: { eyebrow: "Brain map", title: "Brain map", purpose: "The map is populated only from real imaging, observation, or source-backed records.", icon: Brain },
  hypotheses: { eyebrow: "Hypotheses", title: "Hypotheses", purpose: "A hypothesis appears only when it has a source, boundary, and verification status.", icon: FlaskConical },
  therapies: { eyebrow: "Therapy candidates", title: "Therapy candidates", purpose: "Therapy records appear only with source-backed status and safety boundaries.", icon: Stethoscope },
  timeline: { eyebrow: "Timeline", title: "Timeline", purpose: "The timeline is populated only with real dates, sources, and review records.", icon: FileText },
  "evidence-map": { eyebrow: "Evidence map", title: "Evidence map", purpose: "Sources, claims, and limitations appear only when the data actually exists.", icon: Network },
  cohorts: { eyebrow: "Cohorts", title: "Cohorts", purpose: "Cohort data appears only when source-backed population metadata exists.", icon: UsersRound },
  "data-integrations": { eyebrow: "Data integrations", title: "Data integrations", purpose: "Integration status appears only when a real connector or ingestion record exists.", icon: Database },
  papers: { eyebrow: "Papers", title: "Papers", purpose: "A paper appears only when a full citation, source link, or verified record exists.", icon: BookOpen },
  alerts: { eyebrow: "Alerts", title: "Alerts", purpose: "Alerts appear only from real risk, safety, or review records.", icon: AlertTriangle },
  resources: { eyebrow: "Resources", title: "Resources for the clinician visit", purpose: "Resources and briefs are generated only from verified evidence, risk, and question data.", icon: FileText },
  "how-it-works": { eyebrow: "How it works", title: "How the real-data mode works", purpose: "This page explains the rule: facts appear only with sources; missing data is shown as a no-data state.", icon: Scale },
  support: { eyebrow: "Support", title: "Support", purpose: "Support material appears only from verified help or policy records.", icon: LifeBuoy },
  settings: { eyebrow: "Settings", title: "Settings", purpose: "Settings control the display mode, but do not create medical conclusions or invented data.", icon: Scale },
  audit: { eyebrow: "Audit trail", title: "Audit trail", purpose: "Audit records appear only when real provenance or review events exist.", icon: FileText },
  knowledge: { eyebrow: "Knowledge base", title: "Knowledge base", purpose: "Terms and explanations appear only when a source or curated record exists.", icon: Library },
};

const buildTopics = (shell: Record<PageKey, Omit<TopicModel, "data">>): Record<PageKey, TopicModel> =>
  Object.fromEntries(Object.entries(shell).map(([key, value]) => [key, { ...value, data: emptyVerifiedData() }])) as Record<PageKey, TopicModel>;

const kaTopics = buildTopics(pageShellKa);
const enTopics = buildTopics(pageShellEn);

function copyFor(locale: Locale) {
  return locale === "ka" ? kaCopy : enCopy;
}

function contentFor(locale: Locale, pageKey: PageKey) {
  return locale === "ka" ? kaTopics[pageKey] : enTopics[pageKey];
}

function Surface({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-3xl border border-white/10 bg-white/[0.035] ${className}`}>{children}</section>;
}

function Pill({ children, tone = "slate" }: { children: ReactNode; tone?: Tone }) {
  const style = toneStyles[tone];
  return <span className={`inline-flex items-center rounded-full border px-3 py-1 text-[0.72rem] font-semibold ${style.border} ${style.bg} ${style.text}`}>{children}</span>;
}

function NoDataState({ locale, category = "evidence" }: { locale: Locale; category?: DataCategory }) {
  const copy = copyFor(locale);
  const { icon: Icon, tone } = dataCategories[category];
  const style = toneStyles[tone];

  return (
    <div className={`rounded-2xl border border-dashed px-4 py-4 ${style.border} ${style.bg}`}>
      <div className="flex items-start gap-3">
        <span className={`mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-white/10 bg-black/10 ${style.icon}`}>
          <Icon className="h-4 w-4" />
        </span>
        <div>
          <p className="text-sm font-semibold leading-6 text-white">{copy.noData}</p>
          <p className="mt-1 text-xs leading-6 text-slate-400">{copy.noVerifiedData}</p>
        </div>
      </div>
    </div>
  );
}

function DataPolicyCard({ locale }: { locale: Locale }) {
  const copy = copyFor(locale);

  return (
    <Surface className="border-emerald-300/15 bg-emerald-300/[0.045] p-4">
      <div className="flex items-start gap-3">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-emerald-300/20 bg-emerald-300/[0.07] text-emerald-100">
          <ShieldCheck className="h-4 w-4" />
        </span>
        <div>
          <p className="text-sm font-semibold text-emerald-50">{copy.policyLabel}</p>
          <p className="mt-2 text-xs leading-6 text-slate-300">{copy.policyText}</p>
        </div>
      </div>
    </Surface>
  );
}

function MetricGrid({ locale, metrics }: { locale: Locale; metrics: VerifiedMetric[] }) {
  const copy = copyFor(locale);

  if (metrics.length === 0) {
    return (
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {copy.metricLabels.map((label) => (
          <Surface key={label} className="p-4">
            <p className="text-[0.72rem] font-medium leading-5 text-slate-500">{label}</p>
            <p className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-white">{copy.noData}</p>
            <p className="mt-1 text-xs leading-5 text-slate-400">{copy.verifiedOnly}</p>
          </Surface>
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric) => (
        <Surface key={`${metric.label}-${metric.sourceTitle}`} className="p-4">
          <p className="text-[0.72rem] font-medium leading-5 text-slate-500">{metric.label}</p>
          <p className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-white">{metric.value}</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">{metric.sourceTitle}</p>
        </Surface>
      ))}
    </div>
  );
}

function FlowCard({ icon: Icon, label, title, item, tone, locale, category }: { icon: LucideIcon; label: string; title: string; item?: VerifiedItem; tone: Tone; locale: Locale; category: DataCategory }) {
  const style = toneStyles[tone];
  const copy = copyFor(locale);

  return (
    <Surface className={`p-5 ${style.bg} ${style.border}`}>
      <div className="flex items-center justify-between gap-3">
        <span className={`grid h-10 w-10 place-items-center rounded-xl border border-white/10 bg-black/10 ${style.icon}`}>
          <Icon className="h-5 w-5" />
        </span>
        <Pill tone={tone}>{label}</Pill>
      </div>
      <h2 className="mt-5 text-lg font-semibold leading-7 text-white">{title}</h2>
      {item ? (
        <div className="mt-3 text-sm leading-7 text-slate-300">
          <p>{item.text}</p>
          <p className="mt-2 text-xs leading-5 text-slate-500">{copy.sourceLabel}: {item.sourceTitle}</p>
        </div>
      ) : (
        <div className="mt-4">
          <NoDataState locale={locale} category={category} />
        </div>
      )}
    </Surface>
  );
}

function ListBlock({ icon: Icon, title, items, tone = "slate", locale, category }: { icon: LucideIcon; title: string; items: VerifiedItem[]; tone?: Tone; locale: Locale; category: DataCategory }) {
  const style = toneStyles[tone];
  const copy = copyFor(locale);

  return (
    <Surface className="p-5">
      <div className="flex items-center gap-3">
        <span className={`grid h-9 w-9 place-items-center rounded-xl border ${style.border} ${style.bg} ${style.icon}`}>
          <Icon className="h-4 w-4" />
        </span>
        <h2 className="text-base font-semibold text-white">{title}</h2>
      </div>
      <div className="mt-4 space-y-3">
        {items.length > 0 ? (
          items.map((item) => (
            <div key={`${item.text}-${item.sourceTitle}`} className="rounded-2xl border border-white/8 bg-[#0b1424]/70 px-3 py-3 text-sm leading-6 text-slate-300">
              <p>{item.text}</p>
              <p className="mt-2 text-xs leading-5 text-slate-500">{copy.sourceLabel}: {item.sourceTitle}</p>
            </div>
          ))
        ) : (
          <NoDataState locale={locale} category={category} />
        )}
      </div>
    </Surface>
  );
}

function BriefBuilder({ topic, locale }: { topic: TopicModel; locale: Locale }) {
  const copy = copyFor(locale);
  const canBuild = topic.data.briefItems.length > 0;

  return (
    <Surface className="p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Pill tone="emerald">{copy.briefTitle}</Pill>
          <h2 className="mt-4 text-xl font-semibold leading-7 text-white">{canBuild ? copy.briefTitle : copy.unavailable}</h2>
          <p className="mt-2 text-sm leading-7 text-slate-400">{copy.briefDescription}</p>
        </div>
        <button type="button" disabled={!canBuild} className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-300/20 bg-emerald-300/[0.07] px-4 py-2.5 text-sm font-semibold text-emerald-50 transition enabled:hover:bg-emerald-300/[0.11] disabled:cursor-not-allowed disabled:opacity-50">
          {canBuild ? copy.briefTitle : copy.disabledAction}
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-5">
        {canBuild ? (
          <div className="grid gap-3 md:grid-cols-3">
            {topic.data.briefItems.map((item, index) => (
              <div key={`${item.text}-${item.sourceTitle}`} className="rounded-2xl border border-white/10 bg-[#0b1424] p-4">
                <p className="text-[0.72rem] font-semibold text-slate-500">{index + 1}</p>
                <p className="mt-2 text-sm font-semibold leading-6 text-white">{item.text}</p>
                <p className="mt-2 text-xs leading-5 text-slate-500">{copy.sourceLabel}: {item.sourceTitle}</p>
              </div>
            ))}
          </div>
        ) : (
          <NoDataState locale={locale} category="briefItems" />
        )}
      </div>
    </Surface>
  );
}

function Hero({ topic, locale }: { topic: TopicModel; locale: Locale }) {
  const copy = copyFor(locale);
  const Icon = topic.icon;

  return (
    <Surface className="overflow-hidden p-5 sm:p-6">
      <div className="grid gap-6 lg:grid-cols-[1fr_18rem]">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Pill tone="sky">{topic.eyebrow}</Pill>
            <Pill tone="emerald">{copy.verifiedOnly}</Pill>
          </div>
          <h1 className="mt-5 max-w-5xl text-[clamp(1.6rem,3vw,3rem)] font-semibold leading-[1.14] tracking-[-0.025em] text-white">{topic.title}</h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-300 sm:text-base">{topic.purpose}</p>
          <div className="mt-5 rounded-2xl border border-white/10 bg-[#0b1424] p-4">
            <p className="text-[0.72rem] font-semibold text-slate-500">{copy.policyLabel}</p>
            <p className="mt-2 text-sm leading-7 text-slate-200">{copy.policyText}</p>
          </div>
        </div>
        <div className="rounded-3xl border border-white/10 bg-[#0b1424] p-5">
          <span className="grid h-12 w-12 place-items-center rounded-2xl border border-sky-300/20 bg-sky-300/[0.07] text-sky-100">
            <Icon className="h-6 w-6" />
          </span>
          <p className="mt-5 text-sm font-semibold text-white">{copy.noData}</p>
          <p className="mt-3 text-xs leading-6 text-slate-400">{copy.notMedicalAdvice}</p>
          <div className="mt-5">
            <NoDataState locale={locale} category="metrics" />
          </div>
        </div>
      </div>
    </Surface>
  );
}

export function PortalHomeDashboard({ locale }: { locale: Locale }) {
  const topic = contentFor(locale, "today");
  const copy = copyFor(locale);

  return (
    <div className="space-y-4">
      <Hero topic={topic} locale={locale} />
      <DataPolicyCard locale={locale} />

      <section className="grid gap-4 lg:grid-cols-3">
        <FlowCard icon={BookOpen} label={copy.flow.evidence.label} title={copy.flow.evidence.title} item={topic.data.evidence[0]} tone="sky" locale={locale} category="evidence" />
        <FlowCard icon={AlertTriangle} label={copy.flow.risk.label} title={copy.flow.risk.title} item={topic.data.uncertainty[0]} tone="amber" locale={locale} category="uncertainty" />
        <FlowCard icon={Stethoscope} label={copy.flow.question.label} title={copy.flow.question.title} item={topic.data.doctorQuestions[0]} tone="emerald" locale={locale} category="doctorQuestions" />
      </section>

      <MetricGrid locale={locale} metrics={topic.data.metrics} />

      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <ListBlock icon={BookOpen} title={copy.sections.evidence} items={topic.data.evidence} tone="sky" locale={locale} category="evidence" />
        <ListBlock icon={AlertTriangle} title={copy.sections.uncertainty} items={topic.data.uncertainty} tone="amber" locale={locale} category="uncertainty" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <ListBlock icon={Scale} title={copy.sections.risks} items={topic.data.risks} tone="violet" locale={locale} category="risks" />
        <ListBlock icon={MessageSquareText} title={copy.sections.doctorQuestions} items={topic.data.doctorQuestions} tone="emerald" locale={locale} category="doctorQuestions" />
      </div>

      <BriefBuilder topic={topic} locale={locale} />
    </div>
  );
}

export function PortalTopicPage({ locale, pageKey }: { locale: Locale; pageKey: PageKey }) {
  const topic = contentFor(locale, pageKey);
  const copy = copyFor(locale);

  return (
    <div className="space-y-4">
      <Hero topic={topic} locale={locale} />
      <DataPolicyCard locale={locale} />
      <MetricGrid locale={locale} metrics={topic.data.metrics} />

      <section className="grid gap-4 xl:grid-cols-3">
        <FlowCard icon={BookOpen} label={copy.flow.evidence.label} title={copy.flow.evidence.title} item={topic.data.evidence[0]} tone="sky" locale={locale} category="evidence" />
        <FlowCard icon={AlertTriangle} label={copy.flow.risk.label} title={copy.flow.risk.title} item={topic.data.uncertainty[0]} tone="amber" locale={locale} category="uncertainty" />
        <FlowCard icon={Stethoscope} label={copy.flow.question.label} title={copy.flow.question.title} item={topic.data.doctorQuestions[0]} tone="emerald" locale={locale} category="doctorQuestions" />
      </section>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <ListBlock icon={BookOpen} title={copy.sections.evidence} items={topic.data.evidence} tone="sky" locale={locale} category="evidence" />
        <ListBlock icon={Search} title={copy.sections.uncertainty} items={topic.data.uncertainty} tone="amber" locale={locale} category="uncertainty" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <ListBlock icon={ShieldCheck} title={copy.sections.risks} items={topic.data.risks} tone="violet" locale={locale} category="risks" />
        <ListBlock icon={MessageSquareText} title={copy.sections.doctorQuestions} items={topic.data.doctorQuestions} tone="emerald" locale={locale} category="doctorQuestions" />
      </div>

      <BriefBuilder topic={topic} locale={locale} />
    </div>
  );
}
