// Phase 6 root layout — reduced to a minimal children pass-through.
// The document shell (lang attribute + body) now lives in viewer/app/[locale]/layout.tsx
// per RESEARCH.md Pattern 2 (locale-owned shell — accessibility/SEO correctness).
// This file's only remaining responsibility is to satisfy Next.js's "root layout must exist"
// requirement and surface project-wide metadata. Top-level routes (api/audit/brain) are
// excluded from the i18n proxy matcher and continue to render their own shells.
import type { Metadata, Viewport } from "next";
import { DEFAULT_OG_IMAGE, SITE_URL } from "@/lib/seo";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "ALEKSANDRA_BRAIN — ბავშვთა HIE კვლევის სამუშაო სივრცე",
    template: "%s",
  },
  description: "ოჯახისა და კლინიკური გუნდისთვის შექმნილი სამუშაო სივრცე, რომელიც HIE კვლევას, პროგრესს, ჰიპოთეზებსა და ექიმთან გადასამოწმებელ ნაბიჯებს აერთიანებს.",
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
}: Readonly<{
  children: React.ReactNode;
}>) {
  return children;
}
