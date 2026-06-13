"use client";

// One stream, three lenses. Papers, hypotheses, and therapy candidates
// used to be three separate pages; here they share a single calm column,
// filterable by kind and searchable, each item carrying its provenance.
// Tapping any item opens a reading sheet with the full text.

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import KindBadge from "@/components/KindBadge";
import SourceTag from "@/components/SourceTag";
import { IconClose } from "@/components/shell/icons";
import type { ResearchItem, ResearchKind } from "@/lib/data";

type Lens = "all" | ResearchKind;

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

      {/* Stream */}
      {filtered.length === 0 ? (
        <div className="mt-6 rounded-xl border border-line bg-surface px-5 py-10 text-center">
          <p className="text-sm text-muted">{items.length === 0 ? t("empty") : t("noMatch")}</p>
        </div>
      ) : (
        <ul className="mt-6 space-y-3">
          {filtered.map((item) => (
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
      )}

      {selected ? (
        <Reader item={selected} onClose={() => setSelected(null)} />
      ) : null}
    </div>
  );
}

function Reader({ item, onClose }: { item: ResearchItem; onClose: () => void }) {
  const t = useTranslations("Research");
  const paragraphs = (item.detail || item.summary).split(/\n{2,}/).filter(Boolean);

  return (
    <div
      className="reader-backdrop no-print"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <article role="dialog" aria-modal="true" aria-label={item.title} className="reader-sheet u-rise">
        <button
          type="button"
          onClick={onClose}
          aria-label={t("close")}
          className="absolute right-4 top-4 grid h-9 w-9 place-items-center rounded-full text-muted transition-colors hover:bg-accent-soft hover:text-accent-ink"
        >
          <IconClose />
        </button>

        <div className="flex flex-wrap items-center gap-2 pr-12">
          <KindBadge kind={item.kind} />
          {item.meta.map((m, i) => (
            <span key={i} className="rounded-full bg-paper px-2 py-0.5 text-[0.72rem] text-muted">
              {m}
            </span>
          ))}
        </div>

        <h2 className="mt-4 font-serif text-2xl leading-tight text-ink">{item.title}</h2>

        <div className="mt-5 space-y-3.5">
          {paragraphs.length > 0 ? (
            paragraphs.map((p, i) => (
              <p key={i} className="text-[0.95rem] leading-relaxed text-ink/90">
                {p}
              </p>
            ))
          ) : (
            <p className="text-sm text-muted">{t("noDetail")}</p>
          )}
        </div>

        {item.implication ? (
          <div className="mt-6 rounded-lg border border-accent-line bg-accent-soft p-4">
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-accent-ink">
              {t("implication")}
            </p>
            <p className="mt-2 text-[0.95rem] leading-relaxed text-ink">{item.implication}</p>
          </div>
        ) : null}

        <div className="mt-6 border-t border-line pt-4">
          <SourceTag source={item.source} url={item.url} />
        </div>
      </article>
    </div>
  );
}
