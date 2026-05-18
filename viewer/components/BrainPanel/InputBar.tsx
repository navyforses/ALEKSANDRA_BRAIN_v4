'use client'

// Phase 5 Day 3 BRAIN input bar: text + voice + attach.
//
// Wired into BrainPanel.tsx on Day 5 once the activity feed lands. For
// now the parent decides what to do with the typed text or transcript.

import { useState } from 'react'
import VoiceRecorder from '@/components/BrainPanel/VoiceRecorder'

export interface InputBarProps {
  onSubmit: (text: string, kind: 'text' | 'voice') => void
  onAttach?: (file: File) => void
  onError?: (msg: string) => void
}

export default function InputBar({ onSubmit, onAttach, onError }: InputBarProps) {
  const [text, setText] = useState('')

  function handleKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && text.trim()) {
      onSubmit(text.trim(), 'text')
      setText('')
    }
  }

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (f) onAttach?.(f)
    e.target.value = '' // allow re-selecting the same file
  }

  return (
    <div className="rounded-md border border-slate-300 bg-white shadow-sm flex items-center p-2 gap-2">
      <input
        type="text"
        placeholder="Ask BRAIN or drop file..."
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKey}
        className="flex-1 px-2 py-1 text-sm bg-transparent outline-none border-none placeholder:text-slate-400 text-slate-800"
      />

      <label className="inline-flex items-center justify-center h-8 px-3 text-xs font-medium rounded-md border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 cursor-pointer">
        Attach
        <input type="file" className="hidden" onChange={handleFile} />
      </label>

      <VoiceRecorder
        onTranscript={(t) => onSubmit(t, 'voice')}
        onError={onError}
      />
    </div>
  )
}
