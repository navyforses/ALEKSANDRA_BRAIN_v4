import type { ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";

const GENERATED_BRAIN_IMAGE = "/assets/generated_digital_twin_brain.webp";

type Tone = "cyan" | "emerald" | "amber" | "rose" | "violet" | "slate" | "stone";

const toneClasses: Record<Tone, string> = {
  cyan: "border-cyan-200 bg-cyan-50 text-cyan-900 shadow-cyan-950/5",
  emerald: "border-emerald-200 bg-emerald-50 text-emerald-900 shadow-emerald-950/5",
  amber: "border-amber-200 bg-amber-50 text-amber-900 shadow-amber-950/5",
  rose: "border-rose-200 bg-rose-50 text-rose-900 shadow-rose-950/5",
  violet: "border-violet-200 bg-violet-50 text-violet-900 shadow-violet-950/5",
  slate: "border-slate-200 bg-slate-50 text-slate-900 shadow-slate-950/5",
  stone: "border-stone-200 bg-white text-stone-900 shadow-stone-950/5",
};

const darkToneClasses: Record<Tone, string> = {
  cyan: "border-cyan-300/25 bg-cyan-300/10 text-cyan-100 shadow-cyan-950/20",
  emerald: "border-emerald-300/25 bg-emerald-300/10 text-emerald-100 shadow-emerald-950/20",
  amber: "border-amber-300/25 bg-amber-300/10 text-amber-100 shadow-amber-950/20",
  rose: "border-rose-300/25 bg-rose-300/10 text-rose-100 shadow-rose-950/20",
  violet: "border-violet-300/25 bg-violet-300/10 text-violet-100 shadow-violet-950/20",
  slate: "border-white/10 bg-white/[0.06] text-slate-100 shadow-slate-950/20",
  stone: "border-white/10 bg-white/[0.08] text-white shadow-slate-950/20",
};

export function PrototypeShell({ children }: { children: ReactNode }) {
  return (
    <main className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.18),_transparent_32%),linear-gradient(135deg,#f8fafc_0%,#f5f5f4_48%,#eef2ff_100%)] text-slate-950">
      <div className="pointer-events-none fixed inset-0 opacity-[0.28] [background-image:linear-gradient(rgba(15,23,42,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(15,23,42,0.05)_1px,transparent_1px)] [background-size:44px_44px]" />
      <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-8 px-5 py-6 sm:px-8 lg:py-8">
        {children}
      </div>
    </main>
  );
}

export function CommandCenterShell({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <main className={`min-h-screen overflow-hidden bg-slate-950 text-white ${className}`}>
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_20%_0%,rgba(34,211,238,0.18),transparent_30%),radial-gradient(circle_at_85%_20%,rgba(124,58,237,0.16),transparent_26%),linear-gradient(135deg,#020617_0%,#0f172a_44%,#111827_100%)]" />
      <div className="pointer-events-none fixed inset-0 opacity-[0.16] [background-image:linear-gradient(rgba(148,163,184,0.18)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,0.18)_1px,transparent_1px)] [background-size:56px_56px]" />
      <div className="relative mx-auto flex w-full max-w-[1500px] flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        {children}
      </div>
    </main>
  );
}

export function FamilyPortalShell({ children }: { children: ReactNode }) {
  return (
    <main className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_18%_8%,rgba(14,165,233,0.18),transparent_28%),radial-gradient(circle_at_88%_0%,rgba(16,185,129,0.16),transparent_24%),linear-gradient(135deg,#f8fafc_0%,#eff6ff_45%,#f0fdf4_100%)] text-slate-950">
      <div className="pointer-events-none fixed inset-0 opacity-[0.22] [background-image:linear-gradient(rgba(15,23,42,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(15,23,42,0.05)_1px,transparent_1px)] [background-size:48px_48px]" />
      <div className="relative mx-auto flex w-full max-w-[1450px] flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        {children}
      </div>
    </main>
  );
}

export function GlassPanel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <section className={`min-w-0 overflow-hidden rounded-[2rem] border border-white/70 bg-white/78 p-5 shadow-xl shadow-slate-950/[0.06] backdrop-blur ${className}`}>
      {children}
    </section>
  );
}

