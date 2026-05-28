import Link from "next/link";
import type { ReactNode } from "react";
import type { Locale } from "@/lib/seo";
import { getCount, getRows } from "@/lib/supabase";
import { PortalDocumentList } from "./PortalDocumentList";

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

type Item = {
  title: string;
  body?: string;
  meta?: string;
  source: string;
  url?: string;
};

type Metric = {
  label: string;
  value: string;
  source: string;
};

type TopicData = {
  metrics: Metric[];
  evidence: Item[];
  uncertainty: Item[];
  risks: Item[];
  questions: Item[];
  briefItems: Item[];
  updated?: string;
};

type Topic = {
  eyebrow: string;
  title: string;
  data: TopicData;
};

type Paper = {
  id?: string;
  title?: string;
  abstract?: string;
  journal?: string;
  publication_year?: number;
  paper_type?: string;
  evidence_level?: number;
  relevance_score?: number;
  relevance_tags?: string[];
  direct_relevance?: boolean;
  cross_disease_source?: string;
  ai_summary?: string;
  ai_key_findings?: string[];
  ai_limitations?: string[];
  ai_aleksandra_implications?: string;
  confidence_level?: string;
  source?: string;
  source_url?: string;
  pmid?: string;
  doi?: string;
  ingested_at?: string;
  updated_at?: string;
  created_at?: string;
};

type Therapy = {
  id?: string;
  name?: string;
  therapy_type?: string;
  mechanism_of_action?: string;
  evidence_in_hie?: string;
  evidence_summary?: string;
  clinical_status?: string;
  aleksandra_eligible?: boolean;
  aleksandra_status?: string;
  aleksandra_notes?: string;
  ai_assessment?: string;
  confidence_level?: string;
  updated_at?: string;
  created_at?: string;
};

type Hypothesis = {
  id?: string;
  title?: unknown;
  description?: unknown;
  hypothesis_type?: string;
  confidence_level?: string;
  novelty_score?: number;
  feasibility_score?: number;
  urgency?: string;
  ai_reasoning?: unknown;
  recommended_action?: unknown;
  status?: string;
  outcome?: unknown;
  reviewed_at?: string;
  updated_at?: string;
  created_at?: string;
};

type BrainRegion = {
  id?: string;
  name?: string;
  name_ka?: string;
  hemisphere?: string;
  region_type?: string;
  primary_functions?: string[];
  functional_networks?: string[];
  damage_status?: string;
  damage_description?: string;
  plasticity_potential?: string;
  plasticity_notes?: string;
  updated_at?: string;
  created_at?: string;
};

type Timeline = {
  id?: string;
  event_date?: string;
  event_type?: string;
  title?: string;
  title_ka?: string;
  description?: string;
  description_ka?: string;
  source?: string;
  source_url?: string;
  created_at?: string;
};

type Trial = {
  id?: string;
  nct_id?: string;
  title?: string;
  condition?: string;
  intervention?: string;
  phase?: string;
  status?: string;
  location?: string;
  eligibility_notes?: string;
  relevance_notes?: string;
  source_url?: string;
  updated_at?: string;
  created_at?: string;
};

type Ingestion = {
  id?: string;
  source?: string;
  query_used?: string;
  results_found?: number;
  new_papers_added?: number;
  hypotheses_generated?: number;
  high_relevance_count?: number;
  status?: string;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
};

type DiscoveryReport = {
  id?: string;
  report_date?: string;
  report_type?: string;
  title?: string;
  executive_summary?: string;
  papers_ingested?: number;
  papers_analyzed?: number;
  hypotheses_generated?: number;
  trials_updated?: number;
  created_at?: string;
};

type Alert = {
  id?: string;
  tier?: string;
  event_kind?: string;
  confidence?: number | string;
  payload?: Record<string, unknown>;
  delivered_at?: string;
  blocked_reason?: string;
  created_at?: string;
};

type Brief = {
  id?: string;
  brief_week?: string;
  pdf_r2_path?: string;
  sections?: Record<string, unknown>;
  generated_at?: string;
};

type Action = {
  id?: string;
  action_type?: string;
  target_table?: string;
  source_input?: string;
  approved_at?: string;
  reversed_at?: string;
  created_at?: string;
};

const emptyData: TopicData = {
  metrics: [],
  evidence: [],
  uncertainty: [],
  risks: [],
  questions: [],
  briefItems: [],
};

