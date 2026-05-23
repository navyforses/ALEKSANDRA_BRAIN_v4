'use client'

// Phase 5 Day 6 — operator types "write to X about Y", BRAIN stages a
// Gmail draft via /api/manager/email. NEVER auto-sent: Gmail compose
// scope only; Shako reviews + clicks Send in Gmail UI.

import { useState } from 'react'
import { useTranslations } from 'next-intl'

interface DraftSummary {
  contact_name: string | null
  subject: string | null
  gmail_draft_id: string | null
  body_excerpt: string | null
  confidence: number | null
}

interface ApiResponse {
  matched: boolean
  blocked: boolean
  block_reason: string | null
  contact_id: string | null
  contact_name: string | null
  fuzzy_score: number | null
  draft: DraftSummary | null
}

type Status = 'idle' | 'pending' | 'staged' | 'blocked' | 'error'

export default function EmailIntent() {
  const t = useTranslations('Manager')
  const [text, setText] = useState('')
  const [status, setStatus] = useState<Status>('idle')
  const [result, setResult] = useState<ApiResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!text.trim()) return
    setStatus('pending')
    setError(null)
    try {
      const resp = await fetch('/api/manager/email', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ text: text.trim() }),
      })
      if (!resp.ok) {
        const errText = await resp.text().catch(() => '')
        throw new Error(`HTTP ${resp.status}: ${errText.slice(0, 200)}`)
      }
      const data = (await resp.json()) as ApiResponse
      setResult(data)
      setStatus(data.blocked ? 'blocked' : 'staged')
      if (!data.blocked) setText('')
    } catch (err) {
      setError((err as Error).message)
      setStatus('error')
    }
  }

  return (
    <div className="space-y-2">
      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={t('email.writeToPlaceholder')}
          className="flex-1 px-2 py-1 text-sm bg-white border border-slate-300 rounded-md outline-none placeholder:text-slate-400 text-slate-800"
          disabled={status === 'pending'}
        />
        <button
          type="submit"
          disabled={status === 'pending' || !text.trim()}
          className={
            'inline-flex items-center justify-center h-8 px-3 text-xs font-medium rounded-md shadow-sm transition-colors '
            + (status === 'pending' || !text.trim()
              ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
              : 'bg-slate-900 text-white hover:bg-slate-800')
          }
        >
          {status === 'pending' ? t('email.drafting') : t('email.draftEmail')}
        </button>
      </form>

      {status === 'staged' && result?.draft && (
        <div className="border border-medical-green/30 bg-medical-green/10 rounded-md px-3 py-2 text-xs text-slate-700">
          <div className="font-medium text-medical-green">
            {t('email.draftStaged', { contact: result.contact_name ?? t('email.contactFallback') })}
          </div>
          <div className="mt-1 text-slate-600">
            <span className="font-mono text-[11px]">{result.draft.subject}</span>
          </div>
          <div className="mt-1 text-[11px] text-slate-500">
            {t('email.openGmailNote')}
          </div>
        </div>
      )}

      {status === 'blocked' && result && (
        <div className="border border-medical-orange/30 bg-medical-orange/10 rounded-md px-3 py-2 text-xs text-medical-orange">
          {t('email.draftBlocked', { reason: result.block_reason ?? 'unknown' })}
        </div>
      )}

      {status === 'error' && error && (
        <div className="border border-medical-red/30 bg-medical-red/10 rounded-md px-3 py-2 text-xs text-medical-red">
          {error}
        </div>
      )}
    </div>
  )
}
