"use client";

// The shared intake console, presented as a calm overlay. Mounted once by
// the shell; opened from anywhere via the intake context (header "+",
// Today's hero, or Cmd/Ctrl-K).

import { useEffect } from "react";
import type { Locale } from "@/lib/seo";
import { useIntake } from "@/components/shell/intake-context";
import IntakeConsole from "@/components/intake/IntakeConsole";

export default function IntakeOverlay({ locale }: { locale: Locale }) {
  const { open, setOpen } = useIntake();

  // Lock the page behind the console while it is open.
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="no-print fixed inset-0 z-50 grid place-items-start justify-center overflow-y-auto px-4 py-[max(1rem,8vh)]"
      style={{ backgroundColor: "color-mix(in srgb, var(--ink) 38%, transparent)", backdropFilter: "blur(3px)" }}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) setOpen(false);
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={locale === "ka" ? "შემოტანა" : "Intake"}
        className="u-rise w-full max-w-2xl rounded-lg border border-line bg-surface p-5 shadow-2xl sm:p-7"
      >
        <IntakeConsole onClose={() => setOpen(false)} />
      </div>
    </div>
  );
}
