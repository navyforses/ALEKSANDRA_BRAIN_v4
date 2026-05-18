'use client'

// Phase 5 Day 5 — single-action undo button.
//
// Subtle gray styling (per DESIGN.md: never red — undo is not a panic
// action, it's a normal reversal that should feel safe).

import { useState } from 'react'

import { postUndo } from '@/lib/brain/undo'

export interface UndoButtonProps {
  actionId: string
  disabled?: boolean
  onUndone?: () => void
  onError?: (msg: string) => void
}

export default function UndoButton({
  actionId,
  disabled,
  onUndone,
  onError,
}: UndoButtonProps) {
  const [pending, setPending] = useState(false)
  const isDisabled = disabled || pending

  async function handle() {
    setPending(true)
    try {
      await postUndo(actionId)
      onUndone?.()
    } catch (err) {
      onError?.((err as Error).message)
    } finally {
      setPending(false)
    }
  }

  return (
    <button
      type="button"
      disabled={isDisabled}
      onClick={handle}
      className={
        'inline-flex items-center justify-center h-7 px-2.5 text-[11px] font-medium rounded-md border shadow-sm transition-colors '
        + (isDisabled
          ? 'bg-slate-100 border-slate-200 text-slate-400 cursor-not-allowed'
          : 'bg-white border-slate-300 text-slate-600 hover:bg-slate-50')
      }
    >
      {pending ? 'Undoing…' : 'Undo'}
    </button>
  )
}
