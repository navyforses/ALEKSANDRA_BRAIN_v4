'use client'

// Phase 5 Day 3 push-to-talk voice recorder.
//
// Trust boundary: the audio Blob is held only in browser memory. On stop,
// it is POSTed to /api/manager/voice and then dereferenced. The component
// state never serializes it to localStorage / IndexedDB.

import { useEffect, useRef, useState } from 'react'
import { useTranslations } from 'next-intl'

type Status = 'idle' | 'recording' | 'transcribing' | 'error'

export interface VoiceRecorderProps {
  onTranscript: (text: string, language: string, durationSec: number) => void
  onError?: (msg: string) => void
}

export default function VoiceRecorder({ onTranscript, onError }: VoiceRecorderProps) {
  const t = useTranslations('Manager')
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const [status, setStatus] = useState<Status>('idle')

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop())
    }
  }, [])

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const mimeType =
        MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : 'audio/webm'
      const rec = new MediaRecorder(stream, { mimeType })
      chunksRef.current = []
      rec.ondataavailable = (e: BlobEvent) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      rec.onstop = handleStop
      mediaRecorderRef.current = rec
      rec.start()
      setStatus('recording')
    } catch (err) {
      setStatus('error')
      onError?.((err as Error).message ?? 'microphone unavailable')
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop()
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
  }

  async function handleStop() {
    setStatus('transcribing')
    const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
    chunksRef.current = []
    const fd = new FormData()
    fd.append('audio', blob, 'clip.webm')
    try {
      const resp = await fetch('/api/manager/voice', { method: 'POST', body: fd })
      if (!resp.ok) {
        const text = await resp.text()
        throw new Error(`HTTP ${resp.status}: ${text.slice(0, 200)}`)
      }
      const data = (await resp.json()) as {
        text: string
        language: string
        duration_sec: number
      }
      onTranscript(data.text, data.language, data.duration_sec)
      setStatus('idle')
    } catch (err) {
      setStatus('error')
      onError?.((err as Error).message ?? 'transcription failed')
    }
  }

  const label =
    status === 'recording' ? t('voice.recording')
    : status === 'transcribing' ? t('voice.transcribing')
    : status === 'error' ? t('voice.retry')
    : t('voice.holdToTalk')

  return (
    <button
      type="button"
      onMouseDown={status === 'idle' || status === 'error' ? startRecording : undefined}
      onMouseUp={status === 'recording' ? stopRecording : undefined}
      onMouseLeave={status === 'recording' ? stopRecording : undefined}
      className={
        'inline-flex items-center justify-center h-8 px-3 text-xs font-medium '
        + 'rounded-md border border-slate-300 bg-white shadow-sm select-none transition-colors '
        + (status === 'recording'
          ? 'text-medical-red border-medical-red'
          : status === 'transcribing'
            ? 'text-slate-400 cursor-wait'
            : 'text-slate-700 hover:bg-slate-50')
      }
      aria-pressed={status === 'recording'}
    >
      <span
        className={
          'w-2 h-2 rounded-full mr-2 '
          + (status === 'recording' ? 'bg-medical-red animate-pulse' : 'bg-slate-300')
        }
      />
      {label}
    </button>
  )
}
