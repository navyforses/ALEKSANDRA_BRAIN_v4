"use client";

// The reading sheet. Tapping any research card (in the research stream or the
// home "what needs you" list) opens this modal with the item's full text,
// implication, and provenance. Shared so both surfaces read identically.

import { useTranslations } from "next-intl";
import KindBadge from "@/components/KindBadge";
import SourceTag from "@/components/SourceTag";
import { IconClose } from "@/components/shell/icons";
import type { ResearchItem } from "@/lib/data";

export default function Reader({
  item,
  onClose,
}: {
  item: ResearchItem;
  onClose: () => void;
}) {
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