export function DarkGlassPanel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <section className={`min-w-0 overflow-hidden rounded-[2rem] border border-white/10 bg-white/[0.055] p-5 shadow-2xl shadow-slate-950/25 backdrop-blur-xl ${className}`}>
      {children}
    </section>
  );
}

export function StatusPill({ children, tone = "stone", compact = false, dark = false }: { children: ReactNode; tone?: Tone; compact?: boolean; dark?: boolean }) {
  return (
    <span className={`inline-flex items-center rounded-full border font-mono uppercase tracking-[0.18em] ${dark ? darkToneClasses[tone] : toneClasses[tone]} ${compact ? "px-2.5 py-1 text-[0.62rem]" : "px-3 py-1.5 text-[0.68rem]"}`}>
      {children}
    </span>
  );
}

export function PrototypeHero({ eyebrow, title, subtitle, primaryAction, secondaryAction, stats = [], children }: { eyebrow: string; title: string; subtitle: string; primaryAction?: { label: string; href: string }; secondaryAction?: { label: string; href: string }; stats?: Array<{ label: string; value: string; tone?: Tone }>; children?: ReactNode }) {
  return (
    <GlassPanel className="p-6 sm:p-8 lg:p-10">
      <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
        <div>
          <StatusPill tone="cyan">{eyebrow}</StatusPill>
          <h1 className="mt-5 max-w-4xl text-4xl font-semibold tracking-[-0.045em] text-slate-950 sm:text-5xl lg:text-6xl">{title}</h1>
          <p className="mt-5 max-w-3xl text-base leading-8 text-slate-600 sm:text-lg">{subtitle}</p>
          {(primaryAction || secondaryAction) ? (
            <div className="mt-7 flex flex-wrap gap-3">
              {primaryAction ? <Link href={primaryAction.href} className="rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-slate-950/15 transition hover:-translate-y-0.5 hover:bg-slate-800">{primaryAction.label}</Link> : null}
              {secondaryAction ? <Link href={secondaryAction.href} className="rounded-full border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-800 shadow-sm transition hover:-translate-y-0.5 hover:border-cyan-300 hover:text-cyan-900">{secondaryAction.label}</Link> : null}
            </div>
          ) : null}
        </div>
        <div className="grid gap-4">
          {stats.length > 0 ? <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">{stats.map((stat) => <MetricTile key={stat.label} label={stat.label} value={stat.value} tone={stat.tone || "stone"} />)}</div> : children}
        </div>
      </div>
      {stats.length > 0 && children ? <div className="mt-8">{children}</div> : null}
    </GlassPanel>
  );
}

export function MetricTile({ label, value, hint, tone = "stone" }: { label: string; value: string | number; hint?: string; tone?: Tone }) {
  return (
    <div className={`rounded-3xl border p-5 shadow-lg ${toneClasses[tone]}`}>
      <p className="font-mono text-[0.68rem] uppercase tracking-[0.18em] opacity-70">{label}</p>
      <p className="mt-3 text-3xl font-semibold tracking-[-0.04em]">{value}</p>
      {hint ? <p className="mt-2 text-sm leading-6 opacity-75">{hint}</p> : null}
    </div>
  );
}

export function CommandMetricCard({ label, value, hint, tone = "cyan" }: { label: string; value: string | number; hint: string; tone?: Tone }) {
  return (
    <div className={`rounded-[1.6rem] border p-4 shadow-2xl backdrop-blur-xl ${darkToneClasses[tone]}`}>
      <p className="font-mono text-[0.65rem] uppercase tracking-[0.18em] opacity-70">{label}</p>
      <div className="mt-3 flex items-end justify-between gap-4">
        <p className="text-3xl font-semibold tracking-[-0.05em] text-white">{value}</p>
        <span className="h-2 w-16 rounded-full bg-current opacity-35" />
      </div>
      <p className="mt-3 text-xs leading-5 opacity-75">{hint}</p>
    </div>
  );
}

export function CapabilityCard({ label, title, body, tone = "stone" }: { label: string; title: string; body: string; tone?: Tone }) {
  return (
    <article className="group rounded-3xl border border-white/70 bg-white/82 p-5 shadow-lg shadow-slate-950/[0.04] backdrop-blur transition hover:-translate-y-1 hover:shadow-xl">
      <StatusPill tone={tone} compact>{label}</StatusPill>
      <h3 className="mt-4 text-lg font-semibold tracking-[-0.02em] text-slate-950">{title}</h3>
      <p className="mt-3 text-sm leading-7 text-slate-600">{body}</p>
    </article>
  );
}

export function SectionHeader({ eyebrow, title, subtitle, dark = false }: { eyebrow: string; title: string; subtitle?: string; dark?: boolean }) {
  return (
    <div className="max-w-3xl">
      <p className={`font-mono text-xs uppercase tracking-[0.2em] ${dark ? "text-cyan-200" : "text-cyan-700"}`}>{eyebrow}</p>
      <h2 className={`mt-2 text-2xl font-semibold tracking-[-0.035em] sm:text-3xl ${dark ? "text-white" : "text-slate-950"}`}>{title}</h2>
      {subtitle ? <p className={`mt-3 text-sm leading-7 ${dark ? "text-slate-300" : "text-slate-600"}`}>{subtitle}</p> : null}
    </div>
  );
}

export function EvidencePipeline({ steps, dark = false }: { steps: Array<{ label: string; title: string; body: string; tone?: Tone }>; dark?: boolean }) {
  return (
    <div className="grid gap-4 lg:grid-cols-4">
      {steps.map((step, index) => (
        <article key={step.title} className={`relative rounded-3xl border p-5 shadow-lg ${dark ? "border-white/10 bg-white/[0.055] shadow-slate-950/20" : "border-white/70 bg-white/82 shadow-slate-950/[0.04]"}`}>
          <div className="flex items-center justify-between gap-3">
            <StatusPill tone={step.tone || "cyan"} compact dark={dark}>{step.label}</StatusPill>
            <span className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold ${dark ? "bg-cyan-300 text-slate-950" : "bg-slate-950 text-white"}`}>{index + 1}</span>
          </div>
          <h3 className={`mt-4 text-base font-semibold ${dark ? "text-white" : "text-slate-950"}`}>{step.title}</h3>
          <p className={`mt-2 text-sm leading-7 ${dark ? "text-slate-300" : "text-slate-600"}`}>{step.body}</p>
        </article>
      ))}
    </div>
  );
}

export function SafetyBoundary({ title, body, items, dark = false }: { title: string; body: string; items: string[]; dark?: boolean }) {
  if (dark) {
    return (
      <DarkGlassPanel className="border-amber-300/20 bg-amber-300/[0.08]">
        <div className="grid gap-5 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
          <div>
            <StatusPill tone="amber" dark>Safety boundary</StatusPill>
            <h2 className="mt-4 text-2xl font-semibold tracking-[-0.035em] text-amber-50">{title}</h2>
            <p className="mt-3 text-sm leading-7 text-amber-100/80">{body}</p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">{items.map((item) => <div key={item} className="rounded-2xl border border-amber-300/20 bg-slate-950/35 p-4 text-sm font-medium leading-6 text-amber-50">{item}</div>)}</div>
        </div>
      </DarkGlassPanel>
    );
  }

  return (
    <GlassPanel className="border-amber-200/80 bg-amber-50/75">
      <div className="grid gap-5 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
        <div>
          <StatusPill tone="amber">Safety boundary</StatusPill>
          <h2 className="mt-4 text-2xl font-semibold tracking-[-0.035em] text-amber-950">{title}</h2>
          <p className="mt-3 text-sm leading-7 text-amber-900/80">{body}</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">{items.map((item) => <div key={item} className="rounded-2xl border border-amber-200 bg-white/70 p-4 text-sm font-medium leading-6 text-amber-950">{item}</div>)}</div>
      </div>
    </GlassPanel>
  );
}

export function NeuralHeroVisual({ title = "Neural evidence map", subtitle = "Clinical, research, therapy and timeline signals converge here." }: { title?: string; subtitle?: string }) {
  return (
    <div className="relative min-h-[28rem] overflow-hidden rounded-[2.25rem] border border-cyan-300/20 bg-slate-950 p-5 shadow-[0_0_80px_rgba(34,211,238,0.12)]">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_44%,rgba(34,211,238,0.40),transparent_25%),radial-gradient(circle_at_42%_54%,rgba(244,63,94,0.28),transparent_14%),radial-gradient(circle_at_62%_48%,rgba(16,185,129,0.24),transparent_16%),radial-gradient(circle_at_50%_50%,rgba(99,102,241,0.32),transparent_34%)]" />
      <div className="absolute left-[20%] top-[22%] h-2 w-2 rounded-full bg-cyan-200 shadow-[0_0_24px_rgba(103,232,249,0.95)]" />
      <div className="absolute right-[24%] top-[34%] h-2 w-2 rounded-full bg-violet-200 shadow-[0_0_24px_rgba(196,181,253,0.95)]" />
      <div className="absolute bottom-[28%] left-[33%] h-2 w-2 rounded-full bg-emerald-200 shadow-[0_0_24px_rgba(110,231,183,0.95)]" />
      <div className="absolute inset-x-10 top-1/2 h-px rotate-[-16deg] bg-cyan-200/25" />
      <div className="absolute inset-x-16 top-[42%] h-px rotate-[22deg] bg-violet-200/20" />
      <div className="relative z-10 flex h-full min-h-[26rem] flex-col justify-between">
        <div className="flex items-center justify-between gap-3">
          <StatusPill tone="cyan" dark>live mockup</StatusPill>
          <StatusPill tone="emerald" dark>human gate</StatusPill>
        </div>
        <div className="mx-auto max-w-md text-center">
          <div className="relative mx-auto h-48 w-full max-w-md overflow-hidden rounded-[2rem] border border-cyan-200/25 bg-slate-950 shadow-[0_0_70px_rgba(34,211,238,0.24)]">
            <Image src={GENERATED_BRAIN_IMAGE} alt="" fill sizes="(min-width: 1024px) 28rem, 90vw" className="object-cover object-center opacity-95" />
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_48%,transparent_42%,rgba(2,6,23,0.36)_76%),linear-gradient(180deg,rgba(2,6,23,0.05),rgba(2,6,23,0.24))]" />
          </div>
          <h3 className="mt-6 text-2xl font-semibold tracking-[-0.04em] text-white">{title}</h3>
          <p className="mt-3 text-sm leading-7 text-slate-300">{subtitle}</p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center text-[0.65rem] uppercase tracking-[0.16em] text-slate-400">
          <span>evidence</span><span>therapy</span><span>timeline</span>
        </div>
      </div>
    </div>
  );
}

export function BrainSignalPanel({ title, subtitle, signals }: { title: string; subtitle: string; signals: Array<{ label: string; value: string; tone?: Tone }> }) {
  return (
    <div className="rounded-[2rem] border border-slate-800 bg-slate-950 p-5 text-white shadow-2xl shadow-slate-950/25">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-cyan-300">Digital twin preview</p>
          <h3 className="mt-2 text-2xl font-semibold tracking-[-0.04em]">{title}</h3>
          <p className="mt-2 max-w-xl text-sm leading-7 text-slate-300">{subtitle}</p>
        </div>
        <StatusPill tone="emerald">human reviewed</StatusPill>
      </div>
      <div className="mt-6 grid gap-3 sm:grid-cols-3">{signals.map((signal) => <div key={signal.label} className="rounded-2xl border border-white/10 bg-white/[0.06] p-4"><p className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-slate-400">{signal.label}</p><p className="mt-2 text-xl font-semibold text-white">{signal.value}</p></div>)}</div>
      <div className="relative mt-6 h-48 overflow-hidden rounded-3xl border border-cyan-300/20 bg-slate-950 shadow-[0_0_54px_rgba(34,211,238,0.14)]">
        <Image src={GENERATED_BRAIN_IMAGE} alt="" fill sizes="(min-width: 1024px) 42rem, 90vw" className="object-cover object-center opacity-95" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_44%,transparent_46%,rgba(2,6,23,0.42)_82%),linear-gradient(90deg,rgba(2,6,23,0.18),transparent_34%,transparent_66%,rgba(2,6,23,0.18))]" />
      </div>
    </div>
  );
}

export function TimelineRail({ events, dark = false }: { events: Array<{ time: string; title: string; body: string; tone?: Tone }>; dark?: boolean }) {
  return (
    <div className="grid gap-4">
      {events.map((event) => (
        <article key={`${event.time}-${event.title}`} className={`grid gap-4 rounded-3xl border p-5 shadow-lg sm:grid-cols-[9rem_1fr] ${dark ? "border-white/10 bg-white/[0.055] shadow-slate-950/20" : "border-white/70 bg-white/82 shadow-slate-950/[0.04]"}`}>
          <div><StatusPill tone={event.tone || "slate"} compact dark={dark}>{event.time}</StatusPill></div>
          <div><h3 className={`text-base font-semibold ${dark ? "text-white" : "text-slate-950"}`}>{event.title}</h3><p className={`mt-2 text-sm leading-7 ${dark ? "text-slate-300" : "text-slate-600"}`}>{event.body}</p></div>
        </article>
      ))}
    </div>
  );
}

export function InsightCard({ label, title, body, meta, tone = "stone", dark = false }: { label: string; title: string; body: string; meta?: string; tone?: Tone; dark?: boolean }) {
  return (
    <article className={`min-w-0 overflow-hidden rounded-3xl border p-5 shadow-lg ${dark ? "border-white/10 bg-white/[0.055] shadow-slate-950/20" : "border-white/70 bg-white/84 shadow-slate-950/[0.04]"}`}>
      <div className="flex flex-wrap items-center gap-2"><StatusPill tone={tone} compact dark={dark}>{label}</StatusPill>{meta ? <span className={`font-mono text-[0.68rem] uppercase tracking-[0.16em] ${dark ? "text-slate-500" : "text-slate-400"}`}>{meta}</span> : null}</div>
      <h3 className={`mt-4 text-lg font-semibold tracking-[-0.02em] ${dark ? "text-white" : "text-slate-950"}`}>{title}</h3>
      <p className={`mt-3 text-sm leading-7 ${dark ? "text-slate-300" : "text-slate-600"}`}>{body}</p>
    </article>
  );
}

export function FamilyJourneyStepper({ steps }: { steps: Array<{ label: string; title: string; body: string; tone?: Tone }> }) {
  return (
    <div className="grid gap-4 lg:grid-cols-4">
      {steps.map((step, index) => (
        <article key={step.title} className="relative overflow-hidden rounded-[1.75rem] border border-white/75 bg-white/82 p-5 shadow-xl shadow-slate-950/[0.05] backdrop-blur">
          <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full bg-cyan-200/30" />
          <div className="relative flex items-center justify-between"><StatusPill tone={step.tone || "cyan"} compact>{step.label}</StatusPill><span className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-950 text-sm font-semibold text-white">{index + 1}</span></div>
          <h3 className="relative mt-5 text-lg font-semibold tracking-[-0.03em] text-slate-950">{step.title}</h3>
          <p className="relative mt-3 text-sm leading-7 text-slate-600">{step.body}</p>
        </article>
      ))}
    </div>
  );
}

export function AssistantPanel({ title, body, items, dark = true }: { title: string; body: string; items: string[]; dark?: boolean }) {
  const panelClass = dark ? "border-cyan-300/20 bg-cyan-300/[0.07] text-white" : "border-cyan-200 bg-white/82 text-slate-950";
  return (
    <aside className={`min-w-0 overflow-hidden rounded-[2rem] border p-5 shadow-2xl backdrop-blur-xl ${panelClass}`}>
      <StatusPill tone="cyan" compact dark={dark}>AI copilot</StatusPill>
      <h3 className={`mt-4 text-xl font-semibold tracking-[-0.035em] ${dark ? "text-white" : "text-slate-950"}`}>{title}</h3>
      <p className={`mt-3 text-sm leading-7 ${dark ? "text-slate-300" : "text-slate-600"}`}>{body}</p>
      <div className="mt-5 grid gap-3">{items.map((item) => <div key={item} className={`rounded-2xl border p-3 text-sm leading-6 ${dark ? "border-white/10 bg-slate-950/35 text-slate-200" : "border-slate-100 bg-slate-50/80 text-slate-700"}`}>{item}</div>)}</div>
    </aside>
  );
}

export function DigitalTwinLab({ locale }: { locale: "en" | "ka" }) {
  const isKa = locale === "ka";
  const layers = [
    { name: isKa ? "MRI T2/FLAIR ზონა" : "MRI T2/FLAIR region", value: "78%", tone: "cyan" as Tone },
    { name: isKa ? "Motor pathway signal" : "Motor pathway signal", value: "64%", tone: "emerald" as Tone },
    { name: isKa ? "Inflammation overlay" : "Inflammation overlay", value: "42%", tone: "rose" as Tone },
    { name: isKa ? "Sleep recovery trend" : "Sleep recovery trend", value: "56%", tone: "violet" as Tone },
  ];
  const evidence = [
    isKa ? "დაკავშირება: თერაპიის ინტენსივობა ↔ motor learning" : "Link: therapy intensity ↔ motor learning",
    isKa ? "ჰიპოთეზა: sleep quality გავლენას ახდენს plasticity window-ზე" : "Hypothesis: sleep quality affects plasticity window",
    isKa ? "ექიმის კითხვა: რომელი სიგნალია actionable ახლა?" : "Clinician question: which signal is actionable now?",
  ];

  return (
    <section className="grid gap-4 xl:grid-cols-[0.8fr_1.55fr_0.85fr]">
      <DarkGlassPanel>
        <SectionHeader dark eyebrow={isKa ? "Layer controls" : "Layer controls"} title={isKa ? "MRI და კლინიკური ფენები" : "MRI and clinical layers"} subtitle={isKa ? "Mockup-ის მარცხენა rail: ყველა ფენა ჩანს confidence მაჩვენებლით." : "Mockup left rail: every layer remains visible with confidence."} />
        <div className="mt-5 grid gap-3">{layers.map((layer) => <div key={layer.name} className="rounded-2xl border border-white/10 bg-slate-950/35 p-4"><div className="flex items-center justify-between gap-3"><span className="text-sm font-medium text-slate-100">{layer.name}</span><StatusPill tone={layer.tone} compact dark>{layer.value}</StatusPill></div><div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-cyan-300" style={{ width: layer.value }} /></div></div>)}</div>
      </DarkGlassPanel>

      <div className="relative min-h-[34rem] overflow-hidden rounded-[2.25rem] border border-cyan-300/20 bg-slate-950 shadow-[0_0_100px_rgba(34,211,238,0.13)]">
        <Image src={GENERATED_BRAIN_IMAGE} alt="Generated translucent digital twin brain visualization" fill priority sizes="(min-width: 1280px) 52vw, 100vw" className="object-cover object-center opacity-95" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_45%,transparent_44%,rgba(2,6,23,0.36)_78%),linear-gradient(180deg,rgba(2,6,23,0.08),rgba(2,6,23,0.18)_52%,rgba(2,6,23,0.38))]" />
        <div className="absolute left-8 right-8 top-8 flex items-center justify-between"><StatusPill tone="slate" dark>digital twin lab</StatusPill><StatusPill tone="amber" dark>prototype only</StatusPill></div>
        <div className="absolute left-[30%] top-[36%] rounded-full border border-cyan-200/40 bg-cyan-200/15 px-3 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-cyan-100 backdrop-blur">T2</div>
        <div className="absolute right-[23%] top-[48%] rounded-full border border-emerald-200/40 bg-emerald-200/15 px-3 py-1 text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-emerald-100 backdrop-blur">motor</div>
        <div className="absolute bottom-8 left-8 right-8 rounded-3xl border border-white/10 bg-white/[0.055] p-4 backdrop-blur-xl"><div className="flex items-center justify-between text-xs uppercase tracking-[0.16em] text-slate-400"><span>scan 01</span><span>scan 02</span><span>scan 03</span><span>next review</span></div><div className="mt-3 h-2 rounded-full bg-white/10"><div className="h-2 w-[62%] rounded-full bg-cyan-300 shadow-[0_0_20px_rgba(103,232,249,0.7)]" /></div></div>
      </div>

      <DarkGlassPanel>
        <SectionHeader dark eyebrow={isKa ? "Evidence links" : "Evidence links"} title={isKa ? "სიგნალი → წყარო → კითხვა" : "Signal → source → question"} subtitle={isKa ? "Mockup-ის მარჯვენა evidence panel უკავშირებს brain region-ს კვლევასა და action item-ს." : "The right evidence panel links brain regions with research and action items."} />
        <div className="mt-5 grid gap-3">{evidence.map((item) => <div key={item} className="rounded-2xl border border-white/10 bg-slate-950/35 p-4 text-sm leading-6 text-slate-200">{item}</div>)}</div>
      </DarkGlassPanel>
    </section>
  );
}

export function DemoDataNotice({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-3xl border border-cyan-200 bg-cyan-50/80 p-4 text-sm leading-7 text-cyan-950 shadow-lg shadow-cyan-950/[0.04]"><strong className="block font-semibold">{title}</strong><span className="text-cyan-900/80">{body}</span></div>
  );
}
