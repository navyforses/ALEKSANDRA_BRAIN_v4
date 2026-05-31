"use client";

import { useEffect, useId, useRef, useState } from "react";
import type { Locale } from "@/lib/seo";

type ReaderItem = {
  title: string;
  body?: string;
  meta?: string;
  source: string;
  url?: string;
};

function noData(locale: Locale) {
  return locale === "ka" ? "მონაცემი არ არის" : "No data available";
}

function sourceLabel(locale: Locale) {
  return locale === "ka" ? "წყარო" : "Source";
}

function openLabel(locale: Locale) {
  return locale === "ka" ? "დოკუმენტის გახსნა" : "Open document";
}

function closeLabel(locale: Locale) {
  return locale === "ka" ? "დახურვა" : "Close";
}

function cleanInlineMarkdown(value: string) {
  return value
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^[-*•]\s+/gm, "")
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/__(.*?)__/g, "$1")
    .replace(/\[(.*?)\]\([^)]*\)/g, "$1")
    .replace(/[`*_~]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function shortTitle(value: string, fallback: string) {
  const raw = value.trim();
  if (!raw) return fallback;

  const heading = raw.match(/^\s*#{1,6}\s+(.+)$/m)?.[1];
  const firstLine = raw.split(/\r?\n/).map((line) => line.trim()).find(Boolean);
  const seed = cleanInlineMarkdown(heading || firstLine || raw);
  const sentence = seed.split(/\s+[—–-]\s+|(?<=[.!?…])\s+/u)[0]?.trim() || seed;
  const capped = sentence.length > 92 ? `${sentence.slice(0, 89).trim()}…` : sentence;
  return capped || fallback;
}

function documentView(item: ReaderItem, locale: Locale) {
  const fallback = item.source || noData(locale);
  const title = shortTitle(item.title, fallback);
  const rawBody = item.body?.trim();
  const cleanedTitle = cleanInlineMarkdown(item.title);
  const body = rawBody || (cleanedTitle && cleanedTitle !== title ? cleanedTitle : undefined);
  return { ...item, title, body };
}

const technicalMarkers = [
  /source_?hypothesis_?id/i,
  /target_?pathway/i,
  /created_?at/i,
  /validated_?at/i,
  /updated_?at/i,
  /pubmed_?signals/i,
  /has_?pediatric_?data/i,
  /recent_?year/i,
  /top_?meta/i,
  /best_?evidence_?paper_?id/i,
];

function articleParagraph(value: string) {
  const raw = value.trim();
  if (!raw) return "";

  const markerCount = technicalMarkers.filter((marker) => marker.test(raw)).length;
  const startsAsTechnicalDump = /^\s*(source_?hypothesis_?id|target_?pathway|created_?at|validated_?at|updated_?at|pubmed_?signals|top_?meta)\s*:/i.test(raw);
  if (startsAsTechnicalDump || markerCount >= 2) return "";

  const cleaned = cleanInlineMarkdown(raw);
  return cleaned.replace(/^dossier\s*:\s*/i, "").trim();
}

function splitBody(body?: string) {
  if (!body?.trim()) return [];
  return body
    .split(/\s+—\s+|\n{2,}/g)
    .map((part) => articleParagraph(part))
    .filter(Boolean);
}

export function PortalDocumentList({ items, locale }: { items: ReaderItem[]; locale: Locale }) {
  const [selected, setSelected] = useState<ReaderItem | null>(null);
  const titleId = useId();
  const sheetRef = useRef<HTMLElement | null>(null);
  const paragraphs = splitBody(selected?.body);

  useEffect(() => {
    if (!selected) return;

    window.requestAnimationFrame(() => {
      if (!sheetRef.current) return;
      sheetRef.current.scrollTop = 0;
      sheetRef.current.focus({ preventScroll: true });
    });

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSelected(null);
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [selected]);

  return (
    <>
      <div className="grid gap-3 lg:grid-cols-2">
        {items.map((item, index) => {
          const doc = documentView(item, locale);
          return (
            <button
              key={`${item.source}-${item.title}-${index}`}
              type="button"
              onClick={() => setSelected(doc)}
              aria-label={`${openLabel(locale)}: ${doc.title}`}
              className="group flex min-h-24 w-full items-center justify-between gap-4 rounded-3xl border border-white/10 bg-white/[0.045] p-5 text-left shadow-2xl shadow-slate-950/20 transition duration-200 hover:-translate-y-0.5 hover:border-sky-200/40 hover:bg-white/[0.075] focus:outline-none focus:ring-2 focus:ring-sky-300/70"
            >
              <h3 className="portal-card-title min-w-0 text-lg font-black leading-snug text-white md:text-xl">{doc.title}</h3>
              <span aria-hidden="true" className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-white/10 bg-sky-300/10 text-xl font-black text-sky-100 transition group-hover:bg-sky-300 group-hover:text-slate-950">
                →
              </span>
            </button>
          );
        })}
      </div>

      {selected ? (
        <div
          className="portal-reader-backdrop fixed inset-0 z-[90] grid place-items-center overflow-hidden bg-slate-950/80 px-3 py-4 backdrop-blur-md md:px-4 md:py-8"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setSelected(null);
          }}
        >
          <article
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            ref={sheetRef}
            tabIndex={-1}
            className="portal-a4-sheet relative mx-auto h-[min(1123px,calc(100dvh-2rem))] max-h-[calc(100dvh-2rem)] w-full max-w-[794px] overflow-y-auto overscroll-contain rounded-[1.25rem] bg-slate-50 px-7 py-8 text-slate-950 shadow-[0_40px_120px_rgba(0,0,0,0.45)] outline-none md:h-[min(1123px,calc(100dvh-4rem))] md:max-h-[calc(100dvh-4rem)] md:px-14 md:py-12"
          >
            <button
              type="button"
              onClick={() => setSelected(null)}
              className="sticky right-0 top-0 z-20 float-right rounded-full border border-slate-200 bg-white/95 px-4 py-2 text-xs font-black uppercase tracking-[0.16em] text-slate-700 shadow-sm backdrop-blur transition hover:border-slate-400 hover:text-slate-950 focus:outline-none focus:ring-2 focus:ring-sky-500"
            >
              {closeLabel(locale)}
            </button>

            <header className="portal-reader-header border-b border-slate-200 pb-7 pr-24">
              <p className="text-xs font-black uppercase tracking-[0.28em] text-sky-700">ALEKSANDRA BRAIN</p>
              <h1 id={titleId} className="mt-5 text-3xl font-black leading-tight tracking-tight text-slate-950 md:text-5xl">
                {selected.title}
              </h1>
              {selected.meta ? <p className="mt-4 inline-flex rounded-full bg-slate-200 px-3 py-1 text-xs font-bold text-slate-700">{selected.meta}</p> : null}
            </header>

            <div className="portal-document-body portal-reader-body mt-8 text-[1.02rem] leading-8 text-slate-800 md:text-lg md:leading-9">
              {paragraphs.length ? paragraphs.map((paragraph, index) => <p key={`${paragraph.slice(0, 32)}-${index}`}>{paragraph}</p>) : <p className="font-semibold text-slate-500">{noData(locale)}</p>}
            </div>

            <footer className="portal-reader-footer mt-12 border-t border-slate-200 pt-5 text-xs font-black uppercase tracking-[0.18em] text-slate-500">
              {sourceLabel(locale)}: {selected.url ? <a href={selected.url} target="_blank" rel="noreferrer" className="text-sky-700 underline decoration-dotted underline-offset-4">{selected.source}</a> : selected.source}
            </footer>
          </article>
        </div>
      ) : null}
    </>
  );
}
