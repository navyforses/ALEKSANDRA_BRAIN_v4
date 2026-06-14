// Server-side data layer for the family-facing surfaces.
//
// Everything the reader sees is shaped here, once, with one rule held
// above all others (CLAUDE.md): never fabricate. Every research item
// carries a `source`; when no provenance exists, `source` is `null` and
// the UI says so plainly rather than inventing one.
//
// This module only reads from Supabase REST via lib/supabase.ts (service
// role stays on the server). It never touches MRI/PHI — that lives
// client-side only, in the browser, on the Brain surface.

import type { BilingualField } from "@/lib/i18n";
import type { Locale } from "@/lib/seo";
import { getCount, getRows } from "@/lib/supabase";

export type ResearchKind = "paper" | "hypothesis" | "therapy";

export interface ResearchItem {
  id: string;
  kind: ResearchKind;
  title: string;
  summary: string; // one calm line for the stream
  detail: string; // the fuller text for the reader
  implication?: string; // "what this means for Aleksandra", when present
  meta: string[]; // small chips: journal, year, status, confidence…
  source: string | null; // provenance — null is honest, not hidden
  url?: string;
  date?: string; // ISO, for sorting
}

export interface AttentionItem {
  id: string;
  kind: ResearchKind;
  title: string;
  note: string;
  source: string | null;
  url?: string;
}

export interface WorkingStatus {
  configured: boolean;
  scanning: boolean;
  lastScanAt?: string;
  lastScanSource?: string;
  counts: { papers: number; hypotheses: number; therapies: number };
}

export interface BriefLine {
  text: string;
  source?: string;
}
export interface BriefSection {
  label: string;
  lines: BriefLine[];
}
export interface BriefDoc {
  weekLabel?: string;
  generatedAt?: string;
  sections: BriefSection[];
}

// --- small, defensive formatting helpers ----------------------------------

// Flatten the messy shapes the pipeline stores (JSONB {en,ka}, arrays,
// AI objects, JSON-looking strings) into a single human string for the
// chosen locale, without ever dumping raw metadata at the reader.
function flatten(value: unknown, locale: Locale): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (
      (trimmed.startsWith("{") && trimmed.endsWith("}")) ||
      (trimmed.startsWith("[") && trimmed.endsWith("]"))
    ) {
      try {
        const rendered = flatten(JSON.parse(trimmed), locale);
        if (rendered) return rendered;
      } catch {
        /* only looked like JSON — keep the text */
      }
    }
    return trimmed;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return value
      .map((entry) => flatten(entry, locale))
      .filter(Boolean)
      .join("; ");
  }
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    // Prefer the requested locale, but treat an EMPTY string as missing and
    // fall back to the other locale — `??` alone keeps "" (e.g. a paper whose
    // ka title was never backfilled), which would otherwise show as a dash.
    const localized =
      flatten(obj[locale], locale) ||
      flatten(obj[locale === "ka" ? "en" : "ka"], locale);
    if (localized) return localized;
    const preferred = [
      "reasoning",
      "summary",
      "answer",
      "recommendation",
      "recommended_action",
      "assessment",
      "analysis",
      "narrative",
      "explanation",
      "conclusion",
      "description",
      "content",
      "text",
      "title",
      "name",
      "value",
    ]
      .map((key) => flatten(obj[key], locale))
      .find(Boolean);
    return preferred ?? "";
  }
  return "";
}

// Strip markdown artifacts the ka translation backfill left behind ('# ',
// '## ', '**bold**'). Applied to short display strings so a headline never
// shows a stray '#'.
function stripMarkdown(s: string): string {
  return s
    .replace(/^\s*#{1,6}\s+/gm, "")
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/__(.*?)__/g, "$1")
    .trim();
}

// A display title. Critically, this runs the value through `flatten` (which
// parses a JSON-encoded string like '{"en":...,"ka":...}' into the locale's
// text) — `displayField` does NOT, so a title stored as a JSON string would
// otherwise render as raw JSON on screen. Then it strips markdown leftovers.
function cleanTitle(value: unknown, locale: Locale): string {
  return stripMarkdown(flatten(value, locale)).replace(/^[-*]\s+/, "").trim();
}

function joinMeta(parts: Array<string | number | undefined | null | false>): string[] {
  return parts
    .map((p) => (p === null || p === undefined || p === false ? "" : String(p).trim()))
    .filter(Boolean);
}

