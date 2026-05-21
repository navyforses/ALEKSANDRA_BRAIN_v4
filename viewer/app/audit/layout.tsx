// Phase 6 (06-03b Rule 3 deviation): sibling root layout for the /audit subtree.
// The locale-scoped [locale]/layout.tsx owns <html lang={locale}> for family routes;
// /audit lives OUTSIDE the next-intl proxy matcher (viewer/proxy.ts) and therefore needs
// its own root layout. Per Next.js 16 file conventions, when app/layout.tsx is a
// children pass-through, every subtree without a parent <html>/<body> wrapper becomes
// its own root layout (docs/01-app/.../layout.md line 142-146).
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import TopNav from "@/components/layout/TopNav";
import "../globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "ALEKSANDRA_BRAIN — Audit",
  description: "Pediatric HIE System Integrator",
};

export default function AuditRootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="h-screen w-screen overflow-hidden bg-background text-foreground flex flex-col font-sans">
        <header className="h-[60px] flex-shrink-0 border-b border-slate-200 bg-white">
          <TopNav />
        </header>
        <main className="flex-1 overflow-y-auto p-8">{children}</main>
      </body>
    </html>
  );
}
