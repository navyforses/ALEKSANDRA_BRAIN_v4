// Sibling root layout for the /audit subtree. /audit is excluded from the
// next-intl proxy matcher (viewer/proxy.ts) so we lock the locale to 'en'
// via setRequestLocale + wrap in NextIntlClientProvider — TopNav is an async
// server component that calls getTranslations('Navigation') and needs the
// request-level locale context that the proxy normally provides under [locale]/.
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import TopNav from "@/components/layout/TopNav";
import "../globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "ALEKSANDRA_BRAIN — Audit",
  description: "Pediatric HIE System Integrator",
};

export default async function AuditRootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  setRequestLocale("en");

  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="h-screen w-screen overflow-hidden bg-background text-foreground flex flex-col font-sans">
        <NextIntlClientProvider locale="en">
          <header className="h-[60px] flex-shrink-0 border-b border-slate-200 bg-white">
            <TopNav />
          </header>
          <main className="flex-1 overflow-y-auto p-8">{children}</main>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
