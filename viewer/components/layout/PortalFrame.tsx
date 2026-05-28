"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ArrowRight,
  BookOpen,
  Brain,
  FileText,
  FlaskConical,
  Home,
  Info,
  Layers3,
  MessageSquareText,
  Scale,
  ShieldCheck,
  Stethoscope,
  type LucideIcon,
} from "lucide-react";
import LanguageSwitcher from "@/components/LanguageSwitcher";

type Locale = "en" | "ka";
type NavItem = { href: string; labelKa: string; labelEn: string; helperKa: string; helperEn: string; icon: LucideIcon };

type AssistantAction = {
  titleKa: string;
  titleEn: string;
  textKa: string;
  textEn: string;
  icon: LucideIcon;
};

const primaryNav: NavItem[] = [
  { href: "/", labelKa: "მთავარი", labelEn: "Home", helperKa: "მოკლე სურათი", helperEn: "Overview", icon: Home },
  { href: "/evidence-map", labelKa: "მტკიცებულება", labelEn: "Evidence", helperKa: "წყაროები და ხარისხი", helperEn: "Sources and grade", icon: BookOpen },
  { href: "/hypotheses", labelKa: "ჰიპოთეზები", labelEn: "Hypotheses", helperKa: "რა მოწმდება", helperEn: "What is being tested", icon: FlaskConical },
  { href: "/therapies", labelKa: "თერაპიები", labelEn: "Therapies", helperKa: "მხოლოდ კვლევითი საზღვრით", helperEn: "Research boundary", icon: Stethoscope },
  { href: "/brain", labelKa: "ტვინის რუკა", labelEn: "Brain map", helperKa: "კავშირები და კონტექსტი", helperEn: "Context and links", icon: Brain },
  { href: "/resources", labelKa: "ბრიფი", labelEn: "Brief", helperKa: "ექიმთან წასაღები", helperEn: "For the doctor visit", icon: FileText },
];

const secondaryLinks: NavItem[] = [
  { href: "/dashboard", labelKa: "სრული პანელი", labelEn: "Full panel", helperKa: "დეტალური ხედვა", helperEn: "Detailed view", icon: Layers3 },
  { href: "/how-it-works", labelKa: "საზღვარი", labelEn: "Boundary", helperKa: "როგორ წავიკითხოთ", helperEn: "How to read", icon: ShieldCheck },
];

