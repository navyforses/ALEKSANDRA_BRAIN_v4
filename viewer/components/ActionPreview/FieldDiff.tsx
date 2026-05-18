// Phase 5 Day 4 — Linear-style before/after row for ActionCard.

import type { ReactNode } from 'react'

export interface FieldDiffRow {
  field: string
  before: unknown
  after: unknown
  changed: boolean
}

function fmt(value: unknown): ReactNode {
  if (value === null || value === undefined) return <span className="text-slate-400">—</span>
  if (typeof value === 'string') return value || <span className="text-slate-400">—</span>
  return <span>{JSON.stringify(value)}</span>
}

export default function FieldDiff({ row }: { row: FieldDiffRow }) {
  const accent = row.changed ? 'text-medical-orange' : 'text-slate-500'
  return (
    <div className="grid grid-cols-[120px_1fr_1fr] items-baseline gap-2 text-xs">
      <div className="font-mono text-slate-500">{row.field}</div>
      <div className="text-slate-500 line-through decoration-slate-300">{fmt(row.before)}</div>
      <div className={accent}>{fmt(row.after)}</div>
    </div>
  )
}
