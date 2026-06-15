"use client";

// Silently refreshes the page every 90 s so newly ingested evidence_ledger
// rows appear without a manual reload. Pauses when the document is hidden
// (tab in background) to avoid wasteful server requests.

import { useEffect, useRef } from "react";
import { useRouter } from "@/i18n/navigation";

const INTERVAL_MS = 90_000;

export default function LiveRefresher() {
  const router = useRouter();
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  function start() {
    if (timer.current) return;
    timer.current = setInterval(() => {
      if (!document.hidden) {
        router.refresh();
      }
    }, INTERVAL_MS);
  }

  function stop() {
    if (timer.current) {
      clearInterval(timer.current);
      timer.current = null;
    }
  }

  useEffect(() => {
    start();

    function onVisibility() {
      if (document.hidden) {
        stop();
      } else {
        start();
      }
    }

    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      stop();
      document.removeEventListener("visibilitychange", onVisibility);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Renders nothing — pure side-effect.
  return null;
}
