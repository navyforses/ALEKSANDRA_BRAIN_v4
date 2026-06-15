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
        // Valid JSON: trust the structured render. If the object carries no
        // human-readable text (e.g. a metadata blob like therapies.ai_assessment
        // = {source_hypothesis_id, target_pathway, …}), return "" — NEVER fall
        // through to dumping the raw JSON at the reader (CLAUDE.md: no metadata).
        return flatten(JSON.parse(trimmed), locale);
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
  // Bilingual JSONB {en, ka} since migration 026 (was TEXT). flatten() already
  // renders {en, ka} and falls back across locales; typed as BilingualField so
  // a plain string from a not-yet-backfilled row is still accepted.
  ai_summary?: BilingualField;
  ai_key_findings?: unknown;
  ai_aleksandra_implications?: BilingualField;
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
  name?: BilingualField;
  therapy_type?: string;
  // JSONB {en, ka} (mechanism_of_action since migration 027); evidence_summary
  // already JSONB. flatten() tolerates a plain string too, for not-yet-migrated rows.
  mechanism_of_action?: BilingualField;
  evidence_in_hie?: string;
  evidence_summary?: BilingualField;
  clinical_status?: string;
  aleksandra_status?: string;
  aleksandra_notes?: string;
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
  // ai_assessment holds pipeline metadata ({source_hypothesis_id, …}), not prose
  // — it is deliberately NOT surfaced to the reader.
  const notes = flatten(row.aleksandra_notes, locale);
  const hasProvenance = Boolean(row.evidence_in_hie || row.evidence_summary || row.clinical_status);
  return {
    id: row.id,
    kind: "therapy",
    title: cleanTitle(row.name, locale) || "—",
    summary: mechanism || evidence || "",
    detail: [mechanism, evidence].filter(Boolean).join("\n\n"),
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
      // Surface the most clinically relevant, ANALYSED papers first — not the
      // most recently ingested, which buried the real findings under newest-first
      // noise and made the stream read as irrelevant.
      relevance_score: "gte.0.5",
      ai_summary: "not.is.null",
      order: "relevance_score.desc.nullslast",
      limit: 60,
    }),
    getRows<HypothesisRow>("hypotheses", {
      select:
        "id,title,description,hypothesis_type,confidence_level,novelty_score,urgency,ai_reasoning,recommended_action,status,created_at,updated_at",
      order: "created_at.desc",
      limit: 30,
    }),
    getRows<TherapyRow>("therapies", {
      select:
        "id,name,therapy_type,mechanism_of_action,evidence_in_hie,evidence_summary,clinical_status,aleksandra_status,aleksandra_notes,confidence_level,updated_at,created_at",
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

// --- Clinical Trials ---------------------------------------------------------

export interface TrialLocationSummary {
  facility: string;
  city: string;
  state: string;
  country: string;
  status: string;
}

export interface TrialItem {
  nctId: string;
  title: string;
  summary: string;
  status: string;
  phase: string;
  intervention: string;
  minAge: string;
  maxAge: string;
  /** Legacy flat-string array retained for backwards compat (LocationLine in page.tsx). */
  locations: string[];
  /** Structured location objects from the JSONB column. */
  locationStructs: TrialLocationSummary[];
  /** Unique non-empty country names for this trial. */
  countries: string[];
  /** First (or most representative) site for compact display. */
  primaryLocation: { city: string; country: string } | null;
  isUs: boolean;
  isInternational: boolean;
  issues: string[];
  lastChecked?: string;
  startDate: string | null;
  coordinatorName: string;
  coordinatorEmail: string;
  piName: string;
  piEmail: string;
}

export interface TrialsView {
  configured: boolean;
  eligible: TrialItem[];
  needsReview: TrialItem[];
}

export interface TrialLocation {
  facility: string;
  city: string;
  state: string;
  country: string;
  status: string;
  isUs: boolean;
}

export interface TrialDetail {
  nctId: string;
  title: string;
  briefSummary: string;
  detailedDescription: string;
  eligibilityCriteria: string;
  conditions: string[];
  status: string;
  phase: string;
  studyType: string;
  intervention: string;
  minAge: string;
  maxAge: string;
  locations: TrialLocation[];
  isUs: boolean;
  isInternational: boolean;
  piName: string;
  piEmail: string;
  coordinatorName: string;
  coordinatorEmail: string;
  startDate: string;
  estimatedCompletion: string;
  lastUpdated: string;
  aleksandraStatus: string;
  eligibilityIssues: string[];
  lastChecked: string;
}

interface TrialRow {
  nct_id?: string;
  title?: unknown;
  brief_summary?: unknown;
  overall_status?: string;
  phase?: string;
  study_type?: string;
  intervention_name?: string;
  min_age?: string;
  max_age?: string;
  eligibility_criteria?: unknown;
  locations?: unknown;
  aleksandra_eligible?: boolean;
  eligibility_issues?: string[] | null;
  aleksandra_status?: string;
  last_checked?: string;
  // Phase D additions
  pi_name?: string;
  pi_email?: string;
  coordinator_name?: string;
  coordinator_email?: string;
  start_date?: string;
}

// Enriched row shape — all columns from Phase C Wave 1 enrichment.
interface TrialDetailRow {
  nct_id?: string;
  title?: unknown;
  brief_summary?: unknown;
  detailed_description?: unknown;
  eligibility_criteria?: unknown;
  conditions?: unknown;
  overall_status?: string;
  phase?: string;
  study_type?: string;
  intervention_name?: string;
  min_age?: string;
  max_age?: string;
  locations?: unknown;
  pi_name?: string;
  pi_email?: string;
  coordinator_name?: string;
  coordinator_email?: string;
  start_date?: string;
  estimated_completion?: string;
  last_updated?: string;
  aleksandra_eligible?: boolean;
  eligibility_issues?: string[] | null;
  aleksandra_status?: string;
  last_checked?: string;
}

// Tokens that indicate a US site in the locations array.
const US_TOKENS = ["united states", "usa", "u.s."];

function isUsLocation(loc: string): boolean {
  const lower = loc.toLowerCase();
  return US_TOKENS.some((t) => lower.includes(t));
}

function mapTrial(row: TrialRow, locale: Locale): TrialItem {
  // Parse JSONB locations array (may be structured objects or legacy strings).
  const structs = parseLocations(row.locations);

  // Unique non-empty country strings — used for the filter chips.
  const countries = Array.from(
    new Set(structs.map((l) => l.country).filter(Boolean)),
  );

  // Legacy flat string array for the existing LocationLine component.
  const flatLocations: string[] = structs.length > 0
    ? structs.map((l) =>
        [l.city, l.state, l.country].filter(Boolean).join(", "),
      )
    : [];

  // If no structs, fall back to a flat string array in the raw column
  // (older rows may store string[] directly).
  const legacyFlat: string[] = flatLocations.length === 0 && Array.isArray(row.locations)
    ? (row.locations as unknown[]).filter((l): l is string => typeof l === "string")
    : [];
  const allFlat = flatLocations.length > 0 ? flatLocations : legacyFlat;

  const hasUs = structs.length > 0
    ? structs.some((l) => US_TOKENS.some((t) => l.country.toLowerCase().includes(t)))
    : allFlat.some(isUsLocation);
  const hasIntl = structs.length > 0
    ? structs.some((l) => !US_TOKENS.some((t) => l.country.toLowerCase().includes(t)))
    : allFlat.some((l) => !isUsLocation(l));

  // Best primary location: prefer US site first, then first entry.
  const usSite = structs.find((l) =>
    US_TOKENS.some((t) => l.country.toLowerCase().includes(t)),
  );
  const firstSite = structs[0] ?? null;
  const primary = usSite ?? firstSite;

  return {
    nctId: row.nct_id ?? "",
    title: cleanTitle(row.title, locale) || "—",
    summary: flatten(row.brief_summary, locale),
    status: row.overall_status ?? "",
    phase: row.phase ?? "",
    intervention: row.intervention_name ?? "",
    minAge: row.min_age ?? "",
    maxAge: row.max_age ?? "",
    locations: allFlat,
    locationStructs: structs,
    countries,
    primaryLocation: primary ? { city: primary.city, country: primary.country } : null,
    isUs: hasUs,
    isInternational: hasIntl || (!hasUs && (structs.length > 0 || allFlat.length > 0)),
    issues: Array.isArray(row.eligibility_issues) ? row.eligibility_issues : [],
    lastChecked: row.last_checked,
    startDate: row.start_date ?? null,
    coordinatorName: row.coordinator_name ?? "",
    coordinatorEmail: row.coordinator_email ?? "",
    piName: row.pi_name ?? "",
    piEmail: row.pi_email ?? "",
  };
}

export async function fetchClinicalTrials(locale: Locale): Promise<TrialsView> {
  const result = await getRows<TrialRow>("clinical_trials", {
    select:
      "nct_id,title,brief_summary,overall_status,phase,study_type,intervention_name,min_age,max_age,eligibility_criteria,locations,aleksandra_eligible,eligibility_issues,aleksandra_status,last_checked,pi_name,pi_email,coordinator_name,coordinator_email,start_date",
    aleksandra_status: "in.(identified,evaluating)",
    order: "last_checked.desc",
    limit: "200",
  });

  const configured = result.configured;
  const eligible: TrialItem[] = [];
  const needsReview: TrialItem[] = [];

  for (const row of result.rows) {
    const item = mapTrial(row, locale);
    if (row.aleksandra_status === "identified") {
      eligible.push(item);
    } else if (row.aleksandra_status === "evaluating") {
      needsReview.push(item);
    }
  }

  return { configured, eligible, needsReview };
}

function parseLocations(raw: unknown): TrialLocation[] {
  // Locations stored as JSONB array of {facility, city, state, country, status}
  // or a plain string array from older rows.
  if (!raw) return [];
  const arr = Array.isArray(raw) ? raw : [];
  return arr
    .map((entry): TrialLocation | null => {
      if (entry && typeof entry === "object" && !Array.isArray(entry)) {
        const obj = entry as Record<string, unknown>;
        const country = String(obj.country ?? "").trim();
        return {
          facility: String(obj.facility ?? "").trim(),
          city: String(obj.city ?? "").trim(),
          state: String(obj.state ?? "").trim(),
          country,
          status: String(obj.status ?? "").trim(),
          isUs: US_TOKENS.some((t) => country.toLowerCase().includes(t)),
        };
      }
      // Flat string fallback — treat entire string as country/facility.
      if (typeof entry === "string" && entry.trim()) {
        const loc = entry.trim();
        return {
          facility: "",
          city: "",
          state: "",
          country: loc,
          status: "",
          isUs: US_TOKENS.some((t) => loc.toLowerCase().includes(t)),
        };
      }
      return null;
    })
    .filter((l): l is TrialLocation => l !== null);
}

function parseConditions(raw: unknown, locale: Locale): string[] {
  // Conditions stored as JSONB array of en strings, or JSONB {en, ka} objects.
  if (!raw) return [];
  const arr = Array.isArray(raw) ? raw : [];
  return arr
    .map((entry) => {
      if (typeof entry === "string") return entry.trim();
      if (entry && typeof entry === "object") {
        const obj = entry as Record<string, unknown>;
        return (String(obj[locale] ?? obj.en ?? "")).trim();
      }
      return "";
    })
    .filter(Boolean);
}

function mapTrialDetail(row: TrialDetailRow, locale: Locale): TrialDetail {
  const locations = parseLocations(row.locations);
  const hasUs = locations.some((l) => l.isUs);
  const hasIntl = locations.some((l) => !l.isUs);

  return {
    nctId: row.nct_id ?? "",
    title: cleanTitle(row.title, locale) || "—",
    briefSummary: flatten(row.brief_summary, locale),
    detailedDescription: flatten(row.detailed_description, locale),
    eligibilityCriteria: flatten(row.eligibility_criteria, locale),
    conditions: parseConditions(row.conditions, locale),
    status: row.overall_status ?? "",
    phase: row.phase ?? "",
    studyType: row.study_type ?? "",
    intervention: row.intervention_name ?? "",
    minAge: row.min_age ?? "",
    maxAge: row.max_age ?? "",
    locations,
    isUs: hasUs,
    isInternational: hasIntl || (!hasUs && locations.length > 0),
    piName: row.pi_name ?? "",
    piEmail: row.pi_email ?? "",
    coordinatorName: row.coordinator_name ?? "",
    coordinatorEmail: row.coordinator_email ?? "",
    startDate: row.start_date ?? "",
    estimatedCompletion: row.estimated_completion ?? "",
    lastUpdated: row.last_updated ?? "",
    aleksandraStatus: row.aleksandra_status ?? "",
    eligibilityIssues: Array.isArray(row.eligibility_issues) ? row.eligibility_issues : [],
    lastChecked: row.last_checked ?? "",
  };
}

export async function fetchTrialDetail(
  locale: Locale,
  nctId: string,
): Promise<{ configured: boolean; trial: TrialDetail | null }> {
  const result = await getRows<TrialDetailRow>("clinical_trials", {
    select:
      "nct_id,title,brief_summary,detailed_description,eligibility_criteria,conditions,overall_status,phase,study_type,intervention_name,min_age,max_age,locations,pi_name,pi_email,coordinator_name,coordinator_email,start_date,estimated_completion,last_updated,aleksandra_eligible,eligibility_issues,aleksandra_status,last_checked",
    nct_id: `eq.${nctId}`,
    limit: "1",
  });

  if (!result.configured) {
    return { configured: false, trial: null };
  }
  const row = result.rows[0];
  if (!row) {
    return { configured: true, trial: null };
  }
  return { configured: true, trial: mapTrialDetail(row, locale) };
}

export interface TodayView {
  status: WorkingStatus;
  attention: ResearchItem[];
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
        // Attention is chosen by relevance below, so fetch by relevance too —
        // otherwise a high-relevance paper ingested earlier never reaches the
        // home surface (it fell outside the newest-8 window).
        order: "relevance_score.desc.nullslast",
        limit: 12,
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
  const attention: ResearchItem[] = [];

  for (const row of papers.rows) {
    if (attention.filter((a) => a.kind === "paper").length >= 3) break;
    if ((row.relevance_score ?? 0) >= 0.75) {
      attention.push(mapPaper(row, locale));
    }
  }
  for (const row of hypotheses.rows) {
    if (attention.filter((a) => a.kind === "hypothesis").length >= 2) break;
    const status_ = (row.status || "").toLowerCase();
    const conf = (row.confidence_level || "").toLowerCase();
    if (["promising", "pursuing"].includes(status_) || conf === "high") {
      attention.push(mapHypothesis(row, locale));
    }
  }
  for (const row of therapies.rows) {
    if (attention.some((a) => a.kind === "therapy")) break;
    const st = (row.aleksandra_status || "").toLowerCase();
    if (["active", "eligible", "considering", "pursuing"].includes(st)) {
      attention.push(mapTherapy(row, locale));
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
