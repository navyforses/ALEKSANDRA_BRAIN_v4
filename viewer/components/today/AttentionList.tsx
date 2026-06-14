"use client";

// The home "what needs you" list. Each card opens the same reading sheet as the
// research stream (these were previously static, non-clickable cards — the
// family tapped them and nothing happened).

import { useState } from "react";
import { Link } from "@/i18n/navigation";
import KindBadge from "@/components/KindBadge";
import Reader from "@/components/research/Reader";
import SourceTag from "@/components/SourceTag";
import type { ResearchItem } from "@/lib/data";

export default function AttentionList({
  items,
  seeAllLabel,
}: {
  items: ResearchItem[];
  seeAllLabel: string;
}) {
  const [selected, setSelected] = useState<ResearchItem | null>(null);

  return (
    <>
      <ul className="mt-4 space-y-3">
        {items.map((item) => (
          <li key={`${item.kind}-${item.id}`}>
            <button
              type="button"
              onClick={() => setSelected(item)}
              className="card group block w-full p-5 text-left transition-colors hover:border-accent-line"
            >
              <div className="flex flex-wrap items-center gap-2">
                <KindBadge kind={item.kind} />
              </div>
              <h3 className="mt-3 font-serif text-lg leading-snug text-ink group-hover:text-accent-ink">
                {item.title}
              </h3>
              {item.implication || item.summary ? (
                <p className="mt-1.5 line-clamp-3 text-sm leading-relaxed text-muted">
                  {item.implication || item.summary}
                </p>
              ) : null}
              <div className="mt-3.5">
                <SourceTag source={item.source} url={item.url} />
              </div>
            </button>
          </li>
        ))}
        <li className="pt-1">
          <Link
            href="/research"
            className="text-sm font-medium text-accent-ink hover:underline"
          >
            {seeAllLabel} →
          </Link>
        </li>
      </ul>

      {selected ? <Reader item={selected} onClose={() => setSelected(null)} /> : null}
    </>
  );
}
