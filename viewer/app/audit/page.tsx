'use client'

// Phase 5 Day 5 — full audit history page.

import ActionRow from '@/components/AuditLog/ActionRow'
import { useManagerActivity } from '@/lib/realtime'

export default function AuditLogPage() {
  const { rows, error, refresh } = useManagerActivity({ intervalMs: 6000, limit: 100 })

  return (
    <div className="flex flex-col h-full space-y-4">
      <header className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
          Audit log
        </h1>
        <p className="mt-2 text-sm text-slate-500">
          Every BRAIN-applied action, newest first. Undo works for the last
          {' '}<span className="font-mono">30</span> actions within{' '}
          <span className="font-mono">24h</span>.
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
              <th className="px-3 py-2 text-left font-medium">When</th>
              <th className="px-3 py-2 text-left font-medium">Action</th>
              <th className="px-3 py-2 text-left font-medium">Target</th>
              <th className="px-3 py-2 text-left font-medium">Source</th>
              <th className="px-3 py-2 text-right font-medium">&nbsp;</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-xs text-slate-400 italic">
                  No actions yet.
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
