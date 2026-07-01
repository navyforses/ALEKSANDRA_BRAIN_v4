// Phase 5 Day 4 — typed POST helper for /api/manager/apply.

export interface ActionFieldDiff {
  field: string
  before: unknown
  after: unknown
  changed: boolean
}

export interface ActionCardPayload {
  id: string
  summary: string
  action_type: string
  target_table: string
  target_record_id?: string | null
  source_entity_kind?: string | null
  confidence: number
  confidence_band: 'high' | 'medium' | 'low' | string
  auto_execute: boolean
  rationale: string
  diff: ActionFieldDiff[]
  warnings: string[]
  intake_drop_id?: string | null
  _before_payload?: Record<string, unknown> | null
  _after_payload?: Record<string, unknown>
}

export interface ApplyActionsResponse {
  committed?: boolean
  error?: string | null
  results?: unknown[]
  [key: string]: unknown
}

export async function postApplyActions(
  cards: ActionCardPayload[],
): Promise<ApplyActionsResponse> {
  const resp = await fetch('/api/manager/apply', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ cards }),
  })
  if (!resp.ok) {
    const text = await resp.text().catch(() => '')
    throw new Error(
      `POST /api/manager/apply HTTP ${resp.status}: ${text.slice(0, 200)}`,
    )
  }
  return (await resp.json()) as ApplyActionsResponse
}
