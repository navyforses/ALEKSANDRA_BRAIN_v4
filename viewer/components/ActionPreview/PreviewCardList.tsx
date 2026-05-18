'use client'

// Phase 5 Day 4 — stacked list of ActionCards + Apply-all button.

import { useMemo, useState } from 'react'

import ActionCard, { type ActionCardPayload } from '@/components/ActionPreview/ActionCard'
import BatchApplyButton from '@/components/ActionPreview/BatchApplyButton'

export interface PreviewCardListProps {
  cards: ActionCardPayload[]
  onApplied?: (selectedIds: string[]) => void
  onError?: (msg: string) => void
}

export default function PreviewCardList({ cards, onApplied, onError }: PreviewCardListProps) {
  // By default everything auto-eligible is checked. Operator can uncheck.
  const initial = useMemo(
    () => new Set(cards.filter((c) => c.auto_execute).map((c) => c.id)),
    [cards],
  )
  const [selected, setSelected] = useState<Set<string>>(initial)

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  if (cards.length === 0) {
    return (
      <p className="text-xs text-slate-500 italic">No actions proposed for this drop.</p>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-500">
          {cards.length} proposed action{cards.length === 1 ? '' : 's'} —{' '}
          <button
            type="button"
            className="underline hover:text-slate-700"
            onClick={() => setSelected(new Set(cards.map((c) => c.id)))}
          >
            select all
          </button>{' '}
          ·{' '}
          <button
            type="button"
            className="underline hover:text-slate-700"
            onClick={() => setSelected(new Set())}
          >
            clear
          </button>
        </p>
        <BatchApplyButton
          cards={cards}
          selectedIds={selected}
          onApplied={onApplied}
          onError={onError}
        />
      </div>
      <div className="space-y-2">
        {cards.map((card) => (
          <ActionCard
            key={card.id}
            card={card}
            selected={selected.has(card.id)}
            onToggle={toggle}
          />
        ))}
      </div>
    </div>
  )
}
