'use client'

// Phase 5 Day 4 — one card per ProposedAction.
//
// Carries:
//   - summary line + confidence band + auto/preview chip
//   - per-field diff rendered by FieldDiff
//   - warnings (medication-dose change, etc.)
//   - a single checkbox controlled by the parent

import FieldDiff, { type FieldDiffRow } from '@/components/ActionPreview/FieldDiff'

export interface ActionCardPayload {
  id: string
  summary: string
  action_type: string
  target_table: string
  source_entity_kind: string
  confidence: number
  confidence_band: 'high' | 'medium' | 'low'
  auto_execute: boolean
  rationale: string
  diff: FieldDiffRow[]
  warnings: string[]
}

export interface ActionCardProps {
  card: ActionCardPayload
  selected: boolean
  onToggle: (id: string) => void
}

const BAND_STYLES: Record<ActionCardPayload['confidence_band'], string> = {
  high: 'text-medical-green border-medical-green/30 bg-medical-green/10',
  medium: 'text-medical-orange border-medical-orange/30 bg-medical-orange/10',
  low: 'text-slate-500 border-slate-300 bg-slate-100',
}

export default function ActionCard({ card, selected, onToggle }: ActionCardProps) {
  return (
    <div className="border border-slate-200 rounded-md bg-white p-3 shadow-sm">
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={selected}
          onChange={() => onToggle(card.id)}
          className="mt-1 h-4 w-4 rounded border-slate-300 text-medical-purple"
          aria-label={`select action ${card.summary}`}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap">
            <h3 className="text-sm font-medium text-slate-900 truncate">{card.summary}</h3>
            <span
              className={`text-[10px] font-mono uppercase border rounded px-1.5 py-0.5 ${BAND_STYLES[card.confidence_band]}`}
              title={`confidence ${card.confidence.toFixed(2)}`}
            >
              {card.confidence_band}
            </span>
            {card.auto_execute ? (
              <span className="text-[10px] font-mono uppercase border border-medical-green/30 rounded px-1.5 py-0.5 text-medical-green bg-medical-green/10">
                auto-ok
              </span>
            ) : (
              <span className="text-[10px] font-mono uppercase border border-slate-300 rounded px-1.5 py-0.5 text-slate-500 bg-slate-100">
                preview
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-slate-500">{card.rationale}</p>

          {card.warnings.length > 0 && (
            <ul className="mt-2 space-y-0.5 text-xs text-medical-red">
              {card.warnings.map((w, i) => (
                <li key={i}>⚠ {w}</li>
              ))}
            </ul>
          )}

          <div className="mt-2 space-y-1">
            {card.diff.filter((r) => r.changed).map((r) => (
              <FieldDiff key={r.field} row={r} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
