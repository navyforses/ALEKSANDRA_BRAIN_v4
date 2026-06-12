import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import { buildPageMetadata, type Locale } from "@/lib/seo";
import JournalClient from "./JournalClient";
import { getRows } from "@/lib/supabase";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(locale, "audit");
}

async function fetchJournalData() {
  try {
    const [actions, ingestions, alerts] = await Promise.all([
      getRows("manager_actions", { limit: 15 }),
      getRows("ingestion_log", { limit: 15 }),
      getRows("alerts_log", { limit: 15 }),
    ]);
    return {
      actions: actions.rows || [],
      ingestions: ingestions.rows || [],
      alerts: alerts.rows || [],
    };
  } catch {
    return { actions: [], ingestions: [], alerts: [] };
  }
}

export default async function JournalPage({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  const dbData = await fetchJournalData();

  return <JournalClient locale={locale} dbData={dbData} />;
}
