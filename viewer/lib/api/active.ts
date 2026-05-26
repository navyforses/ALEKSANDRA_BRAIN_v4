// viewer/lib/api/active.ts — Phase 7.6 typed API client for Active Learning.
//
// Mirrors Phase 7.4 active_questions table shape. MOCK_MODE returns 2 sample
// questions tied to dimensions with the most posterior uncertainty.

const MOCK_MODE: boolean =
  !process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_MOCK_MODE === "true";

const API_BASE: string = process.env.NEXT_PUBLIC_API_URL ?? "";

// ---------------------------------------------------------------------------
// Types — mirror migration 020 active_questions schema (Phase 7.4)
// ---------------------------------------------------------------------------
export type QuestionStatus =
  | "open"
  | "responded"
  | "skipped"
  | "expired";

export interface ActiveQuestion {
  id: string;
  dim_name: string;
  prompt_en: string;
  prompt_ka: string;
  asked_at: string; // ISO 8601
  responded_at: string | null;
  status: QuestionStatus;
  response_text: string | null;
  week_iso: string; // e.g. "2026-W51"
  expected_kl_gain: number;
}

export interface ParsedResponse {
  question_id: string;
  parsed_value: number | string | null;
  parsed_confidence: number;
  raw_text: string;
}

// ---------------------------------------------------------------------------
// Mock data (no PHI; descriptive placeholder prompts only)
// ---------------------------------------------------------------------------
const MOCK_QUESTIONS: ActiveQuestion[] = [
  {
    id: "q_mock_001",
    dim_name: "head_control_seconds",
    prompt_en:
      "About how many seconds can ალექსანდრა hold her head up while sitting supported this week?",
    prompt_ka:
      "ამ კვირაში დაახლოებით რამდენი წამი იჭერს ალექსანდრა თავს ვერტიკალურად მხარდაჭერით ჯდომისას?",
    asked_at: "2026-12-22T09:00:00Z",
    responded_at: null,
    status: "open",
    response_text: null,
    week_iso: "2026-W52",
    expected_kl_gain: 0.42,
  },
  {
    id: "q_mock_002",
    dim_name: "eye_tracking_seconds",
    prompt_en:
      "Roughly how long does ალექსანდრა follow a moving toy with her eyes before disengaging?",
    prompt_ka:
      "დაახლოებით რამდენ ხანს ადევნებს ალექსანდრა მოძრავ სათამაშოს თვალით ყურადღების გადატანამდე?",
    asked_at: "2026-12-22T09:00:00Z",
    responded_at: "2026-12-23T14:30:00Z",
    status: "responded",
    response_text: "Around 4 seconds at the best moments today.",
    week_iso: "2026-W52",
    expected_kl_gain: 0.38,
  },
];

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------
export async function fetchActiveQuestions(
  weekIso?: string,
): Promise<ActiveQuestion[]> {
  if (MOCK_MODE) {
    if (weekIso) {
      return MOCK_QUESTIONS.filter((q) => q.week_iso === weekIso);
    }
    return MOCK_QUESTIONS;
  }
  try {
    const url = weekIso
      ? `${API_BASE}/api/active/questions?week=${encodeURIComponent(weekIso)}`
      : `${API_BASE}/api/active/questions`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) {
      return MOCK_QUESTIONS;
    }
    return (await res.json()) as ActiveQuestion[];
  } catch {
    return MOCK_QUESTIONS;
  }
}

export const __MOCK_MODE__ = MOCK_MODE;