const order: PageKey[] = [
  "today",
  "dashboard",
  "brain",
  "hypotheses",
  "therapies",
  "timeline",
  "evidence-map",
  "cohorts",
  "data-integrations",
  "papers",
  "alerts",
  "resources",
  "knowledge",
  "audit",
  "how-it-works",
  "support",
  "settings",
];

const nav: Record<Locale, Record<PageKey, string>> = {
  ka: {
    today: "დღეს",
    dashboard: "დაფა",
    brain: "ტვინი",
    hypotheses: "ჰიპოთეზები",
    therapies: "თერაპიები",
    timeline: "Timeline",
    "evidence-map": "Evidence map",
    cohorts: "კოჰორტები",
    "data-integrations": "ინტეგრაციები",
    papers: "Papers",
    alerts: "Alerts",
    resources: "რესურსები",
    "how-it-works": "როგორ მუშაობს",
    support: "მხარდაჭერა",
    settings: "პარამეტრები",
    audit: "Audit",
    knowledge: "ცოდნა",
  },
  en: {
    today: "Today",
    dashboard: "Dashboard",
    brain: "Brain",
    hypotheses: "Hypotheses",
    therapies: "Therapies",
    timeline: "Timeline",
    "evidence-map": "Evidence map",
    cohorts: "Cohorts",
    "data-integrations": "Integrations",
    papers: "Papers",
    alerts: "Alerts",
    resources: "Resources",
    "how-it-works": "How it works",
    support: "Support",
    settings: "Settings",
    audit: "Audit",
    knowledge: "Knowledge",
  },
};

const shells: Record<Locale, Record<PageKey, Omit<Topic, "data">>> = {
  ka: {
    today: { eyebrow: "aleksandra_timeline + briefs", title: "დღის რეალური ხედი" },
    dashboard: { eyebrow: "Supabase overview", title: "რეალური მონაცემების დაფა" },
    brain: { eyebrow: "brain_regions", title: "ტვინის რუკა" },
    hypotheses: { eyebrow: "hypotheses", title: "ჰიპოთეზები" },
    therapies: { eyebrow: "therapies", title: "თერაპიები" },
    timeline: { eyebrow: "aleksandra_timeline", title: "Timeline" },
    "evidence-map": { eyebrow: "papers", title: "Evidence map" },
    cohorts: { eyebrow: "clinical_trials", title: "კოჰორტები და trials" },
    "data-integrations": { eyebrow: "ingestion_log", title: "მონაცემთა ინტეგრაციები" },
    papers: { eyebrow: "papers", title: "პუბლიკაციები" },
    alerts: { eyebrow: "alerts_log", title: "Alerts" },
    resources: { eyebrow: "briefs.sections", title: "ექიმთან წასაღები რესურსები" },
    "how-it-works": { eyebrow: "discovery_reports + ingestion_log", title: "როგორ მუშაობს" },
    support: { eyebrow: "manager_actions", title: "მხარდაჭერა" },
    settings: { eyebrow: "manager_actions", title: "პარამეტრები" },
    audit: { eyebrow: "manager_actions", title: "Audit" },
    knowledge: { eyebrow: "papers + discovery_reports", title: "ცოდნის ბაზა" },
  },
  en: {
    today: { eyebrow: "aleksandra_timeline + briefs", title: "Today with real data" },
    dashboard: { eyebrow: "Supabase overview", title: "Real-data dashboard" },
    brain: { eyebrow: "brain_regions", title: "Brain map" },
    hypotheses: { eyebrow: "hypotheses", title: "Hypotheses" },
    therapies: { eyebrow: "therapies", title: "Therapies" },
    timeline: { eyebrow: "aleksandra_timeline", title: "Timeline" },
    "evidence-map": { eyebrow: "papers", title: "Evidence map" },
    cohorts: { eyebrow: "clinical_trials", title: "Cohorts and trials" },
    "data-integrations": { eyebrow: "ingestion_log", title: "Data integrations" },
    papers: { eyebrow: "papers", title: "Papers" },
    alerts: { eyebrow: "alerts_log", title: "Alerts" },
    resources: { eyebrow: "briefs.sections", title: "Resources for the clinician visit" },
    "how-it-works": { eyebrow: "discovery_reports + ingestion_log", title: "How it works" },
    support: { eyebrow: "manager_actions", title: "Support" },
    settings: { eyebrow: "manager_actions", title: "Settings" },
    audit: { eyebrow: "manager_actions", title: "Audit" },
    knowledge: { eyebrow: "papers + discovery_reports", title: "Knowledge" },
  },
};

