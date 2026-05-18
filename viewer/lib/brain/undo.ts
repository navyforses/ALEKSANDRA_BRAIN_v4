// Phase 5 Day 5 — typed POST helper for /api/manager/undo/[id].

export interface UndoResponse {
  reverse_action_id: string
  original_action_id: string
  target_table: string
  target_action_taken: 'deleted_row' | 'restored_row' | 'audit_only'
}

export async function postUndo(actionId: string): Promise<UndoResponse> {
  const resp = await fetch('/api/manager/undo/' + encodeURIComponent(actionId), {
    method: 'POST',
  })
  if (!resp.ok) {
    const text = await resp.text().catch(() => '')
    throw new Error(
      `POST /api/manager/undo/${actionId} HTTP ${resp.status}: ${text.slice(0, 200)}`,
    )
  }
  return (await resp.json()) as UndoResponse
}
