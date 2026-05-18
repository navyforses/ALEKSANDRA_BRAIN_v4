// Phase 5 Day 6 — email-intent route handler.
//
// Forwards "write to X about Y" to the Python worker's /email-intent
// endpoint which runs scripts.manager.email_draft.draft_from_intent.
// Server-side fetch only; runtime:'nodejs'; FND-02 allow-remote marker
// on the outgoing call.

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
          'PHASE5_MANAGER_WORKER_URL not set. Deploy the Python manager worker.',
      },
      { status: 503 },
    )
  }

  let payload: { text?: string; dry_run?: boolean }
  try {
    payload = await req.json()
  } catch {
    return NextResponse.json(
      { error: 'bad_json', message: 'Request body must be JSON.' },
      { status: 400 },
    )
  }
  if (!payload.text || !payload.text.trim()) {
    return NextResponse.json(
      { error: 'text_missing', message: 'Field "text" is required.' },
      { status: 400 },
    )
  }

  const headers: Record<string, string> = { 'content-type': 'application/json' }
  const token = process.env.PHASE5_WORKER_AUTH_TOKEN?.trim()
  if (token) headers['X-Auth-Token'] = token

  let resp: Response
  try {
    const target = workerUrl.replace(/\/$/, '') + '/email-intent'
    resp = await fetch(target, /* allow-remote */ {
      method: 'POST',
      headers,
      body: JSON.stringify({
        text: payload.text.trim(),
        dry_run: !!payload.dry_run,
      }),
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
