// Phase 6 i18n display helper — locked decision D-03 in 06-CONTEXT.md.
// Source of truth: .planning/phases/06-bilingual-system-i18n-.../06-CONTEXT.md §D-03.
// Pure function, no dependencies — usable from both Server and Client Components.
export type BilingualField = string | { en?: string; ka?: string } | null | undefined;

export function displayField(field: BilingualField, locale: 'en' | 'ka'): string {
  if (field == null) return '';
  if (typeof field === 'string') return field;        // legacy TEXT row tolerance
  return field[locale] ?? field.en ?? '';              // strict locale → English fallback
}
