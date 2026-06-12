"use client";

// viewer/app/[locale]/brain/MriViewerInner.tsx — Phase 11 inner client widget.
//
// Holds the actual @niivue/niivue (WebGL2) instantiation. The parent
// MriViewer.tsx dynamic-imports it with { ssr: false } so this WebGL code
// never runs on the server and lands in a code-split chunk (matches the
// Network.tsx / NetworkInner.tsx pattern used for vis-network).
//
// PRIVACY — project Rule #1 (MRI is client-side only): the volume is read
// ONLY in the browser via <input type="file"> / drag-drop + nv.loadFromFile().
// There is deliberately NO fetch / XHR / upload in this file — the bytes never
// leave the device. Keep it that way so scripts/check-no-remote-fetch.sh stays
// GREEN.

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

// Accept NIfTI single-file volumes only (.nii / .nii.gz). A bare *.gz is
// rejected — it is almost never a standalone NIfTI and would only fail at
// parse time. DICOM is a multi-file series and is out of scope for a single
// <input type="file"> picker.
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
  // React 19 StrictMode double-mounts effects in dev — each new Niivue() grabs
  // a WebGL2 context (browsers cap ~16), so cleanup() in the return is
  // mandatory. NOTE: the return closes over the LOCAL `nv`, not nvRef.current,
  // because at StrictMode teardown attachToCanvas().then() may not have
  // resolved yet (nvRef.current still null) — closing over `nv` guarantees the
  // exact instance this effect created is always disposed.
  useEffect(() => {
    let cancelled = false;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const nv = new Niivue({
      isResizeCanvas: true,
      backColor: [0, 0, 0, 1],
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

  // LOCAL file -> NiiVue. The parser is picked from the file name extension.
  // No object URL, no upload, no network — bytes stay in the browser.
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
      e.target.value = ""; // allow re-selecting the same file
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
      className="rounded border border-border bg-panel/15 p-6 md:p-8"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            {t("viewerLabel")}
          </p>
          <h2
            id="mri-viewer-heading"
            className="mt-1.5 text-xl font-bold text-foreground"
          >
            {t("title")}
          </h2>
        </div>
        <button
          type="button"
          disabled={!ready}
          onClick={() => {
            if (ready) inputRef.current?.click();
          }}
          className="inline-flex items-center justify-center rounded bg-primary px-4 py-2.5 text-xs font-semibold text-primary-foreground hover:bg-primary/95 focus:outline-none disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground cursor-pointer"
        >
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
        className={`relative mt-5 h-[480px] w-full overflow-hidden rounded border bg-[#050607] transition-colors duration-150 ${
          dragOver ? "border-medical-orange" : "border-border"
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
            <p className="max-w-md text-xs leading-5 text-muted-foreground">
              {t("dropMriHint")}
            </p>
          </div>
        ) : null}
      </div>

      <div className="mt-4 flex flex-col gap-2">
        <p
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="text-xs font-semibold text-foreground empty:hidden"
        >
          {fileName ? t("loadedFile", { name: fileName }) : ""}
        </p>
        {errKey ? (
          <p role="alert" className="text-xs font-semibold text-medical-red">
            {t(errKey)}
          </p>
        ) : null}
        <p className="text-xs leading-5 text-muted-foreground">{t("privacyNote")}</p>
      </div>
    </section>
  );
}
