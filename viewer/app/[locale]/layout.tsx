import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { notFound } from "next/navigation";
import { NextIntlClientProvider, hasLocale } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import TopNav from "@/components/layout/TopNav";
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
      <body className="min-h-screen bg-slate-950 text-foreground font-sans">
        <NextIntlClientProvider>
          <header className="sticky top-0 z-50 border-b border-white/10 bg-slate-950/88 px-4 py-3 shadow-2xl shadow-slate-950/30 backdrop-blur-xl">
            <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-3">
              <TopNav />
              <LanguageSwitcher />
            </div>
          </header>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
