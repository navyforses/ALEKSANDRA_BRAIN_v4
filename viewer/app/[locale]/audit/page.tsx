import { buildPageMetadata, type Locale } from "@/lib/seo";
import type { Metadata } from "next";
import { setRequestLocale } from 'next-intl/server'
import AuditLogClient from './AuditLogClient'


export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(locale, "audit");
}

export default async function AuditLogPage({
  params,
}: {
  params: Promise<{ locale: 'en' | 'ka' }>
}) {
  const { locale } = await params
  setRequestLocale(locale)
  return <AuditLogClient />
}
