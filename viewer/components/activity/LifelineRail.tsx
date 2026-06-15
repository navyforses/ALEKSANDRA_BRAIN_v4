// Server Component — no "use client" needed.
// Renders the vertical timeline rail with day nodes and milestone markers.

import type { LifelineDayBucket, LifelineMilestone } from "@/lib/data";

// ---------------------------------------------------------------------------
// Source-type → display config
// ---------------------------------------------------------------------------

interface SourceConfig {
  label: string;
  color: string; // Tailwind text-color class
  bgColor: string; // Tailwind bg-color class for chips
}

const SOURCE_MAP: Record<string, SourceConfig> = {
  pubmed: {
    label: "PubMed",
    color: "text-accent-ink",
    bgColor: "bg-accent-soft",
  },
  ctgov: {
    label: "CT.gov",
    color: "text-signal",
    bgColor: "bg-signal-soft",
  },
  ctis: {
    label: "CTIS",
    color: "text-signal",
    bgColor: "bg-signal-soft",
  },
  isrctn: {
    label: "ISRCTN",
    color: "text-signal",
    bgColor: "bg-signal-soft",
  },
  preprint: {
    label: "Preprint",
    color: "text-muted",
    bgColor: "bg-surface",
  },
  biorxiv: {
    label: "bioRxiv",
    color: "text-muted",
    bgColor: "bg-surface",
  },
  medrxiv: {
    label: "medRxiv",
    color: "text-muted",
    bgColor: "bg-surface",
  },
  trials: {
    label: "Trials",
    color: "text-signal",
    bgColor: "bg-signal-soft",
  },
};

function sourceConfig(key: string): SourceConfig {
  return (
    SOURCE_MAP[key.toLowerCase()] ?? {
      label: key,
      color: "text-faint",
      bgColor: "bg-surface",
    }
  );
}

// ---------------------------------------------------------------------------
// Milestone kind → display
// ---------------------------------------------------------------------------

const MILESTONE_ICONS: Record<string, string> = {
  perception_tick: "◉",
  perception_tick_fallback: "◎",
  weekly_brief: "▶",
  weekly_brief_trigger: "▷",
  budget_lock: "⊘",
};

const MILESTONE_LABELS: Record<string, string> = {
  perception_tick: "System scan",
  perception_tick_fallback: "Fallback scan",
  weekly_brief: "Weekly brief",
  weekly_brief_trigger: "Brief triggered",
  budget_lock: "Budget lock",
};

function milestoneIcon(kind: string): string {
  return MILESTONE_ICONS[kind] ?? "·";
}

function milestoneLabel(kind: string): string {
  return MILESTONE_LABELS[kind] ?? kind.replace(/_/g, " ");
}

// ---------------------------------------------------------------------------
// Date formatting
// ---------------------------------------------------------------------------

function formatDisplayDate(isoDate: string, locale: string): string {
  const d = new Date(`${isoDate}T12:00:00Z`);
  return new Intl.DateTimeFormat(locale === "ka" ? "ka-GE" : "en-US", {
    month: "short",
    day: "numeric",
    weekday: "short",
  }).format(d);
}

