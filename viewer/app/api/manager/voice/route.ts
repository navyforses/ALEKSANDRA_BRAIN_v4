// Phase 5 Day 3 voice transcription route handler.
//
// Trust boundary: this route forwards the audio bytes to the Python
// worker (PHASE5_VOICE_WORKER_URL). It NEVER reads OPENAI_API_KEY from
// the Edge/Node env directly — the Whisper call lives in the Python
// process where the API key and the PHI redactor co-locate. The audio
// blob is never written to disk by this handler.
//
// Configuration:
//   PHASE5_VOICE_WORKER_URL — e.g. https://aleksandra-worker.up.railway.app
//   PHASE5_WORKER_AUTH_TOKEN — Bearer token expected by the Python worker
//
// If PHASE5_VOICE_WORKER_URL is not set, the route returns HTTP 503 with
// a clear "voice worker not deployed" body so the BRAIN panel can show
// a friendly message instead of a silent hang. Same fallback pattern as
// workflows/weekly_brief.json's render node.

import { NextRequest, NextResponse } from 'next/server'

export const runtime = 'nodejs' // file uploads need the Node runtime, not Edge
export const dynamic = 'force-dynamic'

export async function POST(req: NextRequest) {
  const workerUrl = process.env.PHASE5_VOICE_WORKER_URL?.trim()
  if (!workerUrl) {
    return NextResponse.json(
      {
        error: 'voice_worker_not_deployed',
        message:
          'PHASE5_VOICE_WORKER_URL not set. Deploy the Python voice worker before using voice input.',
      },
      { status: 503 },
    )
  }

  const form = await req.formData()
  const audio = form.get('audio')
  // FormData.get returns string | File | null in standard DOM lib; the
  // Node runtime uses the same shape via undici. We treat anything with
  // both `.arrayBuffer()` and `.type` as a Blob/File.
  if (
    audio === null ||
    typeof audio === 'string' ||
    typeof (audio as Blob).arrayBuffer !== 'function'
  ) {
    return NextResponse.json(
      { error: 'audio_missing', message: 'Multipart field "audio" is required.' },
      { status: 400 },
    )
  }

  const audioBlob = audio as Blob & { name?: string }
  const forwardForm = new FormData()
  forwardForm.append('audio', audioBlob, audioBlob.name ?? 'clip.webm')

  const headers: Record<string, string> = {}
  const token = process.env.PHASE5_WORKER_AUTH_TOKEN?.trim()
  if (token) headers['X-Auth-Token'] = token

  let resp: Response
  try {
    // Server-side forward to the Python Whisper worker. Runs in the
    // Node runtime (runtime='nodejs' above), never executes in the
    // browser, so PHI/MRI exfiltration via this line is impossible.
    resp = await fetch(`${workerUrl.replace(/\/$/, '')}/voice-transcribe`, /* allow-remote */ {
      method: 'POST',
      headers,
      body: forwardForm,
    })
  } catch (err) {
    return NextResponse.json(
      {
        error: 'voice_worker_unreachable',
        message: (err as Error).message,
      },
      { status: 502 },
    )
  }

  const body = await resp.text()
  return new NextResponse(body, {
    status: resp.status,
    headers: { 'content-type': resp.headers.get('content-type') ?? 'application/json' },
  })
}
