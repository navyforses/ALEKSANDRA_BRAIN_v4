"use client";

// The intake console — one place that takes everything.
//
// You type or speak a request; you may attach a file. On send, BRAIN's
// worker (draft_from_intent) reads the request and, when it recognises an
// outreach ("write to Dr. Hien about the EEG"), stages a Gmail draft —
// never sent automatically. Shako reviews and sends it himself, and the
// whole exchange is recorded (outreach_log) and visible on History.
//
// Honesty rules this surface (CLAUDE.md "do not fabricate"):
//   - We show the worker's real verdict — staged / blocked / no match —
//     never an invented "3 actions proposed".
//   - Attached files stay in the browser. Medical files never reach a
//     server; the privacy note says so because it is true by design.

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import {
  IconArrowUp,
  IconAttach,
  IconClose,
  IconHistory,
  IconLock,
} from "@/components/shell/icons";
import VoiceButton from "@/components/intake/VoiceButton";

interface DraftResult {
  matched: boolean;
  blocked: boolean;
  block_reason: string | null;
  contact_name: string | null;
  draft: {
    subject: string | null;
    body_excerpt: string | null;
    gmail_draft_id: string | null;
  } | null;
}

type Outcome =
  | { kind: "staged"; contact: string; subject: string; excerpt: string }
  | { kind: "blocked"; reason: string }
  | { kind: "nomatch" }
  | { kind: "workerDown" }
  | { kind: "error"; message: string };

export default function IntakeConsole({ onClose }: { onClose?: () => void }) {
  const t = useTranslations("Intake");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  // Auto-grow the field so a long dictated note stays fully visible.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`;
  }, [text]);

  function appendTranscript(transcript: string) {
    setNotice(null);
    setText((prev) => (prev ? `${prev} ${transcript}` : transcript));
    textareaRef.current?.focus();
  }

  async function send() {
    const payload = text.trim();
    if (!payload || busy) return;
    setBusy(true);
    setOutcome(null);
    try {
      const resp = await fetch("/api/manager/email", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ text: payload }),
      });
      if (resp.status === 503) {
        setOutcome({ kind: "workerDown" });
        return;
      }
      if (!resp.ok) {
        const body = await resp.text().catch(() => "");
        setOutcome({ kind: "error", message: `HTTP ${resp.status}: ${body.slice(0, 140)}` });
        return;
      }
      const data = (await resp.json()) as DraftResult;
      if (data.draft && !data.blocked) {
        setOutcome({
          kind: "staged",
          contact: data.contact_name ?? t("contactFallback"),
          subject: data.draft.subject ?? "",
          excerpt: data.draft.body_excerpt ?? "",
        });
        setText("");
      } else if (data.blocked) {
        setOutcome({ kind: "blocked", reason: data.block_reason ?? "unknown" });
      } else {
        setOutcome({ kind: "nomatch" });
      }
    } catch (err) {
      setOutcome({ kind: "error", message: (err as Error).message });
    } finally {
      setBusy(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-serif text-xl text-ink">{t("title")}</h2>
          <p className="mt-1 text-sm leading-relaxed text-muted">{t("subtitle")}</p>
        </div>
        {onClose ? (
          <button
            type="button"
            onClick={onClose}
            aria-label={t("close")}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-muted transition-colors hover:bg-accent-soft hover:text-accent-ink"
          >
            <IconClose />
          </button>
        ) : null}
      </div>

      <div className="rounded-lg border border-line bg-paper/60 focus-within:border-accent-line">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          rows={3}
          placeholder={t("placeholder")}
          className="w-full resize-none bg-transparent px-4 py-3.5 text-[0.95rem] leading-relaxed text-ink placeholder:text-faint focus:outline-none"
        />

        {file ? (
          <div className="mx-4 mb-3 flex items-center gap-2 rounded-md border border-line bg-surface px-3 py-2 text-xs text-muted">
            <IconAttach className="h-4 w-4 text-faint" />
            <span className="truncate">{file.name}</span>
            <button
              type="button"
              onClick={() => setFile(null)}
              aria-label={t("removeAttach")}
              className="ml-auto text-faint hover:text-ink"
            >
              <IconClose className="h-4 w-4" />
            </button>
          </div>
        ) : null}

        <div className="flex flex-wrap items-center gap-2 border-t border-line px-3 py-2.5">
          <label className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-line px-3 py-2 text-sm text-muted transition-colors hover:text-ink">
            <IconAttach className="h-4 w-4" />
            <span className="hidden sm:inline">{t("attach")}</span>
            <input
              type="file"
              accept=".pdf,image/*,.txt,.eml,.doc,.docx"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) {
                  setFile(f);
                  setNotice(t("fileNote"));
                }
                e.target.value = "";
              }}
            />
          </label>

          <VoiceButton
            onTranscript={appendTranscript}
            onError={(m) => setNotice(m)}
          />

          <button
            type="button"
            onClick={send}
            disabled={busy || !text.trim()}
            className={`ml-auto inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
              busy || !text.trim()
                ? "cursor-not-allowed bg-line text-faint"
                : "bg-ink text-paper hover:bg-accent-ink"
            }`}
          >
            <IconArrowUp className="h-4 w-4" />
            {busy ? t("sending") : t("send")}
          </button>
        </div>
      </div>

      {notice ? (
        <p className="text-xs leading-relaxed text-muted">{notice}</p>
      ) : null}

      {outcome ? <OutcomeCard outcome={outcome} /> : null}

      <div className="mt-1 flex items-center justify-between gap-3 border-t border-line pt-3">
        <p className="flex items-start gap-1.5 text-xs leading-relaxed text-faint">
          <IconLock className="mt-px h-3.5 w-3.5 shrink-0" />
          {t("privacy")}
        </p>
        <Link
          href="/history"
          onClick={onClose}
          className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-muted hover:text-accent-ink"
        >
          <IconHistory className="h-3.5 w-3.5" />
          {t("seeHistory")}
        </Link>
      </div>
    </div>
  );
}

