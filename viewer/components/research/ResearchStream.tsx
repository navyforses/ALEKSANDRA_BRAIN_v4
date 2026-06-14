"use client";

// One stream, three lenses. Papers, hypotheses, and therapy candidates
// used to be three separate pages; here they share a single calm column,
// filterable by kind and searchable, each item carrying its provenance.
// Tapping any item opens a reading sheet with the full text.

import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import KindBadge from "@/components/KindBadge";
import Reader from "@/components/research/Reader";
import SourceTag from "@/components/SourceTag";
import type { ResearchItem, ResearchKind } from "@/lib/data";

type Lens = "all" | ResearchKind;

// How many items fill one page of the stream. A short page keeps the column
// readable and stops the list from running the full height of the document;
// the numbered switcher below grows automatically as more papers land.
const PAGE_SIZE = 5;

// Page numbers to render, windowed around the current page with ellipses so a
// large corpus shows e.g. "1 … 7 8 9 … 24" instead of every number. -1 marks
// an ellipsis gap (never a clickable page).
function buildPages(current: number, total: number): number[] {
  const delta = 1;
  const range: number[] = [];
  for (let i = Math.max(1, current - delta); i <= Math.min(total, current + delta); i++) {
    range.push(i);
  }
  if (range[0] > 1) {
    if (range[0] > 2) range.unshift(-1);
    range.unshift(1);
  }
  if (range[range.length - 1] < total) {
    if (range[range.length - 1] < total - 1) range.push(-1);
    range.push(total);
  }
  return range;
}