export function formatDate(value: string | undefined, locale: Locale): string {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat(locale === "ka" ? "ka-GE" : "en-US", {
    year: "numeric",
    month: "short",
    day: "2-digit",
  }).format(parsed);
}

function relevancePct(value: number | undefined): string {
  if (value === undefined || value === null) return "";
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  return `${Math.round(n * 100)}%`;
}

function newest(values: Array<string | undefined>): string | undefined {
  return values
    .filter(Boolean)
    .map((v) => new Date(String(v)))
    .filter((d) => !Number.isNaN(d.getTime()))
    .sort((a, b) => b.getTime() - a.getTime())[0]
    ?.toISOString();
}

// --- row shapes (only the columns we read) --------------------------------

interface PaperRow {
  id: string;
  title?: BilingualField;
  abstract?: BilingualField;
  journal?: string;
  publication_year?: number;
  relevance_score?: number;
  ai_summary?: string;
  ai_key_findings?: unknown;
  ai_aleksandra_implications?: string;
  confidence_level?: string;
  source?: string;
  source_url?: string;
  pmid?: string;
  doi?: string;
  ingested_at?: string;
  updated_at?: string;
  created_at?: string;
}

interface HypothesisRow {
  id: string;
  title?: unknown;
  description?: unknown;
  hypothesis_type?: string;
  confidence_level?: string;
  novelty_score?: number;
  urgency?: string;
  ai_reasoning?: unknown;
  recommended_action?: unknown;
  status?: string;
  created_at?: string;
  updated_at?: string;
}

interface TherapyRow {
  id: string;
  name?: string;
  therapy_type?: string;
  mechanism_of_action?: string;
  evidence_in_hie?: string;
  evidence_summary?: string;
  clinical_status?: string;
  aleksandra_status?: string;
  aleksandra_notes?: string;
  ai_assessment?: string;
  confidence_level?: string;
  updated_at?: string;
  created_at?: string;
}

interface IngestionRow {
  id: string;
  source?: string;
  status?: string;
  new_papers_added?: number;
  started_at?: string;
  completed_at?: string;
}

interface BriefRow {
  id: string;
  brief_week?: string;
  sections?: Record<string, unknown>;
  generated_at?: string;
}

// --- mappers --------------------------------------------------------------

function paperProvenance(row: PaperRow): { source: string | null; url?: string } {
  const bits = joinMeta([
    row.source,
    row.pmid ? `PMID ${row.pmid}` : "",
    row.doi ? `DOI ${row.doi}` : "",
  ]);
  const url = row.source_url || (row.pmid ? `https://pubmed.ncbi.nlm.nih.gov/${row.pmid}/` : undefined);
  if (bits.length === 0 && !url) return { source: null };
  return { source: bits.join(" · ") || (url ?? null), url };
}

function mapPaper(row: PaperRow, locale: Locale): ResearchItem {
  const summary = flatten(row.ai_summary ?? row.abstract, locale);
  const findings = flatten(row.ai_key_findings, locale);
  const implication = flatten(row.ai_aleksandra_implications, locale);
  const { source, url } = paperProvenance(row);
  return {
    id: row.id,
    kind: "paper",
    title: cleanTitle(row.title, locale) || "—",
    summary: summary || findings || "",
    detail: [summary, findings].filter(Boolean).join("\n\n"),
    implication: implication || undefined,
    meta: joinMeta([
      row.journal,
      row.publication_year,
      row.relevance_score !== undefined ? `${relevancePct(row.relevance_score)}` : "",
      row.confidence_level,
    ]),
    source,
    url,
    date: row.ingested_at || row.updated_at || row.created_at,
  };
}

function mapHypothesis(row: HypothesisRow, locale: Locale): ResearchItem {
  const description = flatten(row.description, locale);
  const reasoning = flatten(row.ai_reasoning, locale);
  const action = flatten(row.recommended_action, locale);
  return {
    id: row.id,
    kind: "hypothesis",
    title: cleanTitle(row.title, locale) || "—",
    summary: description || reasoning || "",
    detail: [description, reasoning].filter(Boolean).join("\n\n"),
    implication: action || undefined,
    meta: joinMeta([row.hypothesis_type, row.status, row.confidence_level, row.urgency]),
    // A hypothesis is a proposal the system reasoned to, not a sourced
    // fact — so its provenance is named as exactly that, honestly.
    source: "ALEKSANDRA_BRAIN · hypothesis pipeline",
    date: row.created_at || row.updated_at,
  };
}

