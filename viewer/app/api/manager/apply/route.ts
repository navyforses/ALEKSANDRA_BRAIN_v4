// Phase 5 Day 4 apply route — forwards approved ActionCards to the
// Python worker's /apply-actions endpoint, which calls
// scripts.manager.routing.apply_batch.apply_many inside a transaction.
//
// Same trust posture as /api/manager/voice: server-side fetch only,
// PHASE5_WORKER_URL gates deployment, and a fallback HTTP 503 fires
// when the worker isn't configured.

import { NextRequest, NextResponse } from 'next/server'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export async function POST(req: NextRequest) {
  const workerUrl =
    process.env.PHASE5_MANAGER_WORKER_URL?.trim()
    ?? process.env.PHASE5_VOICE_WORKER_URL?.trim()
  if (!workerUrl) {
    return NextResponse.json(
      {
        error: 'manager_worker_not_deployed',
        message:
          'PHASE5_MANAGER_WORKER_URL (or PHASE5_VOICE_WORKER_URL) not set. '
          + 'Deploy the Python manager worker before applying actions.',
      },
      { status: 503 },
    )
  }

  let payload: unknown
  try {
    payload = await req.json()
  } catch {
    return NextResponse.json(
      { error: 'bad_json', message: 'Request body must be JSON.' },
      { status: 400 },
    )
  }
  const cards = (payload as { cards?: unknown[] } | null)?.cards
  if (!Array.isArray(cards) || cards.length === 0) {
    return NextResponse.json(
      { error: 'cards_missing', message: 'Body must carry a non-empty cards[].' },
      { status: 400 },
    )
  }

  const headers: Record<string, string> = { 'content-type': 'application/json' }
  const token = process.env.PHASE5_WORKER_AUTH_TOKEN?.trim()
  if (token) headers['X-Auth-Token'] = token

  let resp: Response
  try {
    // Server-side forward to the Python worker. runtime:'nodejs', not
    // browser; PHI/MRI exfiltration impossible from this line.
    resp = await fetch(`${workerUrl.replace(/\/$/, '')}/apply-actions`, /* allow-remote */ {
      method: 'POST',
      headers,
      body: JSON.stringify({ cards }),
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
