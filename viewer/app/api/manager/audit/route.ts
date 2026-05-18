// Phase 5 Day 5 — server-side audit feed.
//
// Queries manager_actions directly via Supabase REST (service-role key
// stays on the server). Returns the most recent rows for the configured
// MANAGER_USER_ID. Matches the read pattern in viewer/lib/supabase.ts.

import { NextRequest, NextResponse } from 'next/server'

import { getRows } from '@/lib/supabase'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const DEFAULT_MANAGER_USER_ID = 'shako-jincharadze'

export async function GET(req: NextRequest) {
  const url = new URL(req.url)
  const limit = Math.min(
    Math.max(parseInt(url.searchParams.get('limit') || '25', 10), 1),
    100,
  )
  const manager = process.env.MANAGER_USER_ID?.trim() || DEFAULT_MANAGER_USER_ID

  const select =
    'id,action_type,target_table,target_record_id,before_payload,'
    + 'after_payload,source_input,intake_drop_id,approved_at,'
    + 'reversed_at,reversed_by,created_at'

  const result = await getRows('manager_actions', {
    select,
    manager_user_id: `eq.${manager}`,
    order: 'created_at.desc',
    limit,
  })

  if (!result.configured) {
    return NextResponse.json(
      { error: 'supabase_not_configured', rows: [] },
      { status: 503 },
    )
  }
  if (result.error) {
    return NextResponse.json(
      { error: result.error, rows: [] },
      { status: 502 },
    )
  }
  return NextResponse.json({ rows: result.rows })
}
