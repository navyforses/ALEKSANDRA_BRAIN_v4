'use client'

// Phase 5 Day 5 — one row per manager_actions item on the audit log page.

import type { ManagerActionRow } from '@/lib/realtime'
import UndoButton from '@/components/AuditLog/UndoButton'

const UNDO_WINDOW_HOURS = 24

function isUndoable(row: ManagerActionRow): boolean {
  if (row.reversed_at) return false
  if (row.action_type === 'reverse' || row.action_type === 'dismiss') return false
  if (!row.created_at) return false
  const ageMs = Date.now() - new Date(row.created_at).getTime()
  return ageMs < UNDO_WINDOW_HOURS * 3_600_000
}

function shortSummary(row: ManagerActionRow): string {
  const ap = row.after_payload as Record<string, unknown> | null
  if (row.action_type === 'add_event') return `Appointment: ${String(ap?.title ?? '?')}`
  if (row.action_type === 'add_milestone') return `Observation: ${String(ap?.title ?? '?')}`
  if (row.action_type === 'create' && row.target_table === 'therapies')
    return `New therapy: ${String(ap?.name ?? '?')}`
  if (row.action_type === 'update' && row.target_table === 'therapies')
    return `Therapy note appended`
  if (row.action_type === 'add_contact') return `Contact: ${String(ap?.full_name ?? '?')}`
  if (row.action_type === 'reverse') return `↺ Reversed action ${String(row.target_record_id ?? '').slice(0, 8)}…`
  if (row.action_type === 'dismiss') return 'Dismissed intake drop'
  if (row.action_type === 'log_pattern')
    return `Pattern: ${String(ap?.description ?? '')}`
  return `${row.action_type} on ${row.target_table}`
}

export interface ActionRowProps {
  row: ManagerActionRow
  onUndone?: () => void
}

export default function ActionRow({ row, onUndone }: ActionRowProps) {
  const reversed = !!row.reversed_at
  return (
    <tr
      className={
        'border-b border-slate-200 hover:bg-slate-50 '
        + (reversed ? 'opacity-60' : '')
      }
    >
      <td className="px-3 py-2 font-mono text-[11px] text-slate-500 whitespace-nowrap">
        {row.created_at ? new Date(row.created_at).toLocaleString() : '—'}
      </td>
      <td className="px-3 py-2 text-xs">
        <span
          className={
            reversed
              ? 'line-through text-slate-400'
              : 'text-slate-800'
          }
        >
          {shortSummary(row)}
        </span>
      </td>
      <td className="px-3 py-2 text-[11px] font-mono text-slate-500 whitespace-nowrap">
        {row.target_table}
      </td>
      <td className="px-3 py-2 text-[11px] font-mono text-slate-500 whitespace-nowrap">
        {row.source_input ?? '—'}
      </td>
      <td className="px-3 py-2 text-right whitespace-nowrap">
        {reversed ? (
          <span className="text-[11px] font-mono text-slate-400">reversed</span>
        ) : isUndoable(row) ? (
          <UndoButton actionId={row.id} onUndone={onUndone} />
        ) : (
          <span className="text-[11px] font-mono text-slate-400">—</span>
        )}
      </td>
    </tr>
  )
}
