"use client";

// Push-to-talk dictation.
//
// Trust boundary (unchanged from the original VoiceRecorder): the audio
// Blob lives only in browser memory. On stop it is POSTed to
// /api/manager/voice (which forwards to the Python Whisper worker where
// the API key and the PHI redactor co-locate) and then dereferenced. It
// is never written to localStorage / IndexedDB / disk by this component.

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { IconMic, IconStop } from "@/components/shell/icons";

type Status = "idle" | "recording" | "transcribing" | "error";

export default function VoiceButton({
  onTranscript,
  onError,
}: {
  onTranscript: (text: string) => void;
  onError?: (msg: string) => void;
}) {
  const t = useTranslations("Intake");
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const [status, setStatus] = useState<Status>("idle");

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((tr) => tr.stop());
    };
  }, []);

  async function start() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const rec = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];
      rec.ondataavailable = (e: BlobEvent) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      rec.onstop = handleStop;
      recorderRef.current = rec;
      rec.start();
      setStatus("recording");
    } catch (err) {
      setStatus("error");
      onError?.((err as Error).message ?? "microphone unavailable");
    }
  }

  function stop() {
    recorderRef.current?.stop();
    streamRef.current?.getTracks().forEach((tr) => tr.stop());
    streamRef.current = null;
  }

  async function handleStop() {
    setStatus("transcribing");
    const blob = new Blob(chunksRef.current, { type: "audio/webm" });
    chunksRef.current = [];
    const fd = new FormData();
    fd.append("audio", blob, "clip.webm");
    try {
      const resp = await fetch("/api/manager/voice", { method: "POST", body: fd });
      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(`HTTP ${resp.status}: ${text.slice(0, 160)}`);
      }
      const data = (await resp.json()) as { text: string };
      if (data.text?.trim()) onTranscript(data.text.trim());
      setStatus("idle");
    } catch (err) {
      setStatus("error");
      onError?.((err as Error).message ?? "transcription failed");
    }
  }

  const recording = status === "recording";
  const label =
    status === "recording"
      ? t("voiceRecording")
      : status === "transcribing"
        ? t("voiceTranscribing")
        : status === "error"
          ? t("voiceRetry")
          : t("voiceHold");

  return (
    <button
      type="button"
      onMouseDown={status === "idle" || status === "error" ? start : undefined}
      onMouseUp={recording ? stop : undefined}
      onMouseLeave={recording ? stop : undefined}
      onTouchStart={(e) => {
        if (status === "idle" || status === "error") {
          e.preventDefault();
          start();
        }
      }}
      onTouchEnd={(e) => {
        if (recording) {
          e.preventDefault();
          stop();
        }
      }}
      aria-pressed={recording}
      aria-label={label}
      title={label}
      disabled={status === "transcribing"}
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm transition-colors select-none ${
        recording
          ? "border-urgent text-urgent"
          : status === "transcribing"
            ? "cursor-wait border-line text-faint"
            : "border-line text-muted hover:text-ink"
      }`}
    >
      {recording ? (
        <IconStop className="h-4 w-4" />
      ) : (
        <IconMic className="h-4 w-4" />
      )}
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}
