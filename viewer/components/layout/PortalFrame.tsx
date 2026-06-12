"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import LanguageSwitcher from "@/components/LanguageSwitcher";

type Locale = "en" | "ka";
type NavItem = { href: string; labelKa: string; labelEn: string; helperKa: string; helperEn: string };

const primaryNav: NavItem[] = [
  { href: "/", labelKa: "დღეს", labelEn: "Today", helperKa: "კვირის რეზიუმე და შეტანა", helperEn: "Weekly brief & upload" },
  { href: "/library", labelKa: "ბიბლიოთეკა", labelEn: "Library", helperKa: "სტატიები და ჰიპოთეზები", helperEn: "Papers and hypotheses" },
  { href: "/brain", labelKa: "ტვინი", labelEn: "Private Brain", helperKa: "ლოკალური MRI მნახველი", helperEn: "Local MRI viewer" },
  { href: "/journal", labelKa: "აქტივობა", labelEn: "Journal", helperKa: "ქმედებები და ჟურნალი", helperEn: "Audit & actions" },
  { href: "/settings", labelKa: "პარამეტრები", labelEn: "Settings", helperKa: "ენის გადართვა და სისტემა", helperEn: "Language & system config" },
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

  const [darkMode, setDarkMode] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(true);

  // Initialize theme from localStorage or default dark/light
  useEffect(() => {
    const root = window.document.documentElement;
    const isDark = localStorage.getItem("theme") === "dark" || 
      (!("theme" in localStorage) && window.matchMedia("(prefers-color-scheme: dark)").matches);
    
    setDarkMode(isDark);
    if (isDark) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, []);

  const toggleTheme = () => {
    const root = window.document.documentElement;
    if (darkMode) {
      root.classList.remove("dark");
      localStorage.setItem("theme", "light");
      setDarkMode(false);
    } else {
      root.classList.add("dark");
      localStorage.setItem("theme", "dark");
      setDarkMode(true);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-150 selection:bg-neutral-200/50 dark:selection:bg-neutral-800/50">
      <div className="relative mx-auto grid min-h-screen max-w-[1440px] grid-cols-1 border-x border-border md:grid-cols-[16rem_minmax(0,1fr)] lg:grid-cols-[16rem_minmax(0,1fr)_20rem]">
        
        {/* Navigation Sidebar */}
        <aside className="border-b border-border bg-panel/30 px-5 py-6 md:sticky md:top-0 md:h-screen md:border-b-0 md:border-r md:overflow-y-auto">
          <div className="mb-8 flex items-baseline justify-between">
            <Link href={localizedHref(locale, "/")} className="group block focus:outline-none">
              <span className="block text-xs font-bold uppercase tracking-[0.25em] text-foreground/40">ALEKSANDRA</span>
              <span className="block text-lg font-bold tracking-tight text-foreground group-hover:underline">BRAIN</span>
            </Link>
            <span className="rounded border border-border px-1.5 py-0.5 text-[0.65rem] font-semibold text-foreground/50">
              v4.0
            </span>
          </div>

          <div className="mb-6 border-l border-medical-orange/30 pl-3 py-1 text-[0.72rem] leading-relaxed text-muted-foreground">
            <div className="font-semibold text-foreground/80 flex items-center gap-1.5">
              <span>●</span>
              {isKa ? "მხოლოდ კვლევისთვის" : "Research only"}
            </div>
            <p className="mt-1">
              {isKa ? "პორტალი არ სვამს დიაგნოზს. გადაწყვეტილებებს იღებს ექიმი." : "This portal does not diagnose. Clinicians make all decisions."}</p>
          </div>

          <nav aria-label={isKa ? "მთავარი მენიუ" : "Primary menu"} className="space-y-1">
            <p className="px-1 py-1.5 text-[0.68rem] font-bold uppercase tracking-wider text-muted-foreground/60">
              {isKa ? "სარჩევი" : "Contents"}
            </p>
            {primaryNav.map((item) => {
              const active = isActive(currentPath, item.href);
              return (
                <Link
                  key={item.href}
                  href={localizedHref(locale, item.href)}
                  className={`group block rounded-md px-3 py-2 text-left transition duration-150 focus:outline-none focus:ring-1 focus:ring-ring ${
                    active
                      ? "bg-panel border border-border font-medium text-foreground"
                      : "border border-transparent text-muted-foreground hover:text-foreground hover:bg-panel/50"
                  }`}
                >
                  <span className="block text-sm leading-normal">{isKa ? item.labelKa : item.labelEn}</span>
                  <span className="block text-[0.68rem] leading-relaxed text-muted-foreground/75 group-hover:text-muted-foreground">
                    {isKa ? item.helperKa : item.helperEn}
                  </span>
                </Link>
              );
            })}
          </nav>
        </aside>

        {/* Middle Main Content */}
        <div className="min-w-0 border-border md:border-r">
          <header className="sticky top-0 z-40 border-b border-border bg-background/90 px-6 py-3.5 backdrop-blur-md">
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <h2 className="text-sm font-semibold text-foreground tracking-tight">
                  {isKa ? "კვლევითი სამუშაო რვეული" : "Clinical Research Notebook"}
                </h2>
              </div>
              <div className="flex items-center gap-4">
                <button
                  type="button"
                  onClick={toggleTheme}
                  className="text-xs text-muted-foreground hover:text-foreground font-mono focus:outline-none"
                  aria-label={isKa ? "თემის გადართვა" : "Toggle theme"}
                >
                  {darkMode ? (isKa ? "[დღე]" : "[Light]") : (isKa ? "[ღამე]" : "[Dark]")}
                </button>
                <LanguageSwitcher />
              </div>
            </div>
          </header>

          <main id="main" tabIndex={-1} className="min-h-[calc(100vh-4.5rem)] p-6 sm:p-8">
            {children}
          </main>
        </div>

        {/* Right Research Assistant Sidebar */}
        <aside className={`bg-panel/10 p-5 lg:block lg:sticky lg:top-0 lg:h-screen lg:overflow-y-auto ${assistantOpen ? "block border-t border-border lg:border-t-0" : "hidden"}`}>
          <div className="flex items-center justify-between border-b border-border pb-3 mb-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              {isKa ? "ასისტენტი" : "Assistant"}
            </h3>
            <button
              type="button"
              onClick={() => setAssistantOpen(false)}
              className="text-xs text-muted-foreground hover:text-foreground lg:hidden focus:outline-none"
            >
              {isKa ? "[დახურვა]" : "[Close]"}
            </button>
          </div>

          <div className="space-y-4">
            <div className="rounded border border-border bg-panel/20 p-4">
              <p className="text-xs leading-relaxed text-muted-foreground">
                {isKa 
                  ? "სისტემა მუდმივად აანალიზებს ახალ ლიტერატურას. თუ შეამჩნევს რელევანტურ კავშირს, აქ გამოჩნდება რჩევები."
                  : "The system monitors scientific literature. When it finds relevant connections, suggestions will appear here."
                }
              </p>
              <p className="mt-3 text-[0.68rem] text-medical-orange font-semibold">
                {isKa ? "● მონაცემი ჯერ არ არის" : "● No new signals"}
              </p>
            </div>

            <div className="rounded border border-border p-4 bg-background">
              <h4 className="text-xs font-bold text-foreground">
                {isKa ? "უსაფრთხოების წესები" : "Privacy & Safety"}
              </h4>
              <ul className="mt-2 space-y-2 text-[0.72rem] leading-relaxed text-muted-foreground list-disc pl-4">
                <li>{isKa ? "MRI მონაცემები არასოდეს ტოვებს თქვენს ბრაუზერს." : "MRI data never leaves your browser."}</li>
                <li>{isKa ? "ყველა ჰიპოთეზას აქვს წყარო — AI არაფერს იგონებს." : "Every hypothesis carries provenance — no fabrications."}</li>
                <li>{isKa ? "ნებისმიერი ქმედების გაუქმება შესაძლებელია 24 საათში." : "All database writes have a 24-hour safety undo net."}</li>
              </ul>
            </div>
          </div>
        </aside>

        {/* Floating open assistant link when collapsed */}
        {!assistantOpen && (
          <button
            type="button"
            onClick={() => setAssistantOpen(true)}
            className="fixed bottom-4 right-4 z-50 rounded-full border border-border bg-panel px-4 py-2.5 text-xs font-bold shadow-sm lg:hidden focus:outline-none"
          >
            {isKa ? "ასისტენტის გახსნა" : "Open Assistant"}
          </button>
        )}

      </div>
    </div>
  );
}
