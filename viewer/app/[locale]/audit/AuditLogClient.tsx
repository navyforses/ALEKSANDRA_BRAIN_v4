'use client'

import { useTranslations } from 'next-intl'
import ActionRow from '@/components/AuditLog/ActionRow'
import { useManagerActivity } from '@/lib/realtime'

export default function AuditLogClient() {
  const t = useTranslations('Audit')
  const { rows, error, refresh } = useManagerActivity({ intervalMs: 6000, limit: 100 })

  return (
    <div className="flex flex-col h-full space-y-4">
      <header className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          {t('title')}
        </h1>
        <p className="mt-2 text-sm text-slate-500">
          {t('subtitle', { undoLimit: 30, undoWindow: '24h' })}
        </p>
      </header>

      {error && (
        <div className="text-xs text-medical-red px-3 py-2 border border-medical-red/30 rounded-md bg-medical-red/10">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto border border-slate-200 rounded-md">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500 sticky top-0">
            <tr>
              <th className="px-3 py-2 text-left font-medium">{t('colWhen')}</th>
              <th className="px-3 py-2 text-left font-medium">{t('colAction')}</th>
              <th className="px-3 py-2 text-left font-medium">{t('colTarget')}</th>
              <th className="px-3 py-2 text-left font-medium">{t('colSource')}</th>
              <th className="px-3 py-2 text-right font-medium">&nbsp;</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-xs text-slate-400 italic">
                  {t('emptyState')}
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <ActionRow key={row.id} row={row} onUndone={refresh} />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
