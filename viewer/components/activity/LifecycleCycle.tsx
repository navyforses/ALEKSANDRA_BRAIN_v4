// Server Component — renders the 6-stage lifecycle pipeline.
// Motion is CSS-only, respects prefers-reduced-motion, no framer-motion/GSAP.
// The connecting line "fills" on load via a CSS animation scoped to the wrapper.

import type { LifecycleStages } from "@/lib/data";

// ---------------------------------------------------------------------------
// Stage type
// ---------------------------------------------------------------------------

interface Stage {
  num: number;
  id: string;
  icon: string;
  nameEN: string;
  nameKA: string;
  descEN: string;
  descKA: string;
  counts: string; // formatted count string (may be empty if not configured)
  accent: string; // Tailwind text/border accent class
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function relTime(iso: string | null): string {
  if (!iso) return "";
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 60_000) return "just now";
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)}m ago`;
  if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)}h ago`;
  return `${Math.floor(ms / 86_400_000)}d ago`;
}

function n(count: number): string {
  return count.toLocaleString("en-US");
}

// ---------------------------------------------------------------------------
// Build stage descriptors from live data
// ---------------------------------------------------------------------------

function buildStages(data: LifecycleStages): Stage[] {
  const cfg = data.configured;

  // Stage 1 — Discovery
  const registryList =
    data.registrySources.length > 0
      ? data.registrySources
          .map((r) => (r === "ctgov" ? "CT.gov" : r === "ctis" ? "EU CTIS" : r.toUpperCase()))
          .join(", ")
      : "CT.gov, EU CTIS, ISRCTN, PubMed";
  const stage1Counts = cfg
    ? `${n(data.totalTrials)} trials indexed · ${registryList}`
    : "CT.gov · EU CTIS · ISRCTN · PubMed · preprints";

  // Stage 2 — Ingest & dedupe
  const stage2Counts = cfg
    ? `${n(data.totalTrials)} records stored · cross-registry duplicates merged`
    : "new records saved · duplicates merged";

  // Stage 3 — Eligibility
  const stage3Counts = cfg
    ? `${n(data.identified)} eligible · ${n(data.evaluating)} needs review · ${n(data.ineligible)} ineligible`
    : "age · diagnosis · recruiting status · location";

  // Stage 4 — Translate
  const stage4Counts = cfg
    ? `${n(data.translated)} translated to Georgian`
    : "eligible & needs-review trials → Georgian";

  // Stage 5 — Publish & alert
  const stage5Counts = cfg
    ? `${n(data.published)} published on site · newly eligible → Telegram + Brief`
    : "visible on site · new eligible → Telegram + Brief";

  // Stage 6 — Monitor & decision
  const lastRan =
    cfg && data.lastCycleAt ? ` · last ran ${relTime(data.lastCycleAt)}` : "";
  const stage6Counts = cfg
    ? `${n(data.decided)} reached a decision${lastRan} · repeats every 6h`
    : "re-checked every 6h · applied → enrolled decision";

  return [
    {
      num: 1,
      id: "discovery",
      icon: "◎",
      nameEN: "Discovery",
      nameKA: "მოძიება",
      descEN: "Registries + sources scanned every 6h",
      descKA: "რეგისტრები სკანირდება ყოველ 6 საათში",
      counts: stage1Counts,
      accent: "text-accent-ink",
    },
    {
      num: 2,
      id: "ingest",
      icon: "▥",
      nameEN: "Ingest & dedupe",
      nameKA: "შემოტანა და დედუპლიკაცია",
      descEN: "New record saved to R2 + evidence ledger; cross-registry duplicates merged",
      descKA: "ახალი ჩანაწერი ინახება; სხვადასხვა რეგისტრის დუბლიკატები ერთდება",
      counts: stage2Counts,
      accent: "text-accent-ink",
    },
    {
      num: 3,
      id: "eligibility",
      icon: "⊡",
      nameEN: "Eligibility match",
      nameKA: "შეფასება",
      descEN: "Age · diagnosis · recruiting · location → eligible / needs-review / ineligible",
      descKA: "ასაკი · დიაგნოზი · ჩარიცხვა · ადგილი → შესაფერისი / გადასამოწმებელი / შეუფერებელი",
      counts: stage3Counts,
      accent: "text-signal",
    },
    {
      num: 4,
      id: "translate",
      icon: "⌨",
      nameEN: "Translate",
      nameKA: "თარგმნა",
      descEN: "Eligible & needs-review trials translated to Georgian (budget-gated)",
      descKA: "შესაფერისი კვლევები ითარგმნება ქართულად (ბიუჯეტის ლიმიტის ფარგლებში)",
      counts: stage4Counts,
      accent: "text-accent-ink",
    },
    {
      num: 5,
      id: "publish",
      icon: "◈",
      nameEN: "Publish & alert",
      nameKA: "გამოქვეყნება და შეტყობინება",
      descEN: "Trial appears on site; newly eligible → Telegram + weekly Brief",
      descKA: "კვლევა გამოჩნდება საიტზე; ახლად შესაფერისი → Telegram + კვირის რეზიუმე",
      counts: stage5Counts,
      accent: "text-signal",
    },
    {
      num: 6,
      id: "monitor",
      icon: "↻",
      nameEN: "Monitor → decision",
      nameKA: "მონიტორინგი და გადაწყვეტილება",
      descEN: "Re-checked each cycle; recruiting→closed flagged; doctor/family decides",
      descKA: "ყოველ ციკლში ხელახლა შემოწმება; გადაწყვეტილება ოჯახთან ან ექიმთან ერთად",
      counts: stage6Counts,
      accent: "text-muted",
    },
  ];
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StageNode({
  stage,
  isLast,
  locale,
}: {
  stage: Stage;
  isLast: boolean;
  locale: string;
}) {
  const isKa = locale === "ka";

  return (
    <li className="lifecycle-stage group relative flex flex-col items-center">
      {/* Connecting line above the node (desktop: left-right connector drawn on parent) */}
      {/* Node circle */}
      <div
        className={`lifecycle-node relative z-10 flex h-12 w-12 shrink-0 items-center justify-center
          rounded-full border-2 border-line bg-surface text-xl shadow-sm
          transition-colors group-hover:border-accent group-hover:bg-accent-soft`}
        aria-hidden
      >
        <span className={`select-none ${stage.accent}`}>{stage.icon}</span>
        {/* Stage number badge */}
        <span
          className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center
            rounded-full bg-accent text-[0.55rem] font-bold text-white"
        >
          {stage.num}
        </span>
      </div>

      {/* Stage content card */}
      <div className="mt-3 w-full rounded-xl border border-line bg-surface p-3 text-center">
        {/* Bilingual name */}
        <p className="text-[0.82rem] font-semibold leading-tight text-ink">
          {isKa ? stage.nameKA : stage.nameEN}
        </p>
        {isKa && (
          <p className="text-[0.68rem] text-faint leading-tight">{stage.nameEN}</p>
        )}
        {!isKa && (
          <p className="text-[0.68rem] text-faint leading-tight">{stage.nameKA}</p>
        )}

        {/* Description */}
        <p className="mt-1.5 text-[0.72rem] leading-relaxed text-muted">
          {isKa ? stage.descKA : stage.descEN}
        </p>

        {/* Live counts */}
        {stage.counts && (
          <p className={`mt-2 text-[0.7rem] font-medium leading-snug ${stage.accent}`}>
            {stage.counts}
          </p>
        )}
      </div>

      {/* Loop indicator on last stage */}
      {isLast && (
        <p className="mt-2 text-[0.65rem] text-faint">
          ↻ {isKa ? "ყოველ 6 საათში იმეორება" : "repeats every 6h"}
        </p>
      )}
    </li>
  );
}

// Mobile: vertical stack with left rail
function StageNodeMobile({
  stage,
  isLast,
  locale,
}: {
  stage: Stage;
  isLast: boolean;
  locale: string;
}) {
  const isKa = locale === "ka";

  return (
    <li className="lifecycle-stage-mobile relative flex gap-4">
      {/* Left column: circle + rail */}
      <div className="flex flex-col items-center">
        <div
          className={`lifecycle-node-mobile relative z-10 flex h-10 w-10 shrink-0 items-center
            justify-center rounded-full border-2 border-line bg-surface text-lg shadow-sm`}
          aria-hidden
        >
          <span className={`select-none ${stage.accent}`}>{stage.icon}</span>
          <span
            className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center
              rounded-full bg-accent text-[0.55rem] font-bold text-white"
          >
            {stage.num}
          </span>
        </div>
        {/* Rail segment below node */}
        {!isLast && (
          <div className="lifecycle-rail-mobile mt-1 w-px flex-1 bg-line" aria-hidden />
        )}
        {isLast && (
          <div className="mt-2 text-[0.65rem] text-faint leading-none" aria-hidden>↻</div>
        )}
      </div>

      {/* Right column: text */}
      <div className="mb-6 min-w-0 flex-1 pb-1">
        <p className="text-[0.82rem] font-semibold leading-tight text-ink">
          {isKa ? stage.nameKA : stage.nameEN}
        </p>
        <p className="text-[0.68rem] text-faint leading-tight">
          {isKa ? stage.nameEN : stage.nameKA}
        </p>
        <p className="mt-1 text-[0.72rem] leading-relaxed text-muted">
          {isKa ? stage.descKA : stage.descEN}
        </p>
        {stage.counts && (
          <p className={`mt-1 text-[0.7rem] font-medium leading-snug ${stage.accent}`}>
            {stage.counts}
          </p>
        )}
        {isLast && (
          <p className="mt-1 text-[0.65rem] text-faint">
            {isKa ? "ყოველ 6 საათში იმეორება" : "repeats every 6h"}
          </p>
        )}
      </div>
    </li>
  );
}

// ---------------------------------------------------------------------------
// Main export — LifecycleCycle (server component)
// ---------------------------------------------------------------------------

export default function LifecycleCycle({
  data,
  locale,
}: {
  data: LifecycleStages;
  locale: string;
}) {
  const stages = buildStages(data);
  const isKa = locale === "ka";

  const intro = isKa
    ? "თითოეული კვლევა გადის ამ ციკლს"
    : "Every trial passes through this cycle";

  return (
    <div className="lifecycle-wrapper">
      {/* CSS animations — scoped, no inline handlers, CSP-safe */}
      <style>{`
        @media (prefers-reduced-motion: no-preference) {
          .lifecycle-fill-line {
            animation: lifecycle-fill 1.2s cubic-bezier(0.22, 1, 0.36, 1) both;
            transform-origin: left center;
          }
          @keyframes lifecycle-fill {
            from { transform: scaleX(0); }
            to   { transform: scaleX(1); }
          }
          .lifecycle-fill-rail {
            animation: lifecycle-fill-y 1.2s cubic-bezier(0.22, 1, 0.36, 1) both;
            transform-origin: top center;
          }
          @keyframes lifecycle-fill-y {
            from { transform: scaleY(0); }
            to   { transform: scaleY(1); }
          }
        }
      `}</style>

      {/* Intro line */}
      <p className="mb-6 text-[0.88rem] leading-relaxed text-muted">
        <span className="font-medium text-ink">{intro}</span>
        {isKa
          ? " — ჩარიცხვის განაცხადიდან ექიმის გადაწყვეტილებამდე."
          : " — from initial scan to a doctor's decision."}
      </p>

      {/* ── Desktop: horizontal pipeline with filling connector line ── */}
      <div className="hidden sm:block" aria-hidden={false}>
        <div className="relative">
          {/* Background rail (full width, behind nodes) */}
          <div
            className="absolute left-0 right-0 top-6 h-0.5 bg-line"
            aria-hidden
          />
          {/* Animated fill overlay */}
          <div
            className="lifecycle-fill-line absolute left-0 right-0 top-6 h-0.5 origin-left bg-accent opacity-70"
            aria-hidden
          />

          {/* Stage nodes in a row */}
          <ol
            className="relative grid gap-3"
            style={{ gridTemplateColumns: `repeat(${stages.length}, minmax(0, 1fr))` }}
            aria-label={isKa ? "ციკლის ეტაპები" : "Lifecycle stages"}
          >
            {stages.map((stage, i) => (
              <StageNode
                key={stage.id}
                stage={stage}
                isLast={i === stages.length - 1}
                locale={locale}
              />
            ))}
          </ol>
        </div>

        {/* Loop back arrow (desktop) */}
        <div className="mt-4 flex items-center justify-end gap-1.5 text-[0.7rem] text-faint">
          <span aria-hidden>↻</span>
          <span>
            {isKa
              ? "ყოველ 6 საათში იწყება თავიდან — გაყინული კვლევები მონიშნულია, ახალი ინდექსირდება"
              : "Restarts every 6h — closed trials flagged, new ones indexed"}
          </span>
        </div>
      </div>

      {/* ── Mobile: vertical stack with left rail ── */}
      <div className="block sm:hidden">
        {/* Animated fill rail overlay — absolutely positioned behind the list */}
        <div className="relative">
          <div
            className="lifecycle-fill-rail absolute bottom-0 left-4 top-0 w-0.5 origin-top bg-accent opacity-60"
            aria-hidden
          />
          <ol
            aria-label={isKa ? "ციკლის ეტაპები" : "Lifecycle stages"}
          >
            {stages.map((stage, i) => (
              <StageNodeMobile
                key={stage.id}
                stage={stage}
                isLast={i === stages.length - 1}
                locale={locale}
              />
            ))}
          </ol>
        </div>

        {/* Loop back label (mobile) */}
        <p className="mt-2 text-[0.7rem] text-faint">
          {isKa
            ? "↻ ყოველ 6 საათში იწყება თავიდან"
            : "↻ Restarts every 6h"}
        </p>
      </div>
    </div>
  );
}