const assistantActions: AssistantAction[] = [
  { titleKa: "შეჯამება", titleEn: "Summary", textKa: "მხოლოდ რეალური მონაცემით", textEn: "Only with real data", icon: MessageSquareText },
  { titleKa: "რისკები", titleEn: "Risks", textKa: "წყაროს არსებობისას", textEn: "Only if sources exist", icon: Scale },
  { titleKa: "ექიმთან კითხვა", titleEn: "Doctor question", textKa: "მონაცემიდან შედგენილი", textEn: "Built from available data", icon: Stethoscope },
  { titleKa: "შედარება", titleEn: "Compare", textKa: "მონაცემი არ არის", textEn: "No data available", icon: Layers3 },
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

function NavLink({ item, locale, active, compact = false }: { item: NavItem; locale: Locale; active: boolean; compact?: boolean }) {
  const Icon = item.icon;
  const isKa = locale === "ka";

  return (
    <Link
      href={localizedHref(locale, item.href)}
      className={`group flex items-center gap-3 rounded-2xl border px-3 py-3 text-left transition duration-200 focus:outline-none focus:ring-2 focus:ring-sky-300/70 ${
        active
          ? "border-sky-300/25 bg-sky-300/[0.08] text-white"
          : "border-transparent text-slate-300 hover:border-white/10 hover:bg-white/[0.045] hover:text-white"
      }`}
    >
      <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl border ${active ? "border-sky-300/25 bg-sky-300/10 text-sky-100" : "border-white/10 bg-white/[0.035] text-slate-400 group-hover:text-sky-100"}`}>
        <Icon className="h-4 w-4" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-semibold tracking-normal">{isKa ? item.labelKa : item.labelEn}</span>
        {!compact ? <span className="mt-0.5 block truncate text-[0.7rem] leading-4 text-slate-500">{isKa ? item.helperKa : item.helperEn}</span> : null}
      </span>
    </Link>
  );
}

export default function PortalFrame({ children, locale }: { children: ReactNode; locale: Locale }) {
  const pathname = usePathname();
  const currentPath = normalizePath(pathname || "/", locale);
  const isKa = locale === "ka";

  return (
    <div className="min-h-screen bg-[#08111f] text-slate-100 selection:bg-sky-300/25 selection:text-sky-50">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_20%_-10%,rgba(14,165,233,0.16),transparent_28%),linear-gradient(180deg,#08111f_0%,#0a1220_48%,#070d18_100%)]" />
      <div className="relative grid min-h-screen xl:grid-cols-[16rem_minmax(0,1fr)_20rem]">
        <aside className="border-b border-white/10 bg-[#091323]/90 px-4 py-4 backdrop-blur-xl xl:sticky xl:top-0 xl:h-screen xl:border-b-0 xl:border-r xl:overflow-y-auto">
          <Link href={localizedHref(locale, "/")} className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.035] px-3 py-3 transition hover:border-sky-300/25 hover:bg-white/[0.055]">
            <span className="grid h-10 w-10 place-items-center rounded-xl border border-sky-300/20 bg-sky-300/[0.08] text-sky-100">
              <Brain className="h-5 w-5" />
            </span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-semibold tracking-normal text-white">Aleksandra</span>
              <span className="block text-[0.72rem] leading-4 text-slate-400">{isKa ? "კვლევის ნავიგატორი" : "Research navigator"}</span>
            </span>
          </Link>

          <div className="mt-4 rounded-2xl border border-amber-200/15 bg-amber-200/[0.045] p-3 text-[0.74rem] leading-5 text-amber-50/80">
            <div className="flex items-center gap-2 font-semibold text-amber-50">
              <ShieldCheck className="h-4 w-4" />
              {isKa ? "მხოლოდ კვლევისთვის" : "Research only"}
            </div>
            <p className="mt-1">{isKa ? "საიტი არ სვამს დიაგნოზს და არ ცვლის ექიმის გადაწყვეტილებას." : "This portal does not diagnose or replace clinical judgment."}</p>
          </div>

          <nav aria-label={isKa ? "მთავარი მენიუ" : "Primary menu"} className="mt-5 space-y-1.5">
            {primaryNav.map((item) => (
              <NavLink key={item.href} item={item} locale={locale} active={isActive(currentPath, item.href)} />
            ))}
          </nav>

          <div className="mt-5 border-t border-white/10 pt-4">
            <p className="px-3 text-[0.68rem] font-semibold text-slate-500">{isKa ? "დამატებით" : "More"}</p>
            <div className="mt-2 space-y-1">
              {secondaryLinks.map((item) => (
                <NavLink key={item.href} item={item} locale={locale} active={isActive(currentPath, item.href)} compact />
              ))}
            </div>
          </div>
        </aside>

        <div className="min-w-0 border-white/10 xl:border-r">
          <header className="sticky top-0 z-40 border-b border-white/10 bg-[#091323]/82 px-4 py-3 backdrop-blur-xl sm:px-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs font-medium leading-5 text-slate-400">{isKa ? "მტკიცებულება → რისკი → ექიმთან კითხვა" : "Evidence → risk → doctor question"}</p>
                <p className="text-sm font-semibold text-white">{isKa ? "მოკლე გზა კვლევიდან უსაფრთხო საუბრამდე" : "A short path from research to safe discussion"}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="hidden rounded-full border border-emerald-300/20 bg-emerald-300/[0.06] px-3 py-1.5 text-xs font-semibold text-emerald-100 md:inline-flex">
                  {isKa ? "ექიმი იღებს გადაწყვეტილებას" : "Doctor decides"}
                </span>
                <LanguageSwitcher />
              </div>
            </div>
          </header>
          <main id="main" tabIndex={-1} className="min-h-[calc(100vh-4rem)] p-4 sm:p-6">
            {children}
          </main>
        </div>

        <aside className="bg-[#091323]/78 px-4 py-4 backdrop-blur-xl xl:sticky xl:top-0 xl:h-screen xl:overflow-y-auto">
          <section className="rounded-3xl border border-white/10 bg-white/[0.035] p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold text-white">{isKa ? "კვლევის ასისტენტი" : "Research assistant"}</h2>
                <p className="mt-1 text-[0.72rem] leading-5 text-slate-400">{isKa ? "პასუხი გამოჩნდება მხოლოდ მაშინ, როცა რეალური მონაცემი არსებობს." : "Answers appear only when real data exists."}</p>
              </div>
              <span className="grid h-9 w-9 place-items-center rounded-xl border border-sky-300/20 bg-sky-300/[0.07] text-sky-100">
                <MessageSquareText className="h-4 w-4" />
              </span>
            </div>

            <div className="mt-4 grid gap-2">
              {assistantActions.map((action) => {
                const Icon = action.icon;
                return (
                  <button key={action.titleEn} type="button" className="group flex items-center gap-3 rounded-2xl border border-white/10 bg-[#0c1728] px-3 py-3 text-left transition hover:border-sky-300/25 hover:bg-sky-300/[0.055] focus:outline-none focus:ring-2 focus:ring-sky-300/60">
                    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-white/10 bg-white/[0.035] text-slate-300 group-hover:text-sky-100">
                      <Icon className="h-4 w-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-semibold text-white">{isKa ? action.titleKa : action.titleEn}</span>
                      <span className="mt-0.5 block truncate text-[0.7rem] leading-4 text-slate-500">{isKa ? action.textKa : action.textEn}</span>
                    </span>
                    <ArrowRight className="h-4 w-4 text-slate-500 transition group-hover:translate-x-0.5 group-hover:text-sky-100" />
                  </button>
                );
              })}
            </div>

            <div className="mt-4 rounded-2xl border border-white/10 bg-[#0b1424] p-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-white">
                <Info className="h-4 w-4 text-sky-100" />
                {isKa ? "უსაფრთხო პასუხის წესი" : "Safe answer rule"}
              </div>
              <p className="mt-2 text-[0.72rem] leading-5 text-slate-400">
                {isKa ? "თუ წყაროთი დადასტურებული მონაცემი არ არსებობს, ინტერფეისი წერს: „მონაცემი არ არის“." : "If source-backed data does not exist, the interface says: “No data available.”"}
              </p>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
