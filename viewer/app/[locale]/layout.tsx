import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { notFound } from "next/navigation";
import { NextIntlClientProvider, hasLocale } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import TopNav from "@/components/layout/TopNav";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import { buildPageMetadata, type Locale } from "@/lib/seo";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(locale, "home");
}

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
  const isKa = locale === "ka";

  return (
    <html lang={locale} className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-screen bg-slate-950 text-foreground font-sans">
        <NextIntlClientProvider>
          <a className="skip-link" href="#main">
            {isKa ? "გადასვლა მთავარ კონტენტზე" : "Skip to main content"}
          </a>
          <header className="sticky top-0 z-50 border-b border-white/10 bg-slate-950/88 px-4 py-3 shadow-2xl shadow-slate-950/30 backdrop-blur-xl">
            <div className="mx-auto flex max-w-[1500px] flex-wrap items-center justify-between gap-3">
              <TopNav />
              <LanguageSwitcher />
            </div>
          </header>
          <div id="main" tabIndex={-1}>
            {children}
          </div>
          <footer role="contentinfo" className="border-t border-white/10 bg-slate-950 px-5 py-8 text-slate-300">
            <div className="mx-auto flex max-w-[1500px] flex-col gap-4 text-sm sm:flex-row sm:items-center sm:justify-between">
              <p className="font-semibold tracking-[-0.02em] text-white">
                © {new Date().getFullYear()} ALEKSANDRA_BRAIN
              </p>
              <p className="max-w-3xl leading-6 text-slate-400">
                {isKa
                  ? "კვლევის, ოჯახის კითხვებისა და ექიმთან გადასამოწმებელი ნაბიჯების უსაფრთხო სამუშაო სივრცე. ეს ვებსაიტი არ ცვლის კლინიკურ გადაწყვეტილებას."
                  : "A safe workspace for research, family questions, and clinician-reviewed next steps. This website does not replace clinical judgment."}
              </p>
              <a className="rounded-full border border-cyan-300/30 px-4 py-2 text-cyan-100 transition hover:border-cyan-200 hover:bg-cyan-300/10" href={`/${locale}/audit`}>
                {isKa ? "აუდიტის ნახვა" : "View audit"}
              </a>
            </div>
          </footer>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
