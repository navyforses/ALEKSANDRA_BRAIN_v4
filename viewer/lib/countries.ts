// Country name localisation for the clinical trials surface.
//
// Only maps well-known countries that appear in clinical trial registrations.
// Unknown countries fall back to the English string — NEVER fabricate a
// translation for an unfamiliar name.

const KA_COUNTRY_MAP: Record<string, string> = {
  "united states": "აშშ",
  "usa": "აშშ",
  "u.s.": "აშშ",
  "u.s.a.": "აშშ",
  "united kingdom": "გაერთიანებული სამეფო",
  "uk": "გაერთიანებული სამეფო",
  "canada": "კანადა",
  "germany": "გერმანია",
  "france": "საფრანგეთი",
  "italy": "იტალია",
  "spain": "ესპანეთი",
  "china": "ჩინეთი",
  "japan": "იაპონია",
  "australia": "ავსტრალია",
  "netherlands": "ნიდერლანდები",
  "sweden": "შვედეთი",
  "norway": "ნორვეგია",
  "denmark": "დანია",
  "finland": "ფინეთი",
  "switzerland": "შვეიცარია",
  "austria": "ავსტრია",
  "belgium": "ბელგია",
  "israel": "ისრაელი",
  "south korea": "სამხრეთ კორეა",
  "korea, republic of": "სამხრეთ კორეა",
  "brazil": "ბრაზილია",
  "india": "ინდოეთი",
  "poland": "პოლონეთი",
  "czech republic": "ჩეხეთი",
  "czechia": "ჩეხეთი",
  "portugal": "პორტუგალია",
  "new zealand": "ახალი ზელანდია",
  "ireland": "ირლანდია",
  "greece": "საბერძნეთი",
  "turkey": "თურქეთი",
  "russia": "რუსეთი",
  "russian federation": "რუსეთი",
  "mexico": "მექსიკა",
  "argentina": "არგენტინა",
  "hungary": "უნგრეთი",
  "romania": "რუმინეთი",
  "georgia": "საქართველო",
};

/**
 * Translate a country name to the requested locale.
 * Falls back to the original English string for unmapped countries.
 */
export function localizeCountry(country: string, locale: "en" | "ka"): string {
  if (!country) return country;
  if (locale !== "ka") return country;
  return KA_COUNTRY_MAP[country.toLowerCase().trim()] ?? country;
}

/**
 * Sort a list of country names with "United States" first, then A–Z.
 */
export function sortCountries(
  countries: string[],
  locale: "en" | "ka",
): string[] {
  const US_KEYS = ["united states", "usa", "u.s.", "u.s.a."];
  return [...countries].sort((a, b) => {
    const aIsUs = US_KEYS.includes(a.toLowerCase());
    const bIsUs = US_KEYS.includes(b.toLowerCase());
    if (aIsUs && !bIsUs) return -1;
    if (!aIsUs && bIsUs) return 1;
    return localizeCountry(a, locale).localeCompare(
      localizeCountry(b, locale),
      locale === "ka" ? "ka-GE" : "en-US",
    );
  });
}
