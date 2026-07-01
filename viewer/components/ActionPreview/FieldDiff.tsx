import type { ActionFieldDiff } from "@/lib/brain/apply";

function renderValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export default function FieldDiff({ row }: { row: ActionFieldDiff }) {
  return (
    <div
      className={`grid gap-2 border-t border-line px-3 py-2.5 text-xs sm:grid-cols-[9rem_1fr_1fr] ${
        row.changed ? "bg-accent-soft/45" : "bg-transparent"
      }`}
    >
      <span className="font-medium text-muted">{row.field}</span>
      <span className="min-w-0 break-words text-faint">{renderValue(row.before)}</span>
      <span className="min-w-0 break-words text-ink">{renderValue(row.after)}</span>
    </div>
  );
}
