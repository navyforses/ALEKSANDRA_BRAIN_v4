"use client";

// The actual @niivue/niivue (WebGL2) instantiation. The parent
// MriViewer.tsx dynamic-imports it with { ssr: false } so this WebGL code
// never runs on the server and lands in a code-split chunk.
//
// PRIVACY — project Rule #1 (MRI is client-side only): the volume is read
// ONLY in the browser via <input type="file"> / drag-drop + nv.loadFromFile().
// There is deliberately NO fetch / XHR / upload in this file — the bytes
// never leave the device. Keep it that way so check-no-remote-fetch.sh
// stays GREEN.

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
} from "react";
import { Niivue } from "@niivue/niivue";
import { useTranslations } from "next-intl";
import { IconAttach } from "@/components/shell/icons";

// Accept NIfTI single-file volumes only (.nii / .nii.gz). DICOM is a
// multi-file series and is out of scope for a single file picker.
const ACCEPTED = /\.nii(\.gz)?$/i;

type ErrKey = "openError" | "webglError";

export default function MriViewerInner() {
  const t = useTranslations("Brain");
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const nvRef = useRef<Niivue | null>(null);
  const [ready, setReady] = useState(false);
  const [errKey, setErrKey] = useState<ErrKey | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  // Instantiate + attach NiiVue once on the client; tear down on unmount.
  // React 19 StrictMode double-mounts effects in dev — each new Niivue()
  // grabs a WebGL2 context (browsers cap ~16), so cleanup() is mandatory.
  // The return closes over the LOCAL `nv` (not nvRef.current) because at
  // StrictMode teardown attachToCanvas().then() may not have resolved yet.
  useEffect(() => {
    let cancelled = false;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const nv = new Niivue({
      isResizeCanvas: true,
      backColor: [0.02, 0.02, 0.02, 1],
      show3Dcrosshair: true,
    });

    nv.attachToCanvas(canvas)
      .then(() => {
        if (cancelled) return;
        nvRef.current = nv;
        setReady(true);
      })
      .catch(() => {
        if (!cancelled) setErrKey("webglError");
      });

    return () => {
      cancelled = true;
      try {
        nv.cleanup();
      } catch {
        /* already disposed */
      }
      nvRef.current = null;
      setReady(false);
    };
  }, []);

  // LOCAL file -> NiiVue. No object URL, no upload, no network.
  const loadFile = useCallback((file: File) => {
    const nv = nvRef.current;
    if (!nv) return;
    if (!ACCEPTED.test(file.name)) {
      setErrKey("openError");
      return;
    }
    setErrKey(null);
    nv.loadFromFile(file)
      .then(() => setFileName(file.name))
      .catch(() => setErrKey("openError"));
  }, []);

  const onInput = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) loadFile(file);
      e.target.value = "";
    },
    [loadFile],
  );

  const onDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files?.[0];
      if (file) loadFile(file);
    },
    [loadFile],
  );

  return (
    <section
      aria-labelledby="mri-viewer-heading"
      className="card overflow-hidden"
    >
      <div className="flex flex-col gap-3 border-b border-line p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-faint">
            {t("viewerLabel")}
          </p>
          <h2 id="mri-viewer-heading" className="mt-1 font-serif text-lg text-ink">
            {t("title")}
          </h2>
        </div>
        <button
          type="button"
          disabled={!ready}
          onClick={() => {
            if (ready) inputRef.current?.click();
          }}
          className="inline-flex items-center justify-center gap-2 rounded-full bg-ink px-4 py-2.5 text-sm font-medium text-paper transition-colors hover:bg-accent-ink disabled:cursor-not-allowed disabled:bg-line disabled:text-faint"
        >
          <IconAttach className="h-4 w-4" />
          {t("loadFile")}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".nii,.nii.gz"
          className="hidden"
          tabIndex={-1}
          aria-hidden="true"
          onChange={onInput}
        />
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`relative m-5 h-[460px] overflow-hidden rounded-lg border bg-[#050505] transition-colors ${
          dragOver ? "border-accent" : "border-line"
        }`}
      >
        <canvas
          ref={canvasRef}
          className="h-full w-full"
          role={fileName ? "application" : "img"}
          aria-label={fileName ? t("canvasLoaded", { name: fileName }) : t("canvasEmpty")}
          aria-describedby="mri-canvas-desc"
        />
        <p id="mri-canvas-desc" className="sr-only">
          {t("canvasControlsHint")}
        </p>
        {!fileName ? (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center p-6 text-center">
            <p className="max-w-md text-sm leading-relaxed text-white/55">{t("dropMriHint")}</p>
          </div>
        ) : null}
      </div>

      <div className="flex flex-col gap-2 px-5 pb-5">
        <p
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="text-sm font-medium text-ink empty:hidden"
        >
          {fileName ? t("loadedFile", { name: fileName }) : ""}
        </p>
        {errKey ? (
          <p role="alert" className="text-sm font-medium text-urgent">
            {t(errKey)}
          </p>
        ) : null}
        <p className="text-xs leading-relaxed text-faint">{t("privacyNote")}</p>
      </div>
    </section>
  );
}
