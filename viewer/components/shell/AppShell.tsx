"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import type { Locale } from "@/lib/seo";
import {
  IconBrain,
  IconBrief,
  IconHistory,
  IconPlus,
  IconResearch,
  IconToday,
  IconTrials,
  type IconComponent,
} from "@/components/shell/icons";
import { IntakeProvider, useIntake } from "@/components/shell/intake-context";
import IntakeOverlay from "@/components/intake/IntakeOverlay";
import LanguageToggle from "@/components/shell/LanguageToggle";
import ThemeToggle from "@/components/shell/ThemeToggle";

type NavKey = "today" | "research" | "brain" | "brief" | "history" | "trials";

const NAV: { key: NavKey; href: string; Icon: IconComponent }[] = [
  { key: "today", href: "/", Icon: IconToday },
  { key: "research", href: "/research", Icon: IconResearch },
  { key: "trials", href: "/research/trials", Icon: IconTrials },
  { key: "brain", href: "/brain", Icon: IconBrain },
  { key: "brief", href: "/brief", Icon: IconBrief },
  { key: "history", href: "/history", Icon: IconHistory },
];

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function Wordmark() {
  return (
    <Link
      href="/"
      className="group flex items-center gap-2.5 focus:outline-none"
      aria-label="ALEKSANDRA BRAIN — home"
    >
      <span
        aria-hidden
        className="dot-breathe h-2 w-2 rounded-full bg-accent"
        title="working"
      />
      <span className="leading-none">
        <span className="block text-[0.62rem] font-medium uppercase tracking-[0.32em] text-faint">
          Aleksandra
        </span>
        <span className="block font-serif text-lg leading-tight tracking-tight text-ink group-hover:text-accent-ink">
          BRAIN
        </span>
      </span>
    </Link>
  );
}

function IntakeButton({ label }: { label: string }) {
  const { setOpen } = useIntake();
  return (
    <button
      type="button"
      onClick={() => setOpen(true)}
      className="inline-flex items-center gap-1.5 rounded-full bg-accent px-3.5 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-accent-ink focus:outline-none"
    >
      <IconPlus className="h-4 w-4" />
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}

function DesktopNav({ pathname }: { pathname: string }) {
  const t = useTranslations("Shell");
  return (
    <nav
      aria-label={t("nav.label")}
      className="hidden items-center gap-1 md:flex"
    >
      {NAV.map(({ key, href, Icon }) => {
        const active = isActive(pathname, href);
        return (
          <Link
            key={key}
            href={href}
            aria-current={active ? "page" : undefined}
            className={`group inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm transition-colors ${
              active
                ? "bg-accent-soft text-accent-ink"
                : "text-muted hover:text-ink"
            }`}
          >
            <Icon className={`h-4 w-4 ${active ? "text-accent" : "text-faint group-hover:text-muted"}`} />
            {t(`nav.${key}`)}
          </Link>
        );
      })}
    </nav>
  );
}

function MobileNav({ pathname }: { pathname: string }) {
  const t = useTranslations("Shell");
  return (
    <nav
      aria-label={t("nav.label")}
      className="no-print fixed inset-x-0 bottom-0 z-40 border-t border-line bg-paper/95 backdrop-blur md:hidden"
    >
      <div className="mx-auto flex max-w-5xl items-stretch justify-between px-2">
        {NAV.map(({ key, href, Icon }) => {
          const active = isActive(pathname, href);
          return (
            <Link
              key={key}
              href={href}
              aria-current={active ? "page" : undefined}
              className={`flex flex-1 flex-col items-center gap-1 py-2.5 text-[0.62rem] font-medium transition-colors ${
                active ? "text-accent-ink" : "text-faint"
              }`}
            >
              <Icon className="h-5 w-5" />
              {t(`nav.${key}`)}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

function ShellInner({ locale, children }: { locale: Locale; children: ReactNode }) {
  const t = useTranslations("Shell");
  const pathname = usePathname();

  return (
    <div className="flex min-h-dvh flex-col pb-16 md:pb-0">
      <a className="skip-link" href="#main">
        {t("skipToContent")}
      </a>

      <header className="no-print sticky top-0 z-30 border-b border-line bg-paper/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between gap-3 px-5 sm:px-8">
          <Wordmark />
          <DesktopNav pathname={pathname} />
          <div className="flex items-center gap-2">
            <IntakeButton label={t("intake")} />
            <LanguageToggle />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main id="main" tabIndex={-1} className="mx-auto w-full max-w-5xl flex-1 px-5 py-10 sm:px-8 sm:py-14">
        {children}
      </main>

      <footer className="no-print border-t border-line">
        <div className="mx-auto max-w-5xl px-5 py-6 sm:px-8">
          <p className="text-xs leading-relaxed text-faint">
            {t("privacy")}
          </p>
          <p className="mt-1 text-xs leading-relaxed text-faint">
            {t("clinician")}
          </p>
        </div>
      </footer>

      <MobileNav pathname={pathname} />
      <IntakeOverlay locale={locale} />
    </div>
  );
}

export default function AppShell({
  locale,
  children,
}: {
  locale: Locale;
  children: ReactNode;
}) {
  return (
    <IntakeProvider>
      <ShellInner locale={locale}>{children}</ShellInner>
    </IntakeProvider>
  );
}
