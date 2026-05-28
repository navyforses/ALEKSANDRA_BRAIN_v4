"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Bell,
  BookOpen,
  Brain,
  CalendarClock,
  ChevronRight,
  CircleHelp,
  Database,
  FileText,
  FlaskConical,
  HeartPulse,
  Home,
  Info,
  Library,
  LifeBuoy,
  LockKeyhole,
  Network,
  PanelRight,
  Radio,
  Settings,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  UsersRound,
  Zap,
  type LucideIcon,
} from "lucide-react";
import LanguageSwitcher from "@/components/LanguageSwitcher";

type Locale = "en" | "ka";
type NavItem = { href: string; labelKa: string; labelEn: string; icon: LucideIcon; metric?: string };
type NavGroup = { titleKa: string; titleEn: string; items: NavItem[] };

const navGroups: NavGroup[] = [
  {
    titleKa: "საკომანდო ცენტრი",
    titleEn: "Command Center",
    items: [
      { href: "/", labelKa: "მთავარი", labelEn: "Command Center", icon: Home, metric: "ცოცხ." },
      { href: "/dashboard", labelKa: "კვლევის ტვინი", labelEn: "Living Research Brain", icon: Brain, metric: "12.8k" },
      { href: "/evidence-map", labelKa: "მტკიცებულებები", labelEn: "Evidence Map", icon: Network, metric: "742" },
      { href: "/hypotheses", labelKa: "ჰიპოთეზები", labelEn: "Hypothesis Validation", icon: FlaskConical, metric: "173" },
      { href: "/therapies", labelKa: "თერაპიები", labelEn: "Therapy Candidates", icon: Stethoscope, metric: "28" },
      { href: "/timeline", labelKa: "დროითი ხაზი", labelEn: "Timeline", icon: CalendarClock, metric: "2025+" },
    ],
  },
  {
    titleKa: "მონაცემთა ქსელი",
    titleEn: "Data Network",
    items: [
      { href: "/cohorts", labelKa: "კოჰორტები", labelEn: "Study Cohorts", icon: UsersRound, metric: "14" },
      { href: "/data-integrations", labelKa: "მონაცემები", labelEn: "Data & Integrations", icon: Database, metric: "36" },
      { href: "/papers", labelKa: "პუბლიკაციები", labelEn: "Publications", icon: BookOpen, metric: "8.1k" },
      { href: "/alerts", labelKa: "სიგნალები", labelEn: "Alerts & Updates", icon: Bell, metric: "+9" },
    ],
  },
  {
    titleKa: "ოპერაციები",
    titleEn: "Operations",
    items: [
      { href: "/resources", labelKa: "შეჯამება", labelEn: "Family-safe summary", icon: Library, metric: "მზად" },
      { href: "/how-it-works", labelKa: "საზღვარი", labelEn: "Clinical boundary", icon: ShieldCheck, metric: "ჩართ." },
      { href: "/support", labelKa: "მხარდაჭერა", labelEn: "Support", icon: LifeBuoy, metric: "24/7" },
      { href: "/audit", labelKa: "აუდიტის კვალი", labelEn: "Audit Trail", icon: FileText, metric: "219" },
      { href: "/settings", labelKa: "პარამეტრები", labelEn: "Settings", icon: Settings, metric: "კონფ." },
    ],
  },
];

function normalizePath(pathname: string, locale: Locale) {
  const withoutLocale = pathname.replace(new RegExp(`^/${locale}`), "") || "/";
  return withoutLocale === "" ? "/" : withoutLocale;
}

function localizedHref(locale: Locale, href: string) {
  return `/${locale}${href === "/" ? "" : href}`;
}

function isActive(current: string, href: string) {
  if (href === "/") return current === "/";
  return current === href || current.startsWith(`${href}/`);
}