export default function ResearchStream({
  items,
  updatedLabel,
}: {
  items: ResearchItem[];
  updatedLabel?: string;
}) {
  const t = useTranslations("Research");
  const [lens, setLens] = useState<Lens>("all");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<ResearchItem | null>(null);
  const [page, setPage] = useState(1);
  const listTopRef = useRef<HTMLDivElement | null>(null);

  const counts = useMemo(
    () => ({
      all: items.length,
      paper: items.filter((i) => i.kind === "paper").length,
      hypothesis: items.filter((i) => i.kind === "hypothesis").length,
      therapy: items.filter((i) => i.kind === "therapy").length,
    }),
    [items],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((item) => {
      if (lens !== "all" && item.kind !== lens) return false;
      if (!q) return true;
      return (
        item.title.toLowerCase().includes(q) ||
        item.summary.toLowerCase().includes(q) ||
        item.detail.toLowerCase().includes(q) ||
        (item.source ?? "").toLowerCase().includes(q)
      );
    });
  }, [items, lens, query]);

  // Reset to the first page whenever the filter or search changes — otherwise a
  // narrower result could strand the reader on a now-empty page.
  useEffect(() => {
    setPage(1);
  }, [lens, query]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pageCount);
  const start = (current - 1) * PAGE_SIZE;
  const pageItems = filtered.slice(start, start + PAGE_SIZE);

  function goToPage(p: number) {
    const next = Math.min(Math.max(1, p), pageCount);
    setPage(next);
    // Bring the top of the list back into view so a new page starts at its head,
    // not wherever the previous page's scroll happened to leave us.
    listTopRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const lenses: { key: Lens; label: string; count: number }[] = [
    { key: "all", label: t("lens.all"), count: counts.all },
    { key: "paper", label: t("lens.papers"), count: counts.paper },
    { key: "hypothesis", label: t("lens.hypotheses"), count: counts.hypothesis },
    { key: "therapy", label: t("lens.therapies"), count: counts.therapy },
  ];

  return (
    <div>
      {/* Lenses + search */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-1.5" role="tablist" aria-label={t("lensLabel")}>
          {lenses.map((l) => {
            const active = lens === l.key;
            return (
              <button
                key={l.key}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => setLens(l.key)}
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm transition-colors ${
                  active ? "bg-ink text-paper" : "border border-line text-muted hover:text-ink"
                }`}
              >
                {l.label}
                <span className={active ? "text-paper/70" : "text-faint"}>{l.count}</span>
              </button>
            );
          })}
        </div>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("searchPlaceholder")}
          className="w-full rounded-full border border-line bg-surface px-4 py-2 text-sm text-ink placeholder:text-faint focus:border-accent-line focus:outline-none sm:max-w-xs"
        />
      </div>

      {updatedLabel ? (
        <p className="mt-4 text-xs text-faint">{t("updated", { time: updatedLabel })}</p>
      ) : null}

      {/* Scroll anchor: paging brings the head of the list back into view. */}
      <div ref={listTopRef} className="scroll-mt-24" />

      {/* Stream */}
      {filtered.length === 0 ? (
        <div className="mt-6 rounded-xl border border-line bg-surface px-5 py-10 text-center">
          <p className="text-sm text-muted">{items.length === 0 ? t("empty") : t("noMatch")}</p>
        </div>
      ) : (
        <>
          <ul className="mt-6 space-y-3">
            {pageItems.map((item) => (
              <li key={`${item.kind}-${item.id}`}>
                <button
                  type="button"
                  onClick={() => setSelected(item)}
                  className="card group block w-full p-5 text-left transition-colors hover:border-accent-line"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <KindBadge kind={item.kind} />
                    {item.meta.slice(0, 3).map((m, i) => (
                      <span
                        key={i}
                        className="rounded-full bg-paper px-2 py-0.5 text-[0.72rem] text-muted"
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                  <h3 className="mt-3 font-serif text-lg leading-snug text-ink group-hover:text-accent-ink">
                    {item.title}
                  </h3>
                  {item.summary ? (
                    <p className="mt-1.5 line-clamp-2 text-sm leading-relaxed text-muted">
                      {item.summary}
                    </p>
                  ) : null}
                  <div className="mt-3.5">
                    <SourceTag source={item.source} url={item.url} />
                  </div>
                </button>
              </li>
            ))}
          </ul>

          {pageCount > 1 ? (
            <nav aria-label={t("pagination.label")} className="mt-8 flex flex-col items-center gap-3">
              <p className="text-xs text-faint">
                {t("pagination.showing", {
                  from: start + 1,
                  to: start + pageItems.length,
                  total: filtered.length,
                })}
              </p>
              <div className="flex flex-wrap items-center justify-center gap-1.5">
                <button
                  type="button"
                  onClick={() => goToPage(current - 1)}
                  disabled={current === 1}
                  aria-label={t("pagination.prev")}
                  className="inline-flex h-9 min-w-9 items-center justify-center rounded-full border border-line px-3 text-sm text-muted transition-colors hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
                >
                  ‹
                </button>
                {buildPages(current, pageCount).map((p, i) =>
                  p === -1 ? (
                    <span key={`gap-${i}`} className="px-1.5 text-faint" aria-hidden="true">
                      …
                    </span>
                  ) : (
                    <button
                      key={p}
                      type="button"
                      onClick={() => goToPage(p)}
                      aria-current={p === current ? "page" : undefined}
                      aria-label={
                        p === current
                          ? t("pagination.current", { n: p })
                          : t("pagination.page", { n: p })
                      }
                      className={`inline-flex h-9 min-w-9 items-center justify-center rounded-full px-3 text-sm transition-colors ${
                        p === current
                          ? "bg-ink text-paper"
                          : "border border-line text-muted hover:text-ink"
                      }`}
                    >
                      {p}
                    </button>
                  ),
                )}
                <button
                  type="button"
                  onClick={() => goToPage(current + 1)}
                  disabled={current === pageCount}
                  aria-label={t("pagination.next")}
                  className="inline-flex h-9 min-w-9 items-center justify-center rounded-full border border-line px-3 text-sm text-muted transition-colors hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
                >
                  ›
                </button>
              </div>
            </nav>
          ) : null}
        </>
      )}

      {selected ? (
        <Reader item={selected} onClose={() => setSelected(null)} />
      ) : null}
    </div>
  );
}
