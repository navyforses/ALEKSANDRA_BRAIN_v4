"use client";

import { useTranslations } from "next-intl";
import {
  IconHypothesis,
  IconPaper,
  IconTherapy,
} from "@/components/shell/icons";
import type { ResearchKind } from "@/lib/data";

const STYLES: Record<ResearchKind, { tint: string; Icon: typeof IconPaper }> = {
  paper: { tint: "border-accent-line bg-accent-soft text-accent-ink", Icon: IconPaper },
  hypothesis: { tint: "border-line bg-paper text-muted", Icon: IconHypothesis },
  therapy: { tint: "border-signal-line bg-signal-soft text-signal", Icon: IconTherapy },
};

export default function KindBadge({ kind }: { kind: ResearchKind }) {
  const t = useTranslations("Research");
  const { tint, Icon } = STYLES[kind];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[0.72rem] font-medium ${tint}`}
    >
      <Icon className="h-3.5 w-3.5" />
      {t(`kind.${kind}`)}
    </span>
  );
}
