"use client";

import { useEffect, useMemo, useState } from "react";
import ActionCard from "@/components/ActionPreview/ActionCard";
import BatchApplyButton from "@/components/ActionPreview/BatchApplyButton";
import type { ActionCardPayload } from "@/lib/brain/apply";

export default function PreviewCardList({ cards }: { cards: ActionCardPayload[] }) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(
    () => new Set(cards.map((card) => card.id)),
  );

  useEffect(() => {
    setSelectedIds(new Set(cards.map((card) => card.id)));
  }, [cards]);

  const selectedCards = useMemo(
    () => cards.filter((card) => selectedIds.has(card.id)),
    [cards, selectedIds],
  );

  function setSelected(id: string, selected: boolean) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (selected) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  if (cards.length === 0) {
    return (
      <div className="rounded-lg border border-line bg-surface px-5 py-8 text-center">
        <p className="text-sm text-muted">No proposed actions.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted">
          {selectedCards.length} of {cards.length} selected
        </p>
        <BatchApplyButton cards={selectedCards} disabled={selectedCards.length === 0} />
      </div>

      <ul className="space-y-3">
        {cards.map((card) => (
          <li key={card.id}>
            <ActionCard
              card={card}
              selected={selectedIds.has(card.id)}
              onSelectedChange={(selected) => setSelected(card.id, selected)}
            />
          </li>
        ))}
      </ul>
    </div>
  );
}
