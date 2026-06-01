import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import { PortalTopicPage } from "@/components/portal/PortalContent";
import { buildPageMetadata, type Locale } from "@/lib/seo";
import MriViewer from "./MriViewer";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(locale, "brain");
}

export default async function PortalRoutePage({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  return <PortalTopicPage locale={locale} pageKey="brain" extra={<MriViewer />} />;
}
