"use client";

// Provenance, made visible. Every fact the family reads carries a source.
// When the system has none, this does not go quiet — it says so plainly,
// in its own honest chip. That is the project's first principle made into
// a piece of UI.

import { useTranslations } from "next-intl";

export default function SourceTag({
  source,
  url,
}: {
  source: string | null;
  url?: string;
}) {
  const t = useTranslations("Common");

  if (!source) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-dashed border-line px-2.5 py-1 text-[0.72rem] font-medium text-faint">
        <span aria-hidden>◦</span>
        {t("noSource")}
      </span>
    );
  }

  const inner = (
    <>
      <span className="text-faint">{t("source")}</span>{" "}
      <span className="text-muted">{source}</span>
    </>
  );

  if (url) {
    return (
      <a
        href={url}
        target="_blank"
        rel="noreferrer"
        className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-line px-2.5 py-1 text-[0.72rem] transition-colors hover:border-accent-line hover:text-accent-ink"
      >
        <span className="truncate">{inner}</span>
      </a>
    );
  }

  return (
    <span className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-line px-2.5 py-1 text-[0.72rem]">
      <span className="truncate">{inner}</span>
    </span>
  );
}
