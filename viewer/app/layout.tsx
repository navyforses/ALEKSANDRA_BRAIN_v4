import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import TopNav from "@/components/layout/TopNav";
import BrainPanel from "@/components/layout/BrainPanel";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "ALEKSANDRA_BRAIN",
  description: "Pediatric HIE System Integrator",
};

export default function RootLayout({
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

        <div className="flex flex-1 overflow-hidden">
          <main className="w-full md:w-[65%] h-full overflow-y-auto bg-background p-8">
            {children}
          </main>

          <aside className="hidden md:flex w-[35%] h-full border-l border-slate-200 bg-slate-50 flex-col">
            <BrainPanel />
          </aside>
        </div>
      </body>
    </html>
  );
}