function text(value: unknown, locale: Locale = "ka"): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") {
    const trimmed = value.trim();
    if ((trimmed.startsWith("{") && trimmed.endsWith("}")) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
      try {
        const parsed = JSON.parse(trimmed) as unknown;
        const rendered = text(parsed, locale);
        if (rendered) return rendered;
      } catch {
        // Keep the original text when a stored value only looks like JSON.
      }
    }
    return trimmed;
  }
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map((entry) => text(entry, locale)).filter(Boolean).join("; ");
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const direct = text(obj[locale] ?? obj[locale === "ka" ? "en" : "ka"], locale);
    if (direct) return direct;

    const preferredKeys = [
      "reasoning",
      "summary",
      "answer",
      "recommendation",
      "recommended_action",
      "action",
      "assessment",
      "analysis",
      "dossier",
      "narrative",
      "explanation",
      "conclusion",
      "description",
      "content",
      "text",
      "title",
      "name",
      "value",
    ];
    const preferred = preferredKeys.map((key) => text(obj[key], locale)).find(Boolean);
    if (preferred) return preferred;

    // Arbitrary backend metadata objects often contain UUIDs, timestamps, and
    // audit fields. Do not dump those key-value pairs into the public reader;
    // if there is no human-facing field above, treat the object as no display data.
    return "";
  }
  return "";
}

function join(parts: Array<unknown>, sep = " · ", locale: Locale = "ka") {
  return parts.map((p) => text(p, locale)).filter(Boolean).join(sep);
}

function date(value?: string, locale: Locale = "ka") {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat(locale === "ka" ? "ka-GE" : "en-US", { year: "numeric", month: "short", day: "2-digit" }).format(parsed);
}

function percent(value?: number | string) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  return `${Math.round(n * 100)}%`;
}

function rowSource(table: string, id?: string) {
  return id ? `Supabase:${table}:${id.slice(0, 8)}` : `Supabase:${table}`;
}

function item(title?: unknown, body?: unknown, source = "Supabase", meta?: unknown, url?: string, locale: Locale = "ka"): Item | null {
  const renderedTitle = text(title, locale);
  const renderedBody = text(body, locale);
  if (!renderedTitle && !renderedBody) return null;
  return { title: renderedTitle || source, body: renderedBody || undefined, source, meta: text(meta, locale) || undefined, url };
}

function latest(locale: Locale, values: Array<string | undefined>) {
  const picked = values.filter(Boolean).map((v) => new Date(String(v))).filter((d) => !Number.isNaN(d.getTime())).sort((a, b) => b.getTime() - a.getTime())[0];
  return picked ? date(picked.toISOString(), locale) : undefined;
}

function paperItem(row: Paper): Item | null {
  return item(
    row.title,
    join([row.ai_summary, text(row.ai_key_findings), row.ai_aleksandra_implications], " — "),
    join([row.source, row.pmid ? `PMID ${row.pmid}` : undefined, row.doi ? `DOI ${row.doi}` : undefined, rowSource("papers", row.id)]),
    join([row.journal, row.publication_year, row.relevance_score !== undefined ? `relevance ${percent(row.relevance_score)}` : undefined, row.confidence_level]),
    row.source_url,
  );
}

function therapyItem(row: Therapy): Item | null {
  return item(
    row.name,
    join([row.mechanism_of_action, row.evidence_summary, row.ai_assessment], " — "),
    rowSource("therapies", row.id),
    join([row.therapy_type, row.evidence_in_hie, row.clinical_status, row.aleksandra_status, row.confidence_level]),
  );
}

function hypothesisItem(row: Hypothesis, locale: Locale): Item | null {
  return item(
    row.title,
    join([row.description, row.ai_reasoning], " — ", locale),
    rowSource("hypotheses", row.id),
    join([row.hypothesis_type, row.status, row.confidence_level, row.urgency], " · ", locale),
    undefined,
    locale,
  );
}

function brainItem(row: BrainRegion, locale: Locale): Item | null {
  return item(
    locale === "ka" ? row.name_ka || row.name : row.name || row.name_ka,
    join([text(row.primary_functions), text(row.functional_networks), row.damage_description, row.plasticity_notes], " — "),
    rowSource("brain_regions", row.id),
    join([row.hemisphere, row.region_type, row.damage_status, row.plasticity_potential]),
  );
}

