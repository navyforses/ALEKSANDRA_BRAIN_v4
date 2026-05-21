// Phase 6 locale-segmented layout — RESEARCH.md Pattern 2.
// Owns <html lang={locale}> + <body> so lang attribute is correct per locale.
// Validates URL locale via hasLocale(routing.locales, locale) → notFound() on miss.
// setRequestLocale(locale) enables static rendering for descendant pages.
// Source: https://next-intl.dev/docs/getting-started/app-router/with-i18n-routing
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { notFound } from "next/navigation";
import { NextIntlClientProvider, hasLocale } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import TopNav from "@/components/layout/TopNav";
import BrainPanel from "@/components/layout/BrainPanel";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import "../globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "ALEKSANDRA_BRAIN",
  description: "Pediatric HIE System Integrator",
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }
  setRequestLocale(locale);

  return (
    <html lang={locale} className={`${inter.variable} h-full antialiased`}>
      <body className="h-screen w-screen overflow-hidden bg-background text-foreground flex flex-col font-sans">
        <NextIntlClientProvider>
          <header className="h-[60px] flex-shrink-0 border-b border-slate-200 bg-white flex items-center justify-between px-4">
            <TopNav />
            <LanguageSwitcher />
          </header>

          <div className="flex flex-1 overflow-hidden">
            <main className="w-full md:w-[65%] h-full overflow-y-auto bg-background p-8">
              {children}
            </main>

            <aside className="hidden md:flex w-[35%] h-full border-l border-slate-200 bg-slate-50 flex-col">
              <BrainPanel />
            </aside>
          </div>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
