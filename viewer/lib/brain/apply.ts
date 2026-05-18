// Phase 5 Day 4 — typed POST helper for /api/manager/apply.

import type { ActionCardPayload } from '@/components/ActionPreview/ActionCard'

export interface ApplyResponse {
  committed: boolean
  results: Array<{
    manager_action_id: string
    target_record_id: string
    action_type: string
    target_table: string
  }>
  error?: string
}

export async function postApply(cards: ActionCardPayload[]): Promise<ApplyResponse> {
  const resp = await fetch('/api/manager/apply', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ cards }),
  })
  if (!resp.ok) {
    const text = await resp.text().catch(() => '')
    throw new Error(`POST /api/manager/apply HTTP ${resp.status}: ${text.slice(0, 200)}`)
  }
  return (await resp.json()) as ApplyResponse
}