function timelineItem(row: Timeline, locale: Locale): Item | null {
  return item(
    locale === "ka" ? row.title_ka || row.title : row.title || row.title_ka,
    locale === "ka" ? row.description_ka || row.description : row.description || row.description_ka,
    join([row.source, rowSource("aleksandra_timeline", row.id)]),
    join([date(row.event_date, locale), row.event_type]),
    row.source_url,
  );
}

function trialItem(row: Trial): Item | null {
  return item(
    row.title,
    join([row.condition, row.intervention, row.eligibility_notes, row.relevance_notes], " — "),
    row.nct_id ? `ClinicalTrials.gov:${row.nct_id}` : rowSource("clinical_trials", row.id),
    join([row.phase, row.status, row.location]),
    row.source_url || (row.nct_id ? `https://clinicaltrials.gov/study/${row.nct_id}` : undefined),
  );
}

function ingestionItem(row: Ingestion, locale: Locale): Item | null {
  return item(
    join([row.source, row.query_used], " / "),
    join([row.results_found !== undefined ? `results ${row.results_found}` : undefined, row.new_papers_added !== undefined ? `new papers ${row.new_papers_added}` : undefined, row.hypotheses_generated !== undefined ? `hypotheses ${row.hypotheses_generated}` : undefined, row.error_message], " — "),
    rowSource("ingestion_log", row.id),
    join([row.status, date(row.completed_at || row.started_at, locale)]),
  );
}

function reportItem(row: DiscoveryReport, locale: Locale): Item | null {
  return item(
    row.title,
    row.executive_summary,
    rowSource("discovery_reports", row.id),
    join([row.report_type, date(row.report_date || row.created_at, locale), row.papers_ingested !== undefined ? `papers ${row.papers_ingested}` : undefined, row.hypotheses_generated !== undefined ? `hypotheses ${row.hypotheses_generated}` : undefined]),
  );
}

function alertItem(row: Alert, locale: Locale): Item | null {
  return item(
    join([row.tier, row.event_kind], " / "),
    join([text(row.payload), row.blocked_reason], " — "),
    rowSource("alerts_log", row.id),
    join([row.confidence !== undefined ? `confidence ${percent(row.confidence)}` : undefined, date(row.delivered_at || row.created_at, locale)]),
  );
}

function actionItem(row: Action, locale: Locale): Item | null {
  return item(
    join([row.action_type, row.target_table], " → "),
    join([row.source_input ? `source ${row.source_input}` : undefined, row.approved_at ? `approved ${date(row.approved_at, locale)}` : undefined, row.reversed_at ? `reversed ${date(row.reversed_at, locale)}` : undefined], " — "),
    rowSource("manager_actions", row.id),
    date(row.created_at, locale),
  );
}

function briefItems(row: Brief | undefined, locale: Locale): Item[] {
  if (!row?.sections) return [];
  const out: Item[] = [];
  const add = (title: string, body: unknown, source: string) => {
    const next = item(title, text(body), source, date(row.generated_at || row.brief_week, locale));
    if (next) out.push(next);
  };
  for (const [key, value] of Object.entries(row.sections)) {
    if (Array.isArray(value)) value.slice(0, 8).forEach((entry, index) => add(`${key} ${index + 1}`, entry, rowSource(`briefs.sections.${key}`, row.id)));
    else add(key, value, rowSource(`briefs.sections.${key}`, row.id));
  }
  return out;
}

async function metric(table: string, label: string): Promise<Metric | null> {
  const result = await getCount(table);
  if (!result.configured || result.error) return null;
  return { label, value: String(result.count), source: `Supabase:${table}` };
}

