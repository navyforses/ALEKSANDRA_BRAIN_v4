// Phase 5 Day 5 — undo route handler.
//
// Forwards to the Python worker's /undo-action endpoint which runs
// scripts.manager.activity.undo.undo() inside a transaction. The
// server holds the operator id from env so the browser cannot lie
// about it.

import { NextRequest, NextResponse } from 'next/server'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const DEFAULT_MANAGER_USER_ID = 'shako-jincharadze'

export async function POST(
  _req: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params
  if (!id || id.length < 8) {
    return NextResponse.json(
      { error: 'invalid_action_id' },
      { status: 400 },
    )
  }

  const workerUrl =
    process.env.PHASE5_MANAGER_WORKER_URL?.trim()
    ?? process.env.PHASE5_VOICE_WORKER_URL?.trim()
  if (!workerUrl) {
    return NextResponse.json(
      {
        error: 'manager_worker_not_deployed',
        message:
          'PHASE5_MANAGER_WORKER_URL not set. Deploy the Python manager worker.',
      },
      { status: 503 },
    )
  }

  const manager = process.env.MANAGER_USER_ID?.trim() || DEFAULT_MANAGER_USER_ID
  const headers: Record<string, string> = { 'content-type': 'application/json' }
  const token = process.env.PHASE5_WORKER_AUTH_TOKEN?.trim()
  if (token) headers['X-Auth-Token'] = token

  let resp: Response
  try {
    // Server-side forward to the Python worker; runtime:'nodejs'.
    const target = workerUrl.replace(/\/$/, '') + '/undo-action'
    resp = await fetch(target, /* allow-remote */ {
      method: 'POST',
      headers,
      body: JSON.stringify({ manager_action_id: id, manager_user_id: manager }),
    })
  } catch (err) {
    return NextResponse.json(
      { error: 'worker_unreachable', message: (err as Error).message },
      { status: 502 },
    )
  }
  const body = await resp.text()
  return new NextResponse(body, {
    status: resp.status,
    headers: {
      'content-type': resp.headers.get('content-type') ?? 'application/json',
    },
  })
}
