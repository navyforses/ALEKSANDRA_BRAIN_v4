// Phase 5 Day 3 voice client helper.
//
// Frontend-only fetch wrapper. The route handler at
// viewer/app/api/manager/voice/route.ts forwards the audio to a Python
// worker that calls OpenAI Whisper, then returns the redacted text.

export interface VoiceTranscriptResponse {
  text: string
  language: string
  duration_sec: number
  redactions_count: number
}

export async function postVoice(blob: Blob, filename = 'clip.webm'): Promise<VoiceTranscriptResponse> {
  const fd = new FormData()
  fd.append('audio', blob, filename)
  const resp = await fetch('/api/manager/voice', { method: 'POST', body: fd })
  if (!resp.ok) {
    const text = await resp.text().catch(() => '')
    throw new Error(`POST /api/manager/voice HTTP ${resp.status}: ${text.slice(0, 200)}`)
  }
  return (await resp.json()) as VoiceTranscriptResponse
}