async function overview(locale: Locale): Promise<TopicData> {
  const [papers, hypotheses, therapies, timeline, briefs, metrics] = await Promise.all([
    getRows<Paper>("papers", { select: "id,title,abstract,journal,publication_year,relevance_score,ai_summary,ai_key_findings,ai_aleksandra_implications,confidence_level,source,source_url,pmid,doi,ingested_at,updated_at,created_at", order: "ingested_at.desc", limit: 5 }),
    getRows<Hypothesis>("hypotheses", { select: "id,title,description,hypothesis_type,confidence_level,urgency,ai_reasoning,recommended_action,status,outcome,reviewed_at,updated_at,created_at", order: "created_at.desc", limit: 5 }),
    getRows<Therapy>("therapies", { select: "id,name,therapy_type,mechanism_of_action,evidence_in_hie,evidence_summary,clinical_status,aleksandra_status,ai_assessment,confidence_level,updated_at,created_at", order: "updated_at.desc", limit: 5 }),
    getRows<Timeline>("aleksandra_timeline", { select: "id,event_date,event_type,title,title_ka,description,description_ka,source,source_url,created_at", order: "event_date.desc", limit: 5 }),
    getRows<Brief>("briefs", { select: "id,brief_week,pdf_r2_path,sections,generated_at", order: "generated_at.desc", limit: 1 }),
    Promise.all([metric("papers", "Papers"), metric("hypotheses", locale === "ka" ? "ჰიპოთეზები" : "Hypotheses"), metric("therapies", locale === "ka" ? "თერაპიები" : "Therapies"), metric("aleksandra_timeline", "Timeline")]),
  ]);
  const b = briefItems(briefs.rows[0], locale);
  return {
    metrics: metrics.filter(Boolean) as Metric[],
    evidence: [...timeline.rows.map((r) => timelineItem(r, locale)), ...papers.rows.map(paperItem)].filter(Boolean) as Item[],
    uncertainty: hypotheses.rows.map((r) => hypothesisItem(r, locale)).filter(Boolean) as Item[],
    risks: therapies.rows.map(therapyItem).filter(Boolean) as Item[],
    questions: [...hypotheses.rows.map((r) => item(r.title, r.recommended_action, rowSource("hypotheses", r.id), r.status, undefined, locale)), ...therapies.rows.map((r) => item(r.name, r.aleksandra_notes || r.ai_assessment, rowSource("therapies", r.id), r.aleksandra_status))].filter(Boolean) as Item[],
    briefItems: b,
    updated: latest(locale, [...papers.rows.map((r) => r.updated_at || r.ingested_at || r.created_at), ...hypotheses.rows.map((r) => r.updated_at || r.created_at), ...therapies.rows.map((r) => r.updated_at || r.created_at), ...timeline.rows.map((r) => r.event_date || r.created_at), ...briefs.rows.map((r) => r.generated_at)]),
  };
}

