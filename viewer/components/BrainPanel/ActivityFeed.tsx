'use client'

// Phase 5 Day 5 — BRAIN panel activity feed.
//
// Polls /api/manager/audit every 4s (Day 5 ships polling; swap to true
// Supabase realtime when the Postgres Changes integration is wired
// — see lib/realtime.ts).

import { useTranslations } from 'next-intl'
import { useManagerActivity, type ManagerActionRow } from '@/lib/realtime'

type ManagerT = ReturnType<typeof useTranslations<'Manager'>>

function summarize(row: ManagerActionRow, t: ManagerT): string {
  if (row.action_type === 'reverse') return t('summarize.undidAction', { id: String(row.target_record_id ?? '').slice(0, 8) })
  if (row.action_type === 'add_event') {
    const ap = row.after_payload as Record<string, unknown> | null
    return t('summarize.addedAppointment', { title: String(ap?.title ?? 'event'), date: String(ap?.event_date ?? '?') })
  }
  if (row.action_type === 'add_milestone') {
    const ap = row.after_payload as Record<string, unknown> | null
    return t('summarize.logged', { title: String(ap?.title ?? 'observation') })
  }
  if (row.action_type === 'create' && row.target_table === 'therapies') {
    const ap = row.after_payload as Record<string, unknown> | null
    return t('summarize.newTherapy', { name: String(ap?.name ?? '?') })
  }
  if (row.action_type === 'update' && row.target_table === 'therapies') {
    return t('summarize.appendedNote')
  }
  if (row.action_type === 'dismiss') return t('summarize.dismissed')
  if (row.action_type === 'log_pattern') {
    const ap = row.after_payload as Record<string, unknown> | null
    return t('summarize.pattern', { description: String(ap?.description ?? '(no description)') })
  }
  return t('summarize.fallback', { action: row.action_type, table: row.target_table })
}

function relativeTime(iso: string | null, t: ManagerT): string {
  if (!iso) return ''
  const ms = Date.now() - new Date(iso).getTime()
  if (ms < 60_000) return t('relativeTime.justNow')
  if (ms < 3_600_000) return t('relativeTime.minutesAgo', { n: Math.floor(ms / 60_000) })
  if (ms < 86_400_000) return t('relativeTime.hoursAgo', { n: Math.floor(ms / 3_600_000) })
  return new Date(iso).toLocaleDateString()
}

export default function ActivityFeed() {
  const t = useTranslations('Manager')
  const { rows, error } = useManagerActivity({ intervalMs: 4000, limit: 15 })

  if (error) {
    return (
      <div className="text-xs text-medical-red px-3 py-2 border border-medical-red/30 rounded-md bg-medical-red/10">
        {t('activityUnreachable', { error })}
      </div>
    )
  }
  if (rows.length === 0) {
    return (
      <div className="text-xs text-slate-400 italic text-center py-4">
        {t('noActivity')}
      </div>
    )
  }
  return (
    <ul className="space-y-2">
      {rows.map((row) => (
        <li
          key={row.id}
          className={
            'bg-white border rounded-md p-2.5 shadow-sm text-xs leading-snug '
            + (row.reversed_at
              ? 'border-slate-200 text-slate-400 line-through'
              : 'border-slate-200 text-slate-700')
          }
        >
          <div className="flex items-baseline justify-between gap-2">
            <span className="truncate">{summarize(row, t)}</span>
            <span className="font-mono text-[10px] text-slate-400 whitespace-nowrap">
              {relativeTime(row.created_at, t)}
            </span>
          </div>
        </li>
      ))}
    </ul>
  )
}
