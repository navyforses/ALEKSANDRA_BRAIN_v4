// Country name localisation for the clinical trials surface.
//
// Only maps well-known countries that appear in clinical trial registrations.
// Unknown countries fall back to the English string — NEVER fabricate a
// translation for an unfamiliar name.

// ---------------------------------------------------------------------------
// Alias table: maps every raw registry variant → one canonical English key.
// Keys are lower-cased and trimmed before lookup.
// ---------------------------------------------------------------------------

const ALIAS_MAP: Record<string, string> = {
  // United States
  "united states": "United States",
  "united states of america": "United States",
  "us": "United States",
  "usa": "United States",
  "u.s.": "United States",
  "u.s.a.": "United States",
  // United Kingdom
  "united kingdom": "United Kingdom",
  "uk": "United Kingdom",
  "u.k.": "United Kingdom",
  "great britain": "United Kingdom",
  "britain": "United Kingdom",
  "gb": "United Kingdom",
  "england": "United Kingdom",
  "scotland": "United Kingdom",
  "wales": "United Kingdom",
  "northern ireland": "United Kingdom",
  // Türkiye
  "turkey": "Türkiye",
  "türkiye": "Türkiye",
  "turkey (türkiye)": "Türkiye",
  // Korea
  "south korea": "Korea, South",
  "republic of korea": "Korea, South",
  "korea, republic of": "Korea, South",
  "korea (the republic of)": "Korea, South",
  // Czechia
  "czech republic": "Czechia",
  "czechia": "Czechia",
  // Russia
  "russian federation": "Russia",
  "russia": "Russia",
  // Vietnam
  "viet nam": "Vietnam",
  "vietnam": "Vietnam",
  // Iran
  "iran (islamic republic of)": "Iran",
  "iran, islamic republic of": "Iran",
  "iran": "Iran",
  // Taiwan
  "taiwan, province of china": "Taiwan",
  "taiwan (province of china)": "Taiwan",
  "taiwan": "Taiwan",
  // Bolivia
  "bolivia (plurinational state of)": "Bolivia",
  "bolivia, plurinational state of": "Bolivia",
  "bolivia": "Bolivia",
  // Venezuela
  "venezuela (bolivarian republic of)": "Venezuela",
  "venezuela": "Venezuela",
  // Syria
  "syrian arab republic": "Syria",
  "syria": "Syria",
  // Moldova
  "moldova (republic of)": "Moldova",
  "republic of moldova": "Moldova",
  "moldova": "Moldova",
  // Palestine
  "palestine, state of": "Palestine",
  "occupied palestinian territory": "Palestine",
  "palestine": "Palestine",
};

/**
 * Return a single canonical English country key for any raw registry string.
 *
 * - Trims whitespace, lowercases, strips trailing punctuation for the lookup.
 * - Falls back to Title-Casing the trimmed original when no alias matches
 *   (so "bulgaria" → "Bulgaria", "ITALY" → "Italy").
 */
export function canonicalCountry(raw: string): string {
  if (!raw) return raw;
  const trimmed = raw.trim();
  const key = trimmed.toLowerCase();
  if (ALIAS_MAP[key]) return ALIAS_MAP[key];
  // Title-case fallback: uppercase first letter of each word.
  return trimmed
    .split(/\s+/)
    .map((w) => (w.length > 0 ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
}

// ---------------------------------------------------------------------------
// KA translation map — keyed by CANONICAL English names only.
// ---------------------------------------------------------------------------

const KA_COUNTRY_MAP: Record<string, string> = {
  "United States": "აშშ",
  "United Kingdom": "გაერთიანებული სამეფო",
  "Canada": "კანადა",
  "Germany": "გერმანია",
  "France": "საფრანგეთი",
  "Italy": "იტალია",
  "Spain": "ესპანეთი",
  "China": "ჩინეთი",
  "Japan": "იაპონია",
  "Australia": "ავსტრალია",
  "Netherlands": "ნიდერლანდები",
  "Sweden": "შვედეთი",
  "Norway": "ნორვეგია",
  "Denmark": "დანია",
  "Finland": "ფინეთი",
  "Switzerland": "შვეიცარია",
  "Austria": "ავსტრია",
  "Belgium": "ბელგია",
  "Israel": "ისრაელი",
  "Korea, South": "სამხრეთ კორეა",
  "Brazil": "ბრაზილია",
  "India": "ინდოეთი",
  "Poland": "პოლონეთი",
  "Czechia": "ჩეხეთი",
  "Portugal": "პორტუგალია",
  "New Zealand": "ახალი ზელანდია",
  "Ireland": "ირლანდია",
  "Greece": "საბერძნეთი",
  "Türkiye": "თურქეთი",
  "Russia": "რუსეთი",
  "Mexico": "მექსიკა",
  "Argentina": "არგენტინა",
  "Hungary": "უნგრეთი",
  "Romania": "რუმინეთი",
  "Georgia": "საქართველო",
  "Bulgaria": "ბულგარეთი",
  "Colombia": "კოლომბია",
  "Vietnam": "ვიეტნამი",
  "Iran": "ირანი",
  "Taiwan": "ტაივანი",
};

/**
 * Translate a CANONICAL country name to the requested locale.
 * Input must already be a canonical key (run through canonicalCountry() first).
 * Falls back to the canonical English string for unmapped countries.
 */
export function localizeCountry(country: string, locale: "en" | "ka"): string {
  if (!country) return country;
  if (locale !== "ka") return country;
  return KA_COUNTRY_MAP[country] ?? country;
}

/**
 * Sort a list of canonical country names with "United States" first, then A–Z.
 */
export function sortCountries(
  countries: string[],
  locale: "en" | "ka",
): string[] {
  return [...countries].sort((a, b) => {
    const aIsUs = a === "United States";
    const bIsUs = b === "United States";
    if (aIsUs && !bIsUs) return -1;
    if (!aIsUs && bIsUs) return 1;
    return localizeCountry(a, locale).localeCompare(
      localizeCountry(b, locale),
      locale === "ka" ? "ka-GE" : "en-US",
    );
  });
}