async function load(pageKey: PageKey, locale: Locale): Promise<TopicData> {
  if (pageKey === "today" || pageKey === "dashboard") return overview(locale);
  if (pageKey === "papers" || pageKey === "evidence-map") {
    const rows = await getRows<Paper>("papers", { select: "id,title,abstract,journal,publication_year,paper_type,evidence_level,relevance_score,relevance_tags,direct_relevance,cross_disease_source,ai_summary,ai_key_findings,ai_limitations,ai_aleksandra_implications,confidence_level,source,source_url,pmid,doi,ingested_at,updated_at,created_at", order: "ingested_at.desc", limit: 12 });
    return { ...emptyData, evidence: rows.rows.map(paperItem).filter(Boolean) as Item[], risks: rows.rows.map((r) => item(r.title, text(r.ai_limitations), rowSource("papers", r.id), r.confidence_level, r.source_url)).filter(Boolean) as Item[], updated: latest(locale, rows.rows.map((r) => r.updated_at || r.ingested_at || r.created_at)) };
  }
  if (pageKey === "hypotheses") {
    const rows = await getRows<Hypothesis>("hypotheses", { select: "id,title,description,hypothesis_type,confidence_level,novelty_score,feasibility_score,urgency,ai_reasoning,recommended_action,status,outcome,reviewed_at,updated_at,created_at", order: "created_at.desc", limit: 12 });
    return { ...emptyData, evidence: rows.rows.map((r) => hypothesisItem(r, locale)).filter(Boolean) as Item[], questions: rows.rows.map((r) => item(r.title, r.recommended_action, rowSource("hypotheses", r.id), r.status, undefined, locale)).filter(Boolean) as Item[], risks: rows.rows.map((r) => item(r.title, r.outcome, rowSource("hypotheses", r.id), r.status, undefined, locale)).filter(Boolean) as Item[], updated: latest(locale, rows.rows.map((r) => r.updated_at || r.reviewed_at || r.created_at)) };
  }
  if (pageKey === "therapies") {
    const rows = await getRows<Therapy>("therapies", { select: "id,name,therapy_type,mechanism_of_action,evidence_in_hie,evidence_summary,clinical_status,aleksandra_eligible,aleksandra_status,aleksandra_notes,ai_assessment,confidence_level,updated_at,created_at", order: "updated_at.desc", limit: 12 });
    return { ...emptyData, evidence: rows.rows.map(therapyItem).filter(Boolean) as Item[], risks: rows.rows.map((r) => item(r.name, r.aleksandra_notes, rowSource("therapies", r.id), r.aleksandra_status)).filter(Boolean) as Item[], questions: rows.rows.map((r) => item(r.name, r.ai_assessment, rowSource("therapies", r.id), r.confidence_level)).filter(Boolean) as Item[], updated: latest(locale, rows.rows.map((r) => r.updated_at || r.created_at)) };
  }
  if (pageKey === "brain") {
    const rows = await getRows<BrainRegion>("brain_regions", { select: "id,name,name_ka,hemisphere,region_type,primary_functions,functional_networks,damage_status,damage_description,plasticity_potential,plasticity_notes,updated_at,created_at", order: "updated_at.desc", limit: 20 });
    return { ...emptyData, evidence: rows.rows.map((r) => brainItem(r, locale)).filter(Boolean) as Item[], updated: latest(locale, rows.rows.map((r) => r.updated_at || r.created_at)) };
  }
  if (pageKey === "timeline") {
    const rows = await getRows<Timeline>("aleksandra_timeline", { select: "id,event_date,event_type,title,title_ka,description,description_ka,source,source_url,created_at", order: "event_date.desc", limit: 20 });
    return { ...emptyData, evidence: rows.rows.map((r) => timelineItem(r, locale)).filter(Boolean) as Item[], updated: latest(locale, rows.rows.map((r) => r.event_date || r.created_at)) };
  }
  if (pageKey === "cohorts") {
    const rows = await getRows<Trial>("clinical_trials", { select: "id,nct_id,title,condition,intervention,phase,status,location,eligibility_notes,relevance_notes,source_url,updated_at,created_at", order: "updated_at.desc", limit: 12 });
    return { ...emptyData, evidence: rows.rows.map(trialItem).filter(Boolean) as Item[], updated: latest(locale, rows.rows.map((r) => r.updated_at || r.created_at)) };
  }
  if (pageKey === "data-integrations") {
    const rows = await getRows<Ingestion>("ingestion_log", { select: "id,source,query_used,results_found,new_papers_added,hypotheses_generated,high_relevance_count,status,error_message,started_at,completed_at", order: "started_at.desc", limit: 12 });
    return { ...emptyData, evidence: rows.rows.map((r) => ingestionItem(r, locale)).filter(Boolean) as Item[], risks: rows.rows.map((r) => item(r.source, r.error_message, rowSource("ingestion_log", r.id), r.status)).filter(Boolean) as Item[], updated: latest(locale, rows.rows.map((r) => r.completed_at || r.started_at)) };
  }
  if (pageKey === "alerts") {
    const rows = await getRows<Alert>("alerts_log", { select: "id,tier,event_kind,confidence,payload,delivered_at,blocked_reason,created_at", order: "created_at.desc", limit: 12 });
    return { ...emptyData, evidence: rows.rows.map((r) => alertItem(r, locale)).filter(Boolean) as Item[], risks: rows.rows.map((r) => item(join([r.tier, r.event_kind], " / "), r.blocked_reason, rowSource("alerts_log", r.id), date(r.created_at, locale))).filter(Boolean) as Item[], updated: latest(locale, rows.rows.map((r) => r.delivered_at || r.created_at)) };
  }
  if (pageKey === "resources") {
    const [briefs, papers, hypotheses, therapies] = await Promise.all([
      getRows<Brief>("briefs", { select: "id,brief_week,pdf_r2_path,sections,generated_at", order: "generated_at.desc", limit: 1 }),
      getRows<Paper>("papers", { select: "id,title,journal,publication_year,relevance_score,ai_summary,source,source_url,pmid,doi,ingested_at,updated_at,created_at", order: "ingested_at.desc", limit: 5 }),
      getRows<Hypothesis>("hypotheses", { select: "id,title,description,confidence_level,recommended_action,status,updated_at,created_at", order: "created_at.desc", limit: 5 }),
      getRows<Therapy>("therapies", { select: "id,name,evidence_summary,aleksandra_status,ai_assessment,updated_at,created_at", order: "updated_at.desc", limit: 5 }),
    ]);
    const b = briefItems(briefs.rows[0], locale);
    return { ...emptyData, evidence: [...b, ...papers.rows.map(paperItem), ...hypotheses.rows.map((r) => hypothesisItem(r, locale)), ...therapies.rows.map(therapyItem)].filter(Boolean) as Item[], questions: b.filter((x) => x.source.includes("questions")), briefItems: b, updated: latest(locale, [...briefs.rows.map((r) => r.generated_at), ...papers.rows.map((r) => r.updated_at || r.created_at), ...hypotheses.rows.map((r) => r.updated_at || r.created_at), ...therapies.rows.map((r) => r.updated_at || r.created_at)]) };
  }
  if (pageKey === "knowledge" || pageKey === "how-it-works") {
    const [reports, ingestion] = await Promise.all([
      getRows<DiscoveryReport>("discovery_reports", { select: "id,report_date,report_type,title,executive_summary,papers_ingested,papers_analyzed,hypotheses_generated,trials_updated,created_at", order: "report_date.desc", limit: 8 }),
      getRows<Ingestion>("ingestion_log", { select: "id,source,query_used,results_found,new_papers_added,hypotheses_generated,status,error_message,started_at,completed_at", order: "started_at.desc", limit: 8 }),
    ]);
    return { ...emptyData, evidence: [...reports.rows.map((r) => reportItem(r, locale)), ...ingestion.rows.map((r) => ingestionItem(r, locale))].filter(Boolean) as Item[], risks: ingestion.rows.map((r) => item(r.source, r.error_message, rowSource("ingestion_log", r.id), r.status)).filter(Boolean) as Item[], updated: latest(locale, [...reports.rows.map((r) => r.created_at || r.report_date), ...ingestion.rows.map((r) => r.completed_at || r.started_at)]) };
  }
  if (pageKey === "audit" || pageKey === "support" || pageKey === "settings") {
    const rows = await getRows<Action>("manager_actions", { select: "id,action_type,target_table,source_input,approved_at,reversed_at,created_at", order: "created_at.desc", limit: 12 });
    return { ...emptyData, evidence: rows.rows.map((r) => actionItem(r, locale)).filter(Boolean) as Item[], risks: rows.rows.map((r) => item(join([r.action_type, r.target_table], " → "), r.reversed_at ? `reversed ${date(r.reversed_at, locale)}` : "", rowSource("manager_actions", r.id), date(r.created_at, locale))).filter(Boolean) as Item[], updated: latest(locale, rows.rows.map((r) => r.reversed_at || r.approved_at || r.created_at)) };
  }
  return emptyData;
}

