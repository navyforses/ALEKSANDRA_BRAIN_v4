import type { Metadata } from "next";
import { Inter, Noto_Sans_Georgian, Noto_Serif_Georgian } from "next/font/google";
import { notFound } from "next/navigation";
import { NextIntlClientProvider, hasLocale } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { routing } from "@/i18n/routing";
import AppShell from "@/components/shell/AppShell";
import { buildPageMetadata, type Locale } from "@/lib/seo";

export const dynamic = "force-dynamic";

// Inter carries Latin UI text; Noto Sans Georgian carries Mkhedruli body
// text. Noto Serif Georgian is the display face for both scripts — a
// deliberate choice so Georgian headings get the same typographic dignity
// as Latin ones, rather than being the afterthought "translation".
const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const notoSansGeorgian = Noto_Sans_Georgian({
  subsets: ["georgian"],
  variable: "--font-georgian",
  display: "swap",
});
const notoSerifGeorgian = Noto_Serif_Georgian({
  subsets: ["georgian", "latin"],
  variable: "--font-georgian-serif",
  display: "swap",
});

// Set the day/night class before paint so the night vigil never flashes
// paper first. Falls back to the OS preference when no choice is stored.
const THEME_SCRIPT = `(function(){try{var t=localStorage.getItem('theme');var d=t?t==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;if(d)document.documentElement.classList.add('dark');}catch(e){}})();`;

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

  return (
    <html
      lang={typedLocale}
      suppressHydrationWarning
      className={`${inter.variable} ${notoSansGeorgian.variable} ${notoSerifGeorgian.variable} h-full antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="font-sans">
        <NextIntlClientProvider>
          <AppShell locale={typedLocale}>{children}</AppShell>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
