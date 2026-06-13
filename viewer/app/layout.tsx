// Root layout — a minimal pass-through. The document shell (html/body,
// fonts, the app chrome) lives in app/[locale]/layout.tsx so the lang
// attribute and locale-owned styling are correct per route. This file
// exists to satisfy Next.js's "root layout must exist" rule and to carry
// project-wide metadata defaults.
import type { Metadata, Viewport } from "next";
import { DEFAULT_OG_IMAGE, SITE_URL } from "@/lib/seo";
import "./globals.css";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#faf8f3" },
    { media: "(prefers-color-scheme: dark)", color: "#161410" },
  ],
};

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "ALEKSANDRA_BRAIN",
    template: "%s",
  },
  description:
    "A research system that never stops, for Aleksandra — what was found, what needs you, what you can do in a single step.",
  openGraph: {
    siteName: "ALEKSANDRA_BRAIN",
    images: [{ url: DEFAULT_OG_IMAGE, width: 1200, height: 630, alt: "ALEKSANDRA_BRAIN" }],
  },
  twitter: {
    card: "summary_large_image",
    images: [DEFAULT_OG_IMAGE],
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return children;
}