function hasData(data: TopicData) {
  return data.metrics.length + data.evidence.length + data.uncertainty.length + data.risks.length + data.questions.length + data.briefItems.length > 0;
}

async function topic(locale: Locale, pageKey: PageKey): Promise<Topic> {
  return { ...shells[locale][pageKey], data: await load(pageKey, locale) };
}

function path(locale: Locale, key: PageKey) {
  return key === "today" ? `/${locale}` : `/${locale}/${key}`;
}

function Shell({ locale, active, children }: { locale: Locale; active: PageKey; children: ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <header className="border-b border-white/10 bg-slate-950/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-5 md:px-8">
          <div className="flex items-center justify-between gap-4">
            <Link href={`/${locale}`} className="text-sm font-black uppercase tracking-[0.32em] text-sky-200">ALEKSANDRA BRAIN</Link>
            <div className="flex gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-300"><Link href="/ka" className={locale === "ka" ? "text-white underline" : ""}>KA</Link><span>/</span><Link href="/en" className={locale === "en" ? "text-white underline" : ""}>EN</Link></div>
          </div>
          <nav className="flex gap-2 overflow-x-auto pb-1 text-sm">
            {order.map((key) => <Link key={key} href={path(locale, key)} className={`whitespace-nowrap rounded-full px-4 py-2 transition ${active === key ? "bg-sky-300 text-slate-950" : "bg-white/5 text-slate-300 hover:bg-white/10"}`}>{nav[locale][key]}</Link>)}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 md:px-8">{children}</main>
    </div>
  );
}

function NoData({ locale }: { locale: Locale }) {
  return <div className="rounded-3xl border border-dashed border-white/15 bg-white/[0.035] p-6 text-sm font-semibold text-slate-300">{locale === "ka" ? "მონაცემი არ არის" : "No data available"}</div>;
}

function Source({ source, url, locale }: { source: string; url?: string; locale: Locale }) {
  const label = locale === "ka" ? "წყარო" : "Source";
  return <p className="mt-3 text-xs font-bold uppercase tracking-[0.18em] text-sky-200">{label}: {url ? <a href={url} target="_blank" rel="noreferrer" className="underline decoration-dotted underline-offset-4">{source}</a> : source}</p>;
}