function mapTherapy(row: TherapyRow, locale: Locale): ResearchItem {
  const mechanism = flatten(row.mechanism_of_action, locale);
  const evidence = flatten(row.evidence_summary ?? row.evidence_in_hie, locale);
  const assessment = flatten(row.ai_assessment, locale);
  const notes = flatten(row.aleksandra_notes, locale);
  const hasProvenance = Boolean(row.evidence_in_hie || row.evidence_summary || row.clinical_status);
  return {
    id: row.id,
    kind: "therapy",
    title: cleanTitle(row.name, locale) || "—",
    summary: mechanism || evidence || assessment || "",
    detail: [mechanism, evidence, assessment].filter(Boolean).join("\n\n"),
    implication: notes || undefined,
    meta: joinMeta([
      row.therapy_type,
      row.clinical_status,
      row.aleksandra_status,
      row.confidence_level,
    ]),
    source: hasProvenance
      ? joinMeta([row.clinical_status, row.evidence_in_hie ? "evidence in HIE" : ""]).join(" · ") ||
        "clinical status on record"
      : null,
    date: row.updated_at || row.created_at,
  };
}

// --- public fetchers ------------------------------------------------------

export interface ResearchView {
  configured: boolean;
  items: ResearchItem[];
  updated?: string;
}

export async function fetchResearch(locale: Locale): Promise<ResearchView> {
  const [papers, hypotheses, therapies] = await Promise.all([
    getRows<PaperRow>("papers", {
      select:
        "id,title,abstract,journal,publication_year,relevance_score,ai_summary,ai_key_findings,ai_aleksandra_implications,confidence_level,source,source_url,pmid,doi,ingested_at,updated_at,created_at",
      order: "ingested_at.desc",
      limit: 30,
    }),
    getRows<HypothesisRow>("hypotheses", {
      select:
        "id,title,description,hypothesis_type,confidence_level,novelty_score,urgency,ai_reasoning,recommended_action,status,created_at,updated_at",
      order: "created_at.desc",
      limit: 30,
    }),
    getRows<TherapyRow>("therapies", {
      select:
        "id,name,therapy_type,mechanism_of_action,evidence_in_hie,evidence_summary,clinical_status,aleksandra_status,aleksandra_notes,ai_assessment,confidence_level,updated_at,created_at",
      order: "updated_at.desc",
      limit: 30,
    }),
  ]);

  const configured = papers.configured || hypotheses.configured || therapies.configured;
  const items = [
    ...papers.rows.map((r) => mapPaper(r, locale)),
    ...hypotheses.rows.map((r) => mapHypothesis(r, locale)),
    ...therapies.rows.map((r) => mapTherapy(r, locale)),
  ].filter((i) => i.title !== "—" || i.summary);

  const updated = newest(items.map((i) => i.date));
  return { configured, items, updated };
}

export interface TodayView {
  status: WorkingStatus;
  attention: AttentionItem[];
  brief: BriefDoc | null;
}

