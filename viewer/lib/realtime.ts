// Phase 5 Day 5 — manager_actions subscription wrapper.
//
// Day 5 ships a polling implementation (no @supabase/supabase-js dep,
// keeps the bundle small, matches the existing viewer REST pattern in
// viewer/lib/supabase.ts). The API surface is intentionally identical
// to a future @supabase/realtime swap — when Supabase realtime is
// adopted, only the subscribe() body changes.
//
// Trust: this client lives in the browser. It calls /api/manager/audit
// (server-side route handler) which adds the service-role key. The
// browser never sees the key.

'use client'

import { useEffect, useRef, useState } from 'react'

export interface ManagerActionRow {
  id: string
  action_type: string
  target_table: string
  target_record_id: string | null
  before_payload: unknown
  after_payload: unknown
  source_input: string | null
  intake_drop_id: string | null
  approved_at: string | null
  reversed_at: string | null
  reversed_by: string | null
  created_at: string | null
}

export interface UseManagerActivityOptions {
  /** Polling interval in ms. Default 4000. */
  intervalMs?: number
  /** Max rows to return per poll. Default 25. */
  limit?: number
  /** When true, skip the network calls (useful for tests). */
  disabled?: boolean
}

/**
 * React hook that polls /api/manager/audit and exposes the latest
 * manager_actions rows + a refresh() callback for immediate refetch
 * after the operator applies/dismisses/undoes something.
 */
export function useManagerActivity({
  intervalMs = 4000,
  limit = 25,
  disabled = false,
}: UseManagerActivityOptions = {}) {
  const [rows, setRows] = useState<ManagerActionRow[]>([])
  const [error, setError] = useState<string | null>(null)
  const cancelledRef = useRef(false)

  async function fetchOnce() {
    try {
      const resp = await fetch('/api/manager/audit?limit=' + String(limit), {
        cache: 'no-store',
      })
      if (!resp.ok) {
        setError(`HTTP ${resp.status}`)
        return
      }
      const data = (await resp.json()) as { rows: ManagerActionRow[] }
      if (!cancelledRef.current) {
        setRows(data.rows ?? [])
        setError(null)
      }
    } catch (err) {
      if (!cancelledRef.current) setError((err as Error).message)
    }
  }

  useEffect(() => {
    if (disabled) return
    cancelledRef.current = false
    fetchOnce()
    const handle = setInterval(fetchOnce, intervalMs)
    return () => {
      cancelledRef.current = true
      clearInterval(handle)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, limit, disabled])

  return { rows, error, refresh: fetchOnce }
}
