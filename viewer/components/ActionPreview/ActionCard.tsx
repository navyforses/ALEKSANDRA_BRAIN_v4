import FieldDiff from "@/components/ActionPreview/FieldDiff";
import type { ActionCardPayload } from "@/lib/brain/apply";

const bandClass: Record<string, string> = {
  high: "border-signal-line bg-signal-soft text-signal",
  medium: "border-accent-line bg-accent-soft text-accent-ink",
  low: "border-line bg-paper text-muted",
};

export default function ActionCard({
  card,
  selected,
  onSelectedChange,
}: {
  card: ActionCardPayload
  selected: boolean
  onSelectedChange: (selected: boolean) => void
}) {
  return (
    <article className="card overflow-hidden">
      <div className="flex items-start gap-3 p-4">
        <input
          type="checkbox"
          checked={selected}
          onChange={(e) => onSelectedChange(e.target.checked)}
          aria-label={`Select ${card.summary}`}
          className="mt-1 h-4 w-4 rounded border-line accent-[var(--accent)]"
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full border px-2 py-0.5 text-[0.72rem] ${
                bandClass[card.confidence_band] ?? bandClass.low
              }`}
            >
              {Math.round(card.confidence * 100)}%
            </span>
            <span className="rounded-full bg-paper px-2 py-0.5 text-[0.72rem] text-muted">
              {card.action_type}
            </span>
            <span className="rounded-full bg-paper px-2 py-0.5 text-[0.72rem] text-muted">
              {card.target_table}
            </span>
          </div>
          <h3 className="mt-2 font-serif text-base leading-snug text-ink">
            {card.summary}
          </h3>
          {card.rationale ? (
            <p className="mt-1.5 text-sm leading-relaxed text-muted">{card.rationale}</p>
          ) : null}
          {card.warnings.length ? (
            <ul className="mt-2 space-y-1 text-xs text-urgent">
              {card.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          ) : null}
        </div>
      </div>

      {card.diff.length ? (
        <div aria-label="Before and after values">
          <div className="grid gap-2 border-t border-line bg-paper px-3 py-2 text-[0.68rem] font-medium uppercase text-faint sm:grid-cols-[9rem_1fr_1fr]">
            <span>Field</span>
            <span>Before</span>
            <span>After</span>
          </div>
          {card.diff.map((row) => (
            <FieldDiff key={row.field} row={row} />
          ))}
        </div>
      ) : null}
    </article>
  );
}