export async function fetchToday(locale: Locale): Promise<TodayView> {
  const [ingestion, papersCount, hypCount, thxCount, papers, hypotheses, therapies, brief] =
    await Promise.all([
      getRows<IngestionRow>("ingestion_log", {
        select: "id,source,status,new_papers_added,started_at,completed_at",
        order: "started_at.desc",
        limit: 6,
      }),
      getCount("papers"),
      getCount("hypotheses"),
      getCount("therapies"),
      getRows<PaperRow>("papers", {
        select:
          "id,title,relevance_score,ai_summary,ai_aleksandra_implications,source,source_url,pmid,doi,ingested_at",
        order: "ingested_at.desc",
        limit: 8,
      }),
      getRows<HypothesisRow>("hypotheses", {
        select: "id,title,description,status,confidence_level,recommended_action,created_at",
        order: "created_at.desc",
        limit: 12,
      }),
      getRows<TherapyRow>("therapies", {
        select: "id,name,aleksandra_status,aleksandra_notes,clinical_status,evidence_in_hie,updated_at",
        order: "updated_at.desc",
        limit: 8,
      }),
      fetchBrief(locale),
    ]);

  const configured = ingestion.configured || papersCount.configured;
  const recent = ingestion.rows[0];
  const status: WorkingStatus = {
    configured,
    scanning: ingestion.rows.some((r) => (r.status || "").toLowerCase() === "running"),
    lastScanAt: recent?.completed_at || recent?.started_at,
    lastScanSource: recent?.source,
    counts: {
      papers: papersCount.count,
      hypotheses: hypCount.count,
      therapies: thxCount.count,
    },
  };

  // "What needs you" — only genuinely high-signal items, each provenance-
  // bound. If nothing qualifies, we return an empty list and the surface
  // says so calmly rather than inventing urgency.
  const attention: AttentionItem[] = [];

  for (const row of papers.rows) {
    if (attention.filter((a) => a.kind === "paper").length >= 3) break;
    if ((row.relevance_score ?? 0) >= 0.75) {
      const mapped = mapPaper(row, locale);
      attention.push({
        id: mapped.id,
        kind: "paper",
        title: mapped.title,
        note: mapped.implication || mapped.summary,
        source: mapped.source,
        url: mapped.url,
      });
    }
  }
  for (const row of hypotheses.rows) {
    if (attention.filter((a) => a.kind === "hypothesis").length >= 2) break;
    const status_ = (row.status || "").toLowerCase();
    const conf = (row.confidence_level || "").toLowerCase();
    if (["promising", "pursuing"].includes(status_) || conf === "high") {
      const mapped = mapHypothesis(row, locale);
      attention.push({
        id: mapped.id,
        kind: "hypothesis",
        title: mapped.title,
        note: mapped.implication || mapped.summary,
        source: mapped.source,
      });
    }
  }
  for (const row of therapies.rows) {
    if (attention.some((a) => a.kind === "therapy")) break;
    const st = (row.aleksandra_status || "").toLowerCase();
    if (["active", "eligible", "considering", "pursuing"].includes(st)) {
      const mapped = mapTherapy(row, locale);
      attention.push({
        id: mapped.id,
        kind: "therapy",
        title: mapped.title,
        note: mapped.implication || mapped.summary,
        source: mapped.source,
      });
    }
  }

  return { status, attention, brief };
}

function humanizeKey(key: string, locale: Locale): string {
  const map: Record<string, { en: string; ka: string }> = {
    summary: { en: "Summary", ka: "მოკლე შინაარსი" },
    highlights: { en: "Highlights", ka: "მთავარი" },
    new_papers: { en: "New papers", ka: "ახალი ნაშრომები" },
    papers: { en: "Papers", ka: "ნაშრომები" },
    hypotheses: { en: "Hypotheses", ka: "ჰიპოთეზები" },
    therapies: { en: "Therapies", ka: "თერაპიები" },
    questions: { en: "Questions for the clinician", ka: "კითხვები ექიმთან" },
    actions: { en: "Suggested next steps", ka: "შემდეგი ნაბიჯები" },
    risks: { en: "Risks and limits", ka: "რისკები და ლიმიტები" },
    outreach: { en: "Outreach queue", ka: "საკონტაქტო რიგი" },
    summary_lines: { en: "This week, in short", ka: "ამ კვირას, მოკლედ" },
  };
  const hit = map[key.toLowerCase()];
  if (hit) return locale === "ka" ? hit.ka : hit.en;
  return key.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

function toBriefLines(value: unknown, locale: Locale): BriefLine[] {
  if (Array.isArray(value)) {
    return value
      .map((entry): BriefLine | null => {
        if (entry && typeof entry === "object" && !Array.isArray(entry)) {
          const obj = entry as Record<string, unknown>;
          const text = stripMarkdown(flatten(obj.text ?? obj.title ?? obj.summary ?? obj, locale));
          const source = flatten(obj.source ?? obj.url ?? obj.provenance, locale);
          if (!text) return null;
          return { text, source: source || undefined };
        }
        const text = stripMarkdown(flatten(entry, locale));
        return text ? { text } : null;
      })
      .filter((l): l is BriefLine => l !== null)
      .slice(0, 12);
  }
  const text = stripMarkdown(flatten(value, locale));
  return text ? [{ text }] : [];
}

export async function fetchBrief(locale: Locale): Promise<BriefDoc | null> {
  const result = await getRows<BriefRow>("briefs", {
    select: "id,brief_week,sections,generated_at",
    order: "generated_at.desc",
    limit: 1,
  });
  const row = result.rows[0];
  if (!row || !row.sections) return null;

  const sections: BriefSection[] = [];
  for (const [key, value] of Object.entries(row.sections)) {
    const lines = toBriefLines(value, locale);
    if (lines.length) sections.push({ label: humanizeKey(key, locale), lines });
  }
  if (sections.length === 0) return null;

  return {
    weekLabel: row.brief_week,
    generatedAt: row.generated_at,
    sections,
  };
}