function formatMilestoneTime(ts: string, locale: string): string {
  const d = new Date(ts);
  return new Intl.DateTimeFormat(locale === "ka" ? "ka-GE" : "en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

// ---------------------------------------------------------------------------
// Mini bar — proportional width to day total
// ---------------------------------------------------------------------------

function MiniBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.max(4, Math.round((value / max) * 100)) : 4;
  return (
    <div
      className="mt-1.5 h-1 rounded-full bg-accent-soft overflow-hidden"
      aria-hidden
    >
      <div
        className="h-full rounded-full bg-accent lifeline-bar"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Source chips
// ---------------------------------------------------------------------------

function SourceChips({ bySource, trials }: { bySource: Record<string, number>; trials: number }) {
  const entries = Object.entries(bySource).sort((a, b) => b[1] - a[1]);
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {entries.map(([src, count]) => {
        const cfg = sourceConfig(src);
        return (
          <span
            key={src}
            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[0.68rem] font-medium ${cfg.color} ${cfg.bgColor}`}
          >
            {cfg.label}
            <span className="font-normal opacity-70">{count}</span>
          </span>
        );
      })}
      {trials > 0 && (
        <span className="inline-flex items-center gap-1 rounded-full bg-signal-soft px-2 py-0.5 text-[0.68rem] font-medium text-signal">
          {SOURCE_MAP.trials.label}
          <span className="font-normal opacity-70">{trials}</span>
        </span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Milestone marker (inline on rail)
// ---------------------------------------------------------------------------

function MilestoneMarker({
  milestone,
  locale,
}: {
  milestone: LifelineMilestone;
  locale: string;
}) {
  const ok = !milestone.status || milestone.status === "ok" || milestone.status === "success";
  const err = milestone.status === "error" || milestone.status === "failed";

  return (
    <li className="relative flex items-start gap-3 py-2 pl-8">
      {/* Rail connector */}
      <span
        aria-hidden
        className="absolute left-[0.6rem] top-0 -bottom-0 w-px bg-line"
      />
      {/* Node */}
      <span
        aria-hidden
        className={`absolute left-0 top-3 flex h-5 w-5 items-center justify-center rounded-full text-[0.6rem] border ${
          err
            ? "border-urgent text-urgent bg-urgent-soft"
            : "border-line text-faint bg-surface"
        }`}
      >
        {milestoneIcon(milestone.kind)}
      </span>

      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className={`text-[0.78rem] font-medium ${err ? "text-urgent" : "text-muted"}`}>
            {milestoneLabel(milestone.kind)}
          </span>
          {milestone.status ? (
            <span
              className={`text-[0.65rem] rounded-full px-1.5 py-0 ${
                ok
                  ? "bg-signal-soft text-signal"
                  : err
                  ? "bg-urgent-soft text-urgent"
                  : "bg-surface text-faint"
              }`}
            >
              {milestone.status}
            </span>
          ) : null}
          <span className="text-[0.68rem] text-faint ml-auto">
            {formatMilestoneTime(milestone.ts, locale)}
          </span>
        </div>
      </div>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Day node
// ---------------------------------------------------------------------------

function DayNode({
  bucket,
  max,
  isToday,
  milestonesOnDay,
  locale,
}: {
  bucket: LifelineDayBucket;
  max: number;
  isToday: boolean;
  milestonesOnDay: LifelineMilestone[];
  locale: string;
}) {
  const dayTotal = bucket.total + bucket.trials;

  return (
    <li className="relative pl-8">
      {/* Vertical rail segment */}
      <span
        aria-hidden
        className="absolute left-[0.6rem] top-0 bottom-0 w-px bg-line"
      />

      {/* Day node dot */}
      <span
        aria-hidden
        className={`absolute left-0 top-5 flex h-5 w-5 items-center justify-center rounded-full border ${
          isToday
            ? "border-accent bg-accent-soft"
            : "border-line-strong bg-surface"
        }`}
      >
        <span
          className={`h-2 w-2 rounded-full ${
            isToday ? "bg-accent" : dayTotal > 50 ? "bg-accent" : "bg-line-strong"
          }`}
        />
      </span>

      {/* Content card */}
      <div className="mb-4 mt-3 rounded-xl border border-line bg-surface p-3.5">
        {/* Date + total */}
        <div className="flex items-baseline justify-between gap-2">
          <time
            dateTime={bucket.date}
            className={`text-[0.82rem] font-medium ${isToday ? "text-accent-ink" : "text-ink"}`}
          >
            {formatDisplayDate(bucket.date, locale)}
            {isToday ? (
              <span className="ml-2 text-[0.68rem] font-normal text-accent">(today)</span>
            ) : null}
          </time>
          <span className="shrink-0 text-[0.75rem] font-semibold text-accent-ink">
            +{dayTotal}
          </span>
        </div>

        {/* Mini bar */}
        <MiniBar value={dayTotal} max={max} />

        {/* Source chips */}
        {Object.keys(bucket.bySource).length > 0 || bucket.trials > 0 ? (
          <SourceChips bySource={bucket.bySource} trials={bucket.trials} />
        ) : null}
      </div>

      {/* Milestones on this day */}
      {milestonesOnDay.length > 0 ? (
        <ul className="mb-4 -mt-2 space-y-0">
          {milestonesOnDay.map((m, i) => (
            <MilestoneMarker key={`${m.kind}-${m.ts}-${i}`} milestone={m} locale={locale} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

// ---------------------------------------------------------------------------
// Today pulse node (live end of the rail)
// ---------------------------------------------------------------------------

function TodayPulse({ label }: { label: string }) {
  return (
    <li className="relative pl-8 pb-2">
      {/* No rail below — this is the end */}
      <span
        aria-hidden
        className="absolute left-[0.6rem] top-0 h-5 w-px bg-line"
      />
      {/* Pulse dot */}
      <span
        aria-hidden
        className="absolute left-0 top-5 flex h-5 w-5 items-center justify-center"
      >
        <span className="lifeline-pulse absolute h-5 w-5 rounded-full bg-accent opacity-20" />
        <span className="relative h-2.5 w-2.5 rounded-full bg-accent" />
      </span>

      <span className="ml-1 mt-4 block text-[0.72rem] font-medium text-accent">
        {label}
      </span>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Rail — full lifeline
// ---------------------------------------------------------------------------

export default function LifelineRail({
  days,
  milestones,
  locale,
  nowLabel,
}: {
  days: LifelineDayBucket[];
  milestones: LifelineMilestone[];
  locale: string;
  nowLabel: string;
}) {
  if (days.length === 0) return null;

  const maxTotal = Math.max(...days.map((d) => d.total + d.trials), 1);
  const todayIso = new Date().toISOString().slice(0, 10);

  // Index milestones by date so we can attach them under the right day node.
  const milestonesByDay = new Map<string, LifelineMilestone[]>();
  for (const m of milestones) {
    const d = m.ts.slice(0, 10);
    if (!milestonesByDay.has(d)) milestonesByDay.set(d, []);
    milestonesByDay.get(d)!.push(m);
  }

  // Milestones on days that have NO evidence_ledger bucket (orphan milestones).
  const knownDays = new Set(days.map((d) => d.date));
  const orphanMilestoneDays = Array.from(milestonesByDay.entries())
    .filter(([d]) => !knownDays.has(d))
    .sort(([a], [b]) => (a < b ? -1 : 1));

  // We render oldest first (ascending) — the line "fills" from bottom → top
  // on a CSS transform perspective; on screen, oldest is at top, newest at bottom,
  // and the "now" pulse is the bottom terminus.
  // Actually for UX clarity: oldest at top, newest (today) at bottom.
  const orderedDays = [...days]; // already oldest→newest from fetchSystemLifeline

  return (
    <div className="lifeline-rail-wrapper">
      {/* Inline styles for fill animation + pulse — scoped, CSP-safe (no inline event handlers).
          All motion wrapped in @media query via the class approach.
          Using a <style> tag in a server component for scoped animation keyframes. */}
      <style>{`
        @media (prefers-reduced-motion: no-preference) {
          .lifeline-bar {
            animation: lifeline-fill 0.8s cubic-bezier(0.22, 1, 0.36, 1) both;
          }
          @keyframes lifeline-fill {
            from { width: 0%; }
          }
          .lifeline-pulse {
            animation: lifeline-pulse-ring 2.4s ease-in-out infinite;
          }
          @keyframes lifeline-pulse-ring {
            0%, 100% { transform: scale(1); opacity: 0.2; }
            50% { transform: scale(1.9); opacity: 0; }
          }
        }
      `}</style>

      <ol className="relative">
        {/* Oldest days first */}
        {orderedDays.map((bucket) => {
          const isToday = bucket.date === todayIso;
          const milestonesOnDay = milestonesByDay.get(bucket.date) ?? [];
          return (
            <DayNode
              key={bucket.date}
              bucket={bucket}
              max={maxTotal}
              isToday={isToday}
              milestonesOnDay={milestonesOnDay}
              locale={locale}
            />
          );
        })}

        {/* Orphan milestones (on days with no evidence_ledger entries) */}
        {orphanMilestoneDays.map(([day, ms]) => (
          <li key={`orphan-${day}`} className="relative pl-8 pb-2">
            <span
              aria-hidden
              className="absolute left-[0.6rem] top-0 bottom-0 w-px bg-line"
            />
            <div className="mb-2 mt-3">
              <time
                dateTime={day}
                className="text-[0.75rem] text-faint"
              >
                {formatDisplayDate(day, locale)}
              </time>
            </div>
            <ul>
              {ms.map((m, i) => (
                <MilestoneMarker
                  key={`${m.kind}-${m.ts}-${i}`}
                  milestone={m}
                  locale={locale}
                />
              ))}
            </ul>
          </li>
        ))}

        {/* "Now" terminus with pulse */}
        <TodayPulse label={nowLabel} />
      </ol>
    </div>
  );
}