const assistantActions = [
  { icon: FileText, titleKa: "მტკიცებულების ბრიფი", textKa: "ბოლო წყაროების მოკლე შეჯამება", titleEn: "Evidence brief", textEn: "Summarize the last 24h source changes" },
  { icon: FlaskConical, titleKa: "ჰიპოთეზა", textKa: "მხარდაჭერა და საწინააღმდეგო სიგნალები", titleEn: "Validate hypothesis", textEn: "Evidence level and counter-signals" },
  { icon: HeartPulse, titleKa: "თერაპიები", textKa: "რისკი, ფაზა და სტატუსი", titleEn: "Therapy pipeline", textEn: "Candidate risk, phase and status" },
  { icon: Sparkles, titleKa: "კვლევის ბრიფი", textKa: "მოკლე და უსაფრთხო ანგარიში", titleEn: "Generate research brief", textEn: "Family-safe short report" },
];

export default function PortalFrame({ children, locale }: { children: ReactNode; locale: Locale }) {
  const pathname = usePathname();
  const currentPath = normalizePath(pathname || "/", locale);
  const isKa = locale === "ka";

  return (
    <div className="min-h-screen overflow-hidden bg-[#020916] text-slate-100 selection:bg-cyan-400/30 selection:text-cyan-50">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_35%_-8%,rgba(37,99,235,0.35),transparent_28%),radial-gradient(circle_at_74%_8%,rgba(168,85,247,0.24),transparent_30%),radial-gradient(circle_at_88%_66%,rgba(20,184,166,0.18),transparent_32%),linear-gradient(135deg,#020916_0%,#061124_48%,#020814_100%)]" />
      <div className="pointer-events-none fixed inset-0 opacity-[0.18] [background-image:linear-gradient(rgba(96,165,250,0.2)_1px,transparent_1px),linear-gradient(90deg,rgba(96,165,250,0.2)_1px,transparent_1px)] [background-size:44px_44px]" />
      <div className="pointer-events-none fixed left-[15rem] top-0 hidden h-full w-px bg-cyan-400/20 shadow-[0_0_36px_rgba(34,211,238,0.55)] xl:block" />

      <div className="relative grid min-h-screen xl:grid-cols-[15rem_minmax(0,1fr)_21rem]">
        <aside className="border-r border-cyan-300/10 bg-[#031023]/88 px-3 py-4 shadow-2xl shadow-black/40 backdrop-blur-2xl xl:sticky xl:top-0 xl:h-screen xl:overflow-y-auto">
          <Link href={localizedHref(locale, "/")} className="group flex items-center gap-3 rounded-2xl border border-cyan-300/10 bg-white/[0.035] px-3 py-3 transition hover:border-cyan-300/35 hover:bg-cyan-300/[0.07]">
            <span className="relative grid h-11 w-11 place-items-center rounded-2xl border border-cyan-300/25 bg-cyan-400/10 text-cyan-200 shadow-[0_0_28px_rgba(34,211,238,0.16)]">
              <Brain className="h-6 w-6" />
              <span className="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-emerald-300 shadow-[0_0_16px_rgba(52,211,153,0.85)]" />
            </span>
            <span className="min-w-0">
              <span className="block truncate text-[0.82rem] font-semibold tracking-normal text-white">Aleksandra Brain</span>
              <span className="block text-[0.67rem] font-medium text-cyan-200/70">{isKa ? "კვლევის ტვინი" : "Living Research Brain"}</span>
            </span>
          </Link>

          <nav aria-label={isKa ? "მთავარი მენიუ" : "Primary menu"} className="mt-5 space-y-5">
            {navGroups.map((group) => (
              <section key={group.titleEn}>
                <p className="px-3 text-[0.68rem] font-semibold leading-5 tracking-normal text-blue-200/42">{isKa ? group.titleKa : group.titleEn}</p>
                <div className="mt-2 space-y-1">
                  {group.items.map((item) => {
                    const Icon = item.icon;
                    const active = isActive(currentPath, item.href);
                    return (
                      <Link
                        key={item.href}
                        href={localizedHref(locale, item.href)}
                        className={`group relative flex items-center gap-3 rounded-2xl px-3 py-2.5 text-[0.82rem] font-semibold transition duration-300 ${
                          active
                            ? "border border-cyan-300/25 bg-blue-500/18 text-cyan-50 shadow-[inset_0_0_0_1px_rgba(34,211,238,0.12),0_0_28px_rgba(37,99,235,0.2)]"
                            : "border border-transparent text-slate-300/78 hover:border-cyan-300/15 hover:bg-white/[0.045] hover:text-white"
                        }`}
                      >
                        <Icon className={`h-4.5 w-4.5 shrink-0 ${active ? "text-cyan-200" : "text-blue-200/60 group-hover:text-cyan-200"}`} />
                        <span className="min-w-0 flex-1 truncate">{isKa ? item.labelKa : item.labelEn}</span>
                        {item.metric ? <span className={`rounded-full px-1.5 py-0.5 text-[0.58rem] ${active ? "bg-cyan-300/15 text-cyan-100" : "bg-white/[0.055] text-blue-100/50"}`}>{item.metric}</span> : null}
                        {active ? <span className="absolute left-0 top-1/2 h-7 w-0.5 -translate-y-1/2 rounded-full bg-cyan-300 shadow-[0_0_14px_rgba(34,211,238,0.9)]" /> : null}
                      </Link>
                    );
                  })}
                </div>
              </section>
            ))}
          </nav>

          <div className="mt-5 rounded-3xl border border-cyan-300/16 bg-cyan-300/[0.055] p-4 text-sm text-cyan-50 shadow-[0_0_36px_rgba(8,145,178,0.12)]">
            <div className="flex items-center gap-2 font-semibold">
              <ShieldCheck className="h-5 w-5 text-cyan-200" />
              {isKa ? "კლინიკური საზღვარი" : "Clinical boundary"}
            </div>
            <div className="mt-3 grid gap-2 text-[0.72rem] text-cyan-100/72">
              <div className="flex items-center gap-2"><LockKeyhole className="h-3.5 w-3.5 text-amber-200" />{isKa ? "არა სამედიცინო რჩევა" : "Not medical advice"}</div>
              <div className="flex items-center gap-2"><BookOpen className="h-3.5 w-3.5 text-blue-200" />{isKa ? "კვლევითი მტკიცებულება" : "Research evidence"}</div>
              <div className="flex items-center gap-2"><UsersRound className="h-3.5 w-3.5 text-emerald-200" />{isKa ? "ექიმი იღებს გადაწყვეტილებას" : "Doctors decide treatment"}</div>
            </div>
          </div>
        </aside>

        <div className="min-w-0 border-r border-cyan-300/10">
          <header className="sticky top-0 z-40 border-b border-cyan-300/10 bg-[#041126]/78 px-4 py-3 backdrop-blur-2xl sm:px-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="inline-flex items-center gap-2 rounded-full border border-emerald-300/20 bg-emerald-300/8 px-3 py-1.5 text-[0.7rem] font-semibold text-emerald-100">
                  <Radio className="h-3.5 w-3.5 animate-pulse text-emerald-300" /> {isKa ? "მონაცემთა ნაკადი" : "Live data"}
                </span>
                <span className="hidden text-xs font-medium text-blue-100/50 sm:inline">{isKa ? "განახლება ყოველ 8 წამში" : "Refresh every 8 seconds"}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="hidden items-center gap-2 rounded-2xl border border-cyan-300/12 bg-white/[0.035] px-3 py-2 text-xs font-semibold text-cyan-100 md:inline-flex">
                  <Stethoscope className="h-4 w-4 text-cyan-200" /> {isKa ? "ექიმის რეჟიმი" : "Doctor Mode"}
                </span>
                <LanguageSwitcher />
              </div>
            </div>
          </header>
          <main id="main" tabIndex={-1} className="min-h-[calc(100vh-4rem)] p-3 sm:p-5">
            {children}
          </main>
        </div>

        <aside className="bg-[#031023]/76 px-3 py-4 shadow-2xl shadow-black/35 backdrop-blur-2xl xl:sticky xl:top-0 xl:h-screen xl:overflow-y-auto">
          <div className="rounded-[1.6rem] border border-cyan-300/14 bg-white/[0.045] p-4 shadow-[0_0_42px_rgba(37,99,235,0.12)]">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="grid h-10 w-10 place-items-center rounded-2xl border border-cyan-300/20 bg-cyan-300/10 text-cyan-200 shadow-[0_0_24px_rgba(34,211,238,0.15)]">
                  <Brain className="h-5 w-5" />
                </span>
                <div>
                  <h2 className="text-sm font-semibold tracking-normal text-white">{isKa ? "კვლევის ასისტენტი" : "BRAIN assistant"}</h2>
                  <p className="text-[0.68rem] text-cyan-100/55">{isKa ? "კვლევის კოპილოტი" : "research copilot"}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 text-blue-100/50">
                <PanelRight className="h-4 w-4" />
                <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_16px_rgba(52,211,153,0.9)]" />
              </div>
            </div>

            <div className="mt-4 rounded-2xl border border-cyan-300/12 bg-[#081a34] p-4 text-[0.82rem] leading-6 text-blue-100/78">
              {isKa
                ? "ვაკვირდები წყაროებს, ჰიპოთეზებს და თერაპიის კანდიდატებს. პასუხები კვლევითია და ექიმის გადაწყვეტილებას არ ცვლის."
                : "I monitor evidence flow, hypothesis support, therapy candidates, and source status. Responses are research-only and do not replace clinical judgment."}
            </div>

            <div className="mt-4 grid gap-2">
              {assistantActions.map((action) => {
                const Icon = action.icon;
                return (
                  <button key={action.titleEn} type="button" className="group flex items-center gap-3 rounded-2xl border border-cyan-300/10 bg-white/[0.035] px-3 py-3 text-left transition hover:border-cyan-300/35 hover:bg-cyan-300/[0.075]">
                    <span className="grid h-9 w-9 place-items-center rounded-xl bg-blue-500/12 text-cyan-200 ring-1 ring-cyan-300/10"><Icon className="h-4.5 w-4.5" /></span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-[0.82rem] font-semibold text-cyan-50">{isKa ? action.titleKa : action.titleEn}</span>
                      <span className="block truncate text-[0.68rem] text-blue-100/48">{isKa ? action.textKa : action.textEn}</span>
                    </span>
                    <ChevronRight className="h-4 w-4 text-blue-100/35 transition group-hover:translate-x-0.5 group-hover:text-cyan-200" />
                  </button>
                );
              })}
            </div>

            <div className="mt-4 rounded-2xl border border-purple-300/12 bg-purple-400/[0.055] p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-purple-100">
                <Zap className="h-4 w-4 text-purple-200" />
                {isKa ? "შემოთავაზებული კითხვები" : "Suggested prompts"}
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {(isKa ? ["კვლევები", "მიტოქონდრია", "ნეიროდაცვა", "ოჯახის ბრიფი"] : ["trials", "mitochondria", "neuroprotection", "family brief"]).map((prompt) => (
                  <span key={prompt} className="rounded-full border border-purple-200/14 bg-white/[0.035] px-3 py-1.5 text-[0.68rem] text-purple-100/72">{prompt}</span>
                ))}
              </div>
            </div>

            <label className="mt-4 flex items-center gap-2 rounded-2xl border border-cyan-300/16 bg-[#061832] px-3 py-2.5 text-sm text-blue-100/55">
              <span className="sr-only">{isKa ? "ჰკითხე ასისტენტს" : "Ask BRAIN assistant"}</span>
              <input className="min-w-0 flex-1 bg-transparent text-[0.8rem] outline-none placeholder:text-blue-100/36" placeholder={isKa ? "ჰკითხე ასისტენტს..." : "Ask BRAIN assistant..."} />
              <button type="button" className="grid h-8 w-8 place-items-center rounded-xl bg-cyan-400/16 text-cyan-200 transition hover:bg-cyan-400/25"><ChevronRight className="h-4 w-4" /></button>
            </label>

            <div className="mt-4 rounded-2xl border border-amber-200/14 bg-amber-200/[0.055] p-3 text-[0.68rem] leading-5 text-amber-100/72">
              <div className="flex items-center gap-2 font-semibold text-amber-100"><CircleHelp className="h-3.5 w-3.5" /> {isKa ? "კვლევისთვის" : "Research only"}</div>
              <p className="mt-1">{isKa ? "ასისტენტი კვლევით ინფორმაციას აწვდის და ექიმის შეფასებას არ ცვლის." : "BRAIN assistant provides research information and is not a substitute for clinical judgment."}</p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
