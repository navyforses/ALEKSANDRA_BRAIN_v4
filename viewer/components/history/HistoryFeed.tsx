"use client";

// The transparent record. Every action BRAIN applied, newest first, with a
// real reversal — this calls /api/manager/undo (which forwards to the
// worker's undo() inside a transaction), not a cosmetic local toggle. The
// feed polls /api/manager/audit so a reversal made elsewhere shows up here
// too. No black box.

import { useState } from "react";
import { useTranslations } from "next-intl";
import { postUndo } from "@/lib/brain/undo";
import { useManagerActivity, type ManagerActionRow } from "@/lib/realtime";
import { IconUndo } from "@/components/shell/icons";

type HistoryT = ReturnType<typeof useTranslations<"History">>;

const UNDO_WINDOW_HOURS = 24;

function isUndoable(row: ManagerActionRow): boolean {
  if (row.reversed_at) return false;
  if (row.action_type === "reverse" || row.action_type === "dismiss") return false;
  if (!row.created_at) return false;
  const ageMs = Date.now() - new Date(row.created_at).getTime();
  return ageMs < UNDO_WINDOW_HOURS * 3_600_000;
}

function summarize(row: ManagerActionRow, t: HistoryT): string {
  const ap = row.after_payload as Record<string, unknown> | null;
  switch (row.action_type) {
    case "add_event":
      return t("summary.appointment", { title: String(ap?.title ?? "—"), date: String(ap?.event_date ?? "—") });
    case "add_milestone":
      return t("summary.observation", { title: String(ap?.title ?? "—") });
    case "add_contact":
      return t("summary.contact", { name: String(ap?.full_name ?? "—") });
    case "log_pattern":
      return t("summary.pattern", { description: String(ap?.description ?? "—") });
    case "reverse":
      return t("summary.reversed", { id: String(row.target_record_id ?? "").slice(0, 8) });
    case "dismiss":
      return t("summary.dismissed");
    case "create":
      if (row.target_table === "therapies")
        return t("summary.newTherapy", { name: String(ap?.name ?? "—") });
      return t("summary.created", { table: row.target_table });
    case "update":
      if (row.target_table === "therapies") return t("summary.therapyNote");
      return t("summary.updated", { table: row.target_table });
    default:
      return t("summary.fallback", { action: row.action_type, table: row.target_table });
  }
}

function relativeTime(iso: string | null, t: HistoryT): string {
  if (!iso) return "";
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 60_000) return t("time.justNow");
  if (ms < 3_600_000) return t("time.minutesAgo", { n: Math.floor(ms / 60_000) });
  if (ms < 86_400_000) return t("time.hoursAgo", { n: Math.floor(ms / 3_600_000) });
  return new Date(iso).toLocaleDateString();
}

function Row({
  row,
  t,
  onChanged,
}: {
  row: ManagerActionRow;
  t: HistoryT;
  onChanged: () => void;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reversed = !!row.reversed_at;

  async function undo() {
    setPending(true);
    setError(null);
    try {
      await postUndo(row.id);
      onChanged();
    } catch (err) {
      setError((err as Error).message.slice(0, 120));
    } finally {
      setPending(false);
    }
  }

  return (
    <li className={`card p-4 ${reversed ? "opacity-60" : ""}`}>
      <div className="flex items-start justify-between gap-4">
        <p className={`text-sm leading-snug ${reversed ? "text-faint line-through" : "text-ink"}`}>
          {summarize(row, t)}
        </p>
        <span className="shrink-0 text-xs text-faint">{relativeTime(row.created_at, t)}</span>
      </div>

      <div className="mt-2.5 flex items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1.5 text-[0.72rem] text-faint">
          {row.target_table ? (
            <span className="rounded-full bg-paper px-2 py-0.5">{row.target_table}</span>
          ) : null}
          {row.source_input ? (
            <span className="rounded-full bg-paper px-2 py-0.5">
              {t("via", { source: row.source_input })}
            </span>
          ) : null}
        </div>

        {reversed ? (
          <span className="text-xs text-faint">{t("undone")}</span>
        ) : isUndoable(row) ? (
          <button
            type="button"
            onClick={undo}
            disabled={pending}
            className="inline-flex items-center gap-1.5 rounded-full border border-line px-2.5 py-1 text-xs font-medium text-muted transition-colors hover:border-accent-line hover:text-accent-ink disabled:opacity-50"
          >
            <IconUndo className="h-3.5 w-3.5" />
            {pending ? t("undoing") : t("undo")}
          </button>
        ) : null}
      </div>

      {error ? <p className="mt-2 text-xs text-urgent">{error}</p> : null}
    </li>
  );
}

export default function HistoryFeed() {
  const t = useTranslations("History");
  const { rows, error, refresh } = useManagerActivity({ intervalMs: 5000, limit: 50 });

  if (error) {
    return (
      <div className="rounded-xl border border-line bg-surface px-5 py-10 text-center">
        <p className="text-sm text-muted">{t("unreachable")}</p>
        <p className="mt-1 text-xs text-faint">{error}</p>
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="rounded-xl border border-line bg-surface px-5 py-12 text-center">
        <p className="text-sm text-muted">{t("empty")}</p>
        <p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-faint">{t("emptyNote")}</p>
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {rows.map((row) => (
        <Row key={row.id} row={row} t={t} onChanged={refresh} />
      ))}
    </ul>
  );
}
