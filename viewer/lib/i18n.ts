// Phase 6 i18n display helper — locked decision D-03 in 06-CONTEXT.md.
// Source of truth: .planning/phases/06-bilingual-system-i18n-.../06-CONTEXT.md §D-03.
// Pure function, no dependencies — usable from both Server and Client Components.
export type BilingualField = string | { en?: string; ka?: string } | null | undefined;

export function displayField(field: BilingualField, locale: 'en' | 'ka'): string {
  if (field == null) return '';
  if (typeof field === 'string') return field;        // legacy TEXT row tolerance
  return field[locale] ?? field.en ?? '';              // strict locale → English fallback
}

// Phase 6 Plan 06-08 — write-side shape contract.
// Mirrors single-language manager input into the {en, ka} JSONB shape that
// migration 012 expects. Used by any TypeScript caller that needs to INSERT
// into the 6 converted columns (aleksandra_timeline.title/description,
// hypotheses.title/description, therapies.name/evidence_summary).
// As of 06-08, viewer/app/api/manager/apply/route.ts is a pure proxy to the
// Python worker (scripts/manager/routing/apply_action.py) and never shapes
// payloads server-side — the Python writers are scheduled in 06-09 (Wave 3).
// This helper is kept available for future TypeScript callers; until then,
// the canonical bilingual emission lives in scripts/communicator/bilingual.py.
export function toBilingual(
  input: string | { en?: string; ka?: string } | null | undefined,
): { en: string; ka: string } | null {
  if (input == null) return null;
  if (typeof input === 'string') return { en: input, ka: input };
  if (typeof input === 'object') {
    return { en: input.en ?? '', ka: input.ka ?? input.en ?? '' };
  }
  return null;
}
