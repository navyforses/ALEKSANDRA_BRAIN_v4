import { setRequestLocale } from 'next-intl/server'
import AuditLogClient from './AuditLogClient'

export default async function AuditLogPage({
  params,
}: {
  params: Promise<{ locale: 'en' | 'ka' }>
}) {
  const { locale } = await params
  setRequestLocale(locale)
  return <AuditLogClient />
}