function OutcomeCard({ outcome }: { outcome: Outcome }) {
  const t = useTranslations("Intake");

  if (outcome.kind === "staged") {
    return (
      <div className="u-fade rounded-lg border border-signal-line bg-signal-soft px-4 py-3.5">
        <p className="text-sm font-medium text-signal">
          {t("stagedTitle", { contact: outcome.contact })}
        </p>
        {outcome.subject ? (
          <p className="mt-1.5 font-serif text-[0.95rem] text-ink">{outcome.subject}</p>
        ) : null}
        {outcome.excerpt ? (
          <p className="mt-1 line-clamp-3 text-xs leading-relaxed text-muted">
            {outcome.excerpt}
          </p>
        ) : null}
        <p className="mt-2 text-xs text-muted">{t("openGmail")}</p>
      </div>
    );
  }

  const tone =
    outcome.kind === "error"
      ? "border-urgent/40 bg-urgent-soft text-urgent"
      : "border-accent-line bg-accent-soft text-accent-ink";

  const body =
    outcome.kind === "blocked"
      ? t("blockedHint", { reason: outcome.reason })
      : outcome.kind === "nomatch"
        ? t("noMatchHint")
        : outcome.kind === "workerDown"
          ? t("workerDownHint")
          : outcome.message;

  const heading =
    outcome.kind === "blocked"
      ? t("blockedTitle")
      : outcome.kind === "nomatch"
        ? t("noMatchTitle")
        : outcome.kind === "workerDown"
          ? t("workerDownTitle")
          : t("errorTitle");

  return (
    <div className={`u-fade rounded-lg border px-4 py-3.5 ${tone}`}>
      <p className="text-sm font-medium">{heading}</p>
      <p className="mt-1 text-xs leading-relaxed opacity-90">{body}</p>
    </div>
  );
}
