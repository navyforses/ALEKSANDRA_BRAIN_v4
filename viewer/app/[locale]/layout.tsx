import type { Metadata } from "next";
import { Inter, Noto_Sans_Georgian } from "next/font/google";
import { notFound } from "next/navigation";
import { NextIntlClientProvider, hasLocale } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import PortalFrame from "@/components/layout/PortalFrame";
import { buildPageMetadata, type Locale } from "@/lib/seo";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const notoSansGeorgian = Noto_Sans_Georgian({ subsets: ["georgian"], variable: "--font-georgian", display: "swap" });

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
  const typedLocale = locale as Locale;
  const isKa = typedLocale === "ka";

  return (
    <html lang={typedLocale} className={`${inter.variable} ${notoSansGeorgian.variable} h-full antialiased`}>
      <body className="min-h-screen bg-slate-50 text-foreground font-sans">
        <NextIntlClientProvider>
          <a className="skip-link" href="#main">
            {isKa ? "გადასვლა მთავარ კონტენტზე" : "Skip to main content"}
          </a>
          <PortalFrame locale={typedLocale}>{children}</PortalFrame>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
