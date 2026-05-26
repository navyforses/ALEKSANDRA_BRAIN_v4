"use client";

// viewer/components/inbox/ActiveQuestionsSection.tsx — Phase 7.6 widget.
//
// Lists Phase 7.4 active_questions for the current week. Reads from
// fetchActiveQuestions on mount (MOCK_MODE returns 2 sample rows). Each
// row shows the bilingual prompt + response status + parsed-value badge
// when present.

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import {
  fetchActiveQuestions,
  type ActiveQuestion,
  type QuestionStatus,
} from "@/lib/api/active";

interface Props {
  weekIso?: string;
  locale?: "en" | "ka";
}

function statusTone(status: QuestionStatus): string {
  switch (status) {
    case "responded":
      return "border-emerald-300 bg-emerald-50 text-emerald-900";
    case "open":
      return "border-cyan-300 bg-cyan-50 text-cyan-900";
    case "expired":
      return "border-stone-300 bg-stone-100 text-stone-700";
    default:
      return "border-amber-300 bg-amber-50 text-amber-900";
  }
}

export default function ActiveQuestionsSection({
  weekIso,
  locale = "en",
}: Props) {
  const t = useTranslations("ActiveQuestionsSection");
  const tDim = useTranslations("Twin.dimensions");
  const [questions, setQuestions] = useState<ActiveQuestion[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchActiveQuestions(weekIso)
      .then((qs) => {
        if (!cancelled) setQuestions(qs);
      })
      .catch(() => {
        if (!cancelled) setQuestions([]);
      });
    return () => {
      cancelled = true;
    };
  }, [weekIso]);

  if (questions === null) {
    return (
      <section className="rounded-md border border-stone-200 bg-white p-3 text-xs text-stone-500">
        {t("loading")}
      </section>
    );
  }

  return (
    <section className="rounded-md border border-stone-200 bg-white p-4">
      <header className="flex items-baseline justify-between border-b border-stone-100 pb-2">
        <h2 className="text-sm font-semibold text-stone-900">{t("title")}</h2>
        <span className="font-mono text-[10px] text-stone-400">
          {questions.length} {t("questionsSuffix")}
        </span>
      </header>

      {questions.length === 0 ? (
        <p className="mt-3 text-xs text-stone-500">{t("empty")}</p>
      ) : (
        <ul className="mt-3 flex flex-col gap-2">
          {questions.map((q) => {
            const prompt = locale === "ka" ? q.prompt_ka : q.prompt_en;
            const dimLabel = tDim.has(q.dim_name) ? tDim(q.dim_name) : q.dim_name;
            return (
              <li
                key={q.id}
                className="rounded-md border border-stone-200 bg-stone-50 p-3"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="font-mono text-[10px] uppercase text-stone-500">
                    {dimLabel}
                  </span>
                  <span
                    className={`rounded-md border px-2 py-0.5 font-mono text-[10px] uppercase ${statusTone(
                      q.status,
                    )}`}
                  >
                    {t(`status.${q.status}`)}
                  </span>
                </div>
                <p className="mt-1 text-xs leading-5 text-stone-800">{prompt}</p>
                {q.response_text ? (
                  <p className="mt-2 rounded-md bg-white px-2 py-1 text-[11px] italic leading-5 text-stone-700 ring-1 ring-stone-200">
                    {q.response_text}
                  </p>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
