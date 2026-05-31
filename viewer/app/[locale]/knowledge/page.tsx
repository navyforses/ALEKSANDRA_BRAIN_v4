import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import { PortalTopicPage } from "@/components/portal/PortalContent";
import { buildPageMetadata, type Locale } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(locale, "knowledge");
}

export default async function PortalRoutePage({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <PortalTopicPage locale={locale} pageKey="knowledge" />;
}