function ItemCard({ value, locale }: { value: Item; locale: Locale }) {
  return (
    <article className="rounded-3xl border border-white/10 bg-white/[0.045] p-5 shadow-2xl shadow-slate-950/20">
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between"><h3 className="text-lg font-black text-white">{value.title}</h3>{value.meta ? <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-bold text-slate-200">{value.meta}</span> : null}</div>
      {value.body ? <p className="mt-3 text-sm leading-6 text-slate-300">{value.body}</p> : null}
      <Source source={value.source} url={value.url} locale={locale} />
    </article>
  );
}

function MetricCard({ value, locale }: { value: Metric; locale: Locale }) {
  return <article className="rounded-3xl border border-white/10 bg-white/[0.045] p-5"><p className="text-xs font-bold uppercase tracking-[0.2em] text-sky-200">{value.label}</p><p className="mt-3 text-4xl font-black">{value.value}</p><Source source={value.source} locale={locale} /></article>;
}

function Section({ title, items, locale }: { title: string; items: Item[]; locale: Locale }) {
  return <section className="mt-8"><h2 className="mb-4 text-xl font-black text-white">{title}</h2>{items.length ? <PortalDocumentList items={items} locale={locale} /> : <NoData locale={locale} />}</section>;
}

function Body({ topic, locale }: { topic: Topic; locale: Locale }) {
  const labels = locale === "ka"
    ? { metrics: "რეალური მაჩვენებლები", evidence: "მონაცემები", uncertainty: "გაურკვევლობა", risks: "რისკები / ლიმიტები", questions: "ექიმთან კითხვები" }
    : { metrics: "Real metrics", evidence: "Data", uncertainty: "Uncertainty", risks: "Risks / limits", questions: "Doctor questions" };

  return (
    <>
      <section className="rounded-[2rem] border border-white/10 bg-white/[0.045] p-8">
        <p className="text-xs font-bold uppercase tracking-[0.28em] text-sky-200">{topic.eyebrow}</p>
        <h1 className="mt-4 max-w-4xl text-4xl font-black tracking-tight md:text-6xl">{topic.title}</h1>
        {topic.data.updated ? <p className="mt-4 text-sm font-semibold text-sky-200">{locale === "ka" ? "ბოლო განახლება" : "Last updated"}: {topic.data.updated}</p> : null}
      </section>
      {!hasData(topic.data) ? <div className="mt-8"><NoData locale={locale} /></div> : null}
      {topic.data.metrics.length ? <section className="mt-8"><h2 className="mb-4 text-xl font-black">{labels.metrics}</h2><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{topic.data.metrics.map((m) => <MetricCard key={`${m.source}-${m.label}`} value={m} locale={locale} />)}</div></section> : null}
      <Section title={labels.evidence} items={topic.data.evidence} locale={locale} />
      <Section title={labels.uncertainty} items={topic.data.uncertainty} locale={locale} />
      <Section title={labels.risks} items={topic.data.risks} locale={locale} />
      <Section title={labels.questions} items={topic.data.questions} locale={locale} />
    </>
  );
}

function DoctorBrief({ topic, locale }: { topic: Topic; locale: Locale }) {
  const items = topic.data.briefItems.length ? topic.data.briefItems : topic.data.questions;
  return (
    <section className="mt-8 rounded-[2rem] border border-white/10 bg-white/[0.045] p-6">
      <p className="text-xs font-bold uppercase tracking-[0.22em] text-sky-200">{locale === "ka" ? "ექიმთან წასაღები ბრიფი" : "Doctor brief"}</p>
      <div className="mt-5">{items.length ? <PortalDocumentList items={items} locale={locale} /> : <NoData locale={locale} />}</div>
    </section>
  );
}

export async function PortalHomeDashboard({ locale }: { locale: Locale }) {
  const current = await topic(locale, "today");
  return <Shell locale={locale} active="today"><Body topic={current} locale={locale} /><DoctorBrief topic={current} locale={locale} /></Shell>;
}

export async function PortalTopicPage({ locale, pageKey }: { locale: Locale; pageKey: PageKey }) {
  const current = await topic(locale, pageKey);
  return <Shell locale={locale} active={pageKey}><Body topic={current} locale={locale} />{pageKey === "resources" || pageKey === "today" || pageKey === "dashboard" ? <DoctorBrief topic={current} locale={locale} /> : null}</Shell>;
}
