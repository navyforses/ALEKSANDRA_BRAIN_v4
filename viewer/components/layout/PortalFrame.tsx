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
  HeartHandshake,
  Home,
  Info,
  Layers3,
  Library,
  LifeBuoy,
  Network,
  Settings,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  UsersRound,
  type LucideIcon,
} from "lucide-react";
import LanguageSwitcher from "@/components/LanguageSwitcher";

type Locale = "en" | "ka";
type NavItem = { href: string; labelKa: string; labelEn: string; icon: LucideIcon };

type NavGroup = { titleKa: string; titleEn: string; items: NavItem[] };

const navGroups: NavGroup[] = [
  {
    titleKa: "მთავარი სივრცე",
    titleEn: "Main workspace",
    items: [
      { href: "/", labelKa: "მთავარი პანელი", labelEn: "Dashboard", icon: Home },
      { href: "/dashboard", labelKa: "მართვის პანელი", labelEn: "Command Center", icon: Activity },
      { href: "/brain", labelKa: "ციფრული ტვინი", labelEn: "Living Brain", icon: Brain },
      { href: "/hypotheses", labelKa: "ჰიპოთეზები", labelEn: "Hypotheses", icon: FlaskConical },
      { href: "/therapies", labelKa: "თერაპიები", labelEn: "Therapies", icon: Stethoscope },
      { href: "/timeline", labelKa: "ქრონოლოგია", labelEn: "Timeline", icon: CalendarClock },
    ],
  },
  {
    titleKa: "კვლევა და წყაროები",
    titleEn: "Research and sources",
    items: [
      { href: "/evidence-map", labelKa: "მტკიცებულების რუკა", labelEn: "Evidence Map", icon: Network },
      { href: "/cohorts", labelKa: "კვლევის ჯგუფები", labelEn: "Study Cohorts", icon: UsersRound },
      { href: "/data-integrations", labelKa: "მონაცემები", labelEn: "Data & Integrations", icon: Database },
      { href: "/papers", labelKa: "პუბლიკაციები", labelEn: "Publications", icon: BookOpen },
      { href: "/alerts", labelKa: "განახლებები", labelEn: "Alerts", icon: Bell },
    ],
  },
  {
    titleKa: "ოჯახის მხარდაჭერა",
    titleEn: "Family support",
    items: [
      { href: "/resources", labelKa: "ოჯახის რესურსები", labelEn: "Family Resources", icon: Library },
      { href: "/how-it-works", labelKa: "როგორ მუშაობს", labelEn: "How This Works", icon: Info },
      { href: "/support", labelKa: "დახმარება", labelEn: "Help & Support", icon: LifeBuoy },
      { href: "/settings", labelKa: "პარამეტრები", labelEn: "Settings", icon: Settings },
      { href: "/audit", labelKa: "აუდიტი", labelEn: "Audit Trail", icon: FileText },
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

export default function PortalFrame({ children, locale }: { children: ReactNode; locale: Locale }) {
  const pathname = usePathname();
  const currentPath = normalizePath(pathname || "/", locale);
  const isKa = locale === "ka";

  return (
    <div className="min-h-screen bg-[#f6f9fc] text-slate-950">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_20%_0%,rgba(56,189,248,0.18),transparent_28%),radial-gradient(circle_at_88%_12%,rgba(16,185,129,0.15),transparent_24%),linear-gradient(135deg,#f8fafc_0%,#eef6ff_48%,#f8fafc_100%)]" />
      <div className="relative grid min-h-screen xl:grid-cols-[17rem_minmax(0,1fr)_21rem]">
        <aside className="border-r border-slate-200/80 bg-white/82 px-4 py-5 shadow-xl shadow-slate-950/[0.04] backdrop-blur-xl xl:sticky xl:top-0 xl:h-screen xl:overflow-y-auto">
          <Link href={localizedHref(locale, "/")} className="flex items-center gap-3 rounded-2xl px-2 py-2 transition hover:bg-cyan-50">
            <span className="grid h-11 w-11 place-items-center rounded-2xl border border-cyan-200 bg-cyan-50 text-cyan-800 shadow-inner">
              <Brain className="h-6 w-6" />
            </span>
            <span>
              <span className="block text-sm font-bold tracking-[-0.02em] text-slate-950">ALEKSANDRA_BRAIN</span>
              <span className="block text-xs font-medium text-slate-500">{isKa ? "ცოდნა, ერთად." : "Knowledge, together."}</span>
            </span>
          </Link>

          <nav aria-label={isKa ? "მთავარი მენიუ" : "Primary menu"} className="mt-7 space-y-6">
            {navGroups.map((group) => (
              <section key={group.titleEn}>
                <p className="px-3 text-[0.68rem] font-semibold uppercase tracking-[0.2em] text-slate-400">{isKa ? group.titleKa : group.titleEn}</p>
                <div className="mt-2 space-y-1">
                  {group.items.map((item) => {
                    const Icon = item.icon;
                    const active = isActive(currentPath, item.href);
                    return (
                      <Link
                        key={item.href}
                        href={localizedHref(locale, item.href)}
                        className={`group flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-semibold transition ${
                          active
                            ? "bg-blue-50 text-blue-800 shadow-sm ring-1 ring-blue-100"
                            : "text-slate-600 hover:bg-slate-50 hover:text-slate-950"
                        }`}
                      >
                        <Icon className={`h-5 w-5 ${active ? "text-blue-700" : "text-slate-500 group-hover:text-slate-800"}`} />
                        <span className="min-w-0 flex-1">{isKa ? item.labelKa : item.labelEn}</span>
                        {active ? <span className="h-2 w-2 rounded-full bg-blue-600" aria-hidden="true" /> : null}
                      </Link>
                    );
                  })}
                </div>
              </section>
            ))}
          </nav>

          <div className="mt-8 rounded-3xl border border-blue-100 bg-blue-50/80 p-4 text-sm text-blue-950">
            <div className="flex items-center gap-2 font-semibold">
              <ShieldCheck className="h-5 w-5 text-blue-700" />
              {isKa ? "უსაფრთხოების საზღვარი" : "Safety boundary"}
            </div>
            <p className="mt-3 leading-6 text-blue-900/80">
              {isKa
                ? "ჩვენ ვაწყობთ კვლევას და კითხვებს. მკურნალობის გადაწყვეტილებას იღებს თქვენი კლინიკური გუნდი."
                : "We organize research and questions. Your clinical team decides treatment."}
            </p>
            <Link href={localizedHref(locale, "/how-it-works")} className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-blue-800 hover:text-blue-950">
              {isKa ? "გაიგე მეტი" : "Learn more"} <ChevronRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </aside>

        <div className="min-w-0 border-r border-slate-200/80">
          <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/78 px-4 py-3 backdrop-blur-xl sm:px-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-slate-400">{isKa ? "ოჯახის ხედვა" : "Family View"}</p>
                <p className="text-sm font-semibold text-slate-800">{isKa ? "კვლევის მხარდაჭერა — ექიმი იღებს მკურნალობის გადაწყვეტილებას" : "Research support — doctors decide treatment"}</p>
              </div>
              <div className="flex items-center gap-3">
                <span className="hidden rounded-full border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-800 sm:inline-flex">{isKa ? "ექიმის რეჟიმი" : "Doctor Mode"}</span>
                <LanguageSwitcher />
              </div>
            </div>
          </header>
          <main id="main" tabIndex={-1} className="min-h-[calc(100vh-4rem)] p-4 sm:p-6">
            {children}
          </main>
        </div>

        <aside className="bg-white/72 px-4 py-5 shadow-xl shadow-slate-950/[0.04] backdrop-blur-xl xl:sticky xl:top-0 xl:h-screen xl:overflow-y-auto">
          <div className="rounded-[1.75rem] border border-slate-200 bg-white/92 p-4 shadow-xl shadow-slate-950/[0.05]">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="grid h-10 w-10 place-items-center rounded-2xl bg-cyan-50 text-cyan-800 ring-1 ring-cyan-100">
                  <Brain className="h-5 w-5" />
                </span>
                <div>
                  <h2 className="text-base font-bold tracking-[-0.02em] text-slate-950">{isKa ? "ჰკითხე Brain-ს" : "Ask the Brain"}</h2>
                  <p className="text-xs text-slate-500">{isKa ? "კვლევის ასისტენტი" : "Your research assistant"}</p>
                </div>
              </div>
              <Sparkles className="h-5 w-5 text-cyan-700" />
            </div>

            <div className="mt-5 rounded-2xl bg-blue-50 p-4 text-sm leading-6 text-slate-700">
              {isKa
                ? "შემიძლია კვლევის მარტივი ენით ახსნა, დღევანდელი სიახლის შეჯამება და ექიმთან დასასმელი კითხვების მომზადება."
                : "I can explain research in plain language, summarize what changed, and prepare questions for your doctor."}
            </div>

            <div className="mt-4 grid gap-2">
              {[
                isKa ? "რა შეიცვალა დღეს?" : "What changed today?",
                isKa ? "კვლევა მარტივად ამიხსენი" : "Explain a study simply",
                isKa ? "რა ვკითხოთ ექიმს?" : "What should we ask?",
                isKa ? "როგორ მუშაობს სისტემა?" : "How does this system work?",
              ].map((prompt) => (
                <button key={prompt} type="button" className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left text-sm font-medium text-slate-700 transition hover:border-cyan-200 hover:bg-cyan-50">
                  <span>{prompt}</span>
                  <ChevronRight className="h-4 w-4 text-slate-400" />
                </button>
              ))}
            </div>

            <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-950">
                <CircleHelp className="h-4 w-4 text-cyan-700" />
                {isKa ? "შემდეგი სასარგებლო კითხვები" : "Next useful questions"}
              </div>
              <ul className="mt-3 space-y-3 text-sm leading-6 text-slate-600">
                <li>{isKa ? "რომელი შედეგების დაკვირვებაა ყველაზე მნიშვნელოვანი?" : "Which outcomes matter most to track?"}</li>
                <li>{isKa ? "როგორ გავიგებთ, მუშაობს თუ არა რამე?" : "How will we know if something is working?"}</li>
                <li>{isKa ? "რომელი მხარდამჭერი სტრატეგია უნდა განვიხილოთ?" : "Which supportive strategies should we discuss?"}</li>
              </ul>
            </div>

            <div className="mt-5 rounded-2xl border border-blue-100 bg-blue-50 p-4 text-sm leading-6 text-blue-950">
              <div className="flex items-center gap-2 font-bold">
                <HeartHandshake className="h-4 w-4 text-blue-700" />
                {isKa ? "კვლევის მხარდაჭერა — მკურნალობას ექიმები წყვეტენ" : "Research support — doctors decide treatment"}
              </div>
              <p className="mt-2 text-blue-900/78">
                {isKa ? "ეს არ არის სამედიცინო რჩევა და არ ცვლის თქვენს კლინიკურ გუნდს." : "This is not medical advice and does not replace your care team."}
              </p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
