import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import { buildPageMetadata, type Locale } from "@/lib/seo";
import LibraryClient from "./LibraryClient";
import { getRows } from "@/lib/supabase";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(locale, "knowledge");
}

// Fetch live database values from Supabase to merge with our clean fallbacks
async function fetchDbData() {
  try {
    const [papers, hypotheses, therapies] = await Promise.all([
      getRows("papers", { limit: 20 }),
      getRows("hypotheses", { limit: 20 }),
      getRows("therapies", { limit: 20 }),
    ]);
    return {
      papers: papers.rows || [],
      hypotheses: hypotheses.rows || [],
      therapies: therapies.rows || [],
    };
  } catch {
    return { papers: [], hypotheses: [], therapies: [] };
  }
}

export default async function LibraryPage({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  const dbData = await fetchDbData();

  return <LibraryClient locale={locale} dbData={dbData} />;
}
