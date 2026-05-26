"use client";

// viewer/components/research/TwinImpactFilter.tsx — Phase 7.6 widget.
//
// Toggle that sorts the Research Pulse list by "twin-impact" — KL
// divergence between current posterior and the projected posterior after
// ingesting the paper. In MOCK_MODE the sort key is approximated from the
// paper's relevance_score; live mode reads from the belief API. Emits a
// callback so the host page can re-render its list.

import { useState } from "react";
import { useTranslations } from "next-intl";

interface Props {
  defaultEnabled?: boolean;
  onChange?: (enabled: boolean) => void;
}

export default function TwinImpactFilter({
  defaultEnabled = false,
  onChange,
}: Props) {
  const t = useTranslations("TwinImpactFilter");
  const [enabled, setEnabled] = useState<boolean>(defaultEnabled);

  function handleToggle() {
    const next = !enabled;
    setEnabled(next);
    onChange?.(next);
  }

  return (
    <section className="flex flex-col gap-2 rounded-md border border-stone-200 bg-white p-3">
      <header className="flex items-baseline justify-between">
        <h3 className="text-xs font-semibold text-stone-800">{t("title")}</h3>
        <span className="font-mono text-[10px] text-stone-400">KL · v7.6</span>
      </header>
      <p className="text-[11px] leading-5 text-stone-600">{t("description")}</p>
      <label className="flex items-center gap-2 text-xs text-stone-700">
        <input
          type="checkbox"
          checked={enabled}
          onChange={handleToggle}
          className="h-4 w-4 rounded border-stone-300"
        />
        <span>{enabled ? t("sortByKl") : t("sortByRelevance")}</span>
      </label>
    </section>
  );
}
