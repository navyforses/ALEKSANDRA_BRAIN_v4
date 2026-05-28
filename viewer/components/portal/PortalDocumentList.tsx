"use client";

import { useEffect, useId, useState } from "react";
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

function splitBody(body?: string) {
  if (!body?.trim()) return [];
  return body
    .split(/\s+—\s+|\n{2,}/g)
    .map((part) => part.trim())
    .filter(Boolean);
}

export function PortalDocumentList({ items, locale }: { items: ReaderItem[]; locale: Locale }) {
  const [selected, setSelected] = useState<ReaderItem | null>(null);
  const titleId = useId();
  const paragraphs = splitBody(selected?.body);

  useEffect(() => {
    if (!selected) return;

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
        {items.map((item, index) => (
          <button
            key={`${item.source}-${item.title}-${index}`}
            type="button"
            onClick={() => setSelected(item)}
            aria-label={`${openLabel(locale)}: ${item.title}`}
            className="group flex min-h-24 w-full items-center justify-between gap-4 rounded-3xl border border-white/10 bg-white/[0.045] p-5 text-left shadow-2xl shadow-slate-950/20 transition duration-200 hover:-translate-y-0.5 hover:border-sky-200/40 hover:bg-white/[0.075] focus:outline-none focus:ring-2 focus:ring-sky-300/70"
          >
            <h3 className="text-lg font-black leading-snug text-white md:text-xl">{item.title}</h3>
            <span aria-hidden="true" className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-white/10 bg-sky-300/10 text-xl font-black text-sky-100 transition group-hover:bg-sky-300 group-hover:text-slate-950">
              →
            </span>
          </button>
        ))}
      </div>

      {selected ? (
        <div
          className="portal-reader-backdrop fixed inset-0 z-[90] overflow-y-auto bg-slate-950/80 px-4 py-8 backdrop-blur-md md:py-12"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setSelected(null);
          }}
        >
          <article
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            className="portal-a4-sheet relative mx-auto min-h-[min(1123px,calc(100vh-4rem))] w-full max-w-[794px] rounded-[1.25rem] bg-slate-50 px-7 py-8 text-slate-950 shadow-[0_40px_120px_rgba(0,0,0,0.45)] md:px-14 md:py-12"
          >
            <button
              type="button"
              onClick={() => setSelected(null)}
              className="absolute right-5 top-5 rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-black uppercase tracking-[0.16em] text-slate-700 shadow-sm transition hover:border-slate-400 hover:text-slate-950 focus:outline-none focus:ring-2 focus:ring-sky-500"
            >
              {closeLabel(locale)}
            </button>

            <header className="border-b border-slate-200 pb-7 pr-24">
              <p className="text-xs font-black uppercase tracking-[0.28em] text-sky-700">ALEKSANDRA BRAIN</p>
              <h1 id={titleId} className="mt-5 text-3xl font-black leading-tight tracking-tight text-slate-950 md:text-5xl">
                {selected.title}
              </h1>
              {selected.meta ? <p className="mt-4 inline-flex rounded-full bg-slate-200 px-3 py-1 text-xs font-bold text-slate-700">{selected.meta}</p> : null}
            </header>

            <div className="portal-document-body mt-8 text-[1.02rem] leading-8 text-slate-800 md:text-lg md:leading-9">
              {paragraphs.length ? paragraphs.map((paragraph, index) => <p key={`${paragraph.slice(0, 32)}-${index}`}>{paragraph}</p>) : <p className="font-semibold text-slate-500">{noData(locale)}</p>}
            </div>

            <footer className="mt-12 border-t border-slate-200 pt-5 text-xs font-black uppercase tracking-[0.18em] text-slate-500">
              {sourceLabel(locale)}: {selected.url ? <a href={selected.url} target="_blank" rel="noreferrer" className="text-sky-700 underline decoration-dotted underline-offset-4">{selected.source}</a> : selected.source}
            </footer>
          </article>
        </div>
      ) : null}
    </>
  );
}
