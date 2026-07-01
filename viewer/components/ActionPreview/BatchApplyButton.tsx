"use client";

import { useState } from "react";
import { Check, Loader2 } from "lucide-react";
import {
  postApplyActions,
  type ActionCardPayload,
  type ApplyActionsResponse,
} from "@/lib/brain/apply";

export default function BatchApplyButton({
  cards,
  disabled = false,
  onApplied,
}: {
  cards: ActionCardPayload[]
  disabled?: boolean
  onApplied?: (result: ApplyActionsResponse) => void
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function applyAll() {
    if (busy || disabled || cards.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      const result = await postApplyActions(cards);
      onApplied?.(result);
    } catch (err) {
      setError((err as Error).message.slice(0, 180));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <button
        type="button"
        onClick={applyAll}
        disabled={busy || disabled || cards.length === 0}
        className="inline-flex items-center gap-2 rounded-full bg-ink px-4 py-2 text-sm font-medium text-paper transition-colors hover:bg-accent-ink disabled:cursor-not-allowed disabled:bg-line disabled:text-faint"
      >
        {busy ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : (
          <Check className="h-4 w-4" aria-hidden="true" />
        )}
        {busy ? "Applying" : `Apply ${cards.length}`}
      </button>
      {error ? <p className="max-w-sm text-right text-xs text-urgent">{error}</p> : null}
    </div>
  );
}
