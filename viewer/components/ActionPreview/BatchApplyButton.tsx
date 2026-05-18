'use client'

// Phase 5 Day 4 — Apply-selected button. POSTs the selected ActionCards
// to /api/manager/apply which forwards to the Python worker that runs
// apply_batch.apply_many() inside a transaction.

import { useState } from 'react'

import type { ActionCardPayload } from '@/components/ActionPreview/ActionCard'
import { postApply } from '@/lib/brain/apply'

export interface BatchApplyButtonProps {
  cards: ActionCardPayload[]
  selectedIds: Set<string>
  onApplied?: (selectedIds: string[]) => void
  onError?: (msg: string) => void
}

export default function BatchApplyButton({
  cards,
  selectedIds,
  onApplied,
  onError,
}: BatchApplyButtonProps) {
  const [pending, setPending] = useState(false)
  const selected = cards.filter((c) => selectedIds.has(c.id))
  const disabled = pending || selected.length === 0

  async function handleClick() {
    setPending(true)
    try {
      await postApply(selected)
      onApplied?.(selected.map((c) => c.id))
    } catch (err) {
      onError?.((err as Error).message ?? 'apply failed')
    } finally {
      setPending(false)
    }
  }

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={handleClick}
      className={
        'inline-flex items-center justify-center h-8 px-3 text-xs font-medium rounded-md shadow-sm transition-colors '
        + (disabled
          ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
          : 'bg-slate-900 text-white hover:bg-slate-800')
      }
    >
      {pending ? 'Applying…' : `Apply ${selected.length} selected`}
    </button>
  )
}
