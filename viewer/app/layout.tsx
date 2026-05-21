// Phase 6 root layout — reduced to a minimal children pass-through.
// The document shell (lang attribute + body) now lives in viewer/app/[locale]/layout.tsx
// per RESEARCH.md Pattern 2 (locale-owned shell — accessibility/SEO correctness).
// This file's only remaining responsibility is to satisfy Next.js's "root layout must exist"
// requirement and surface project-wide metadata. Top-level routes (api/audit/brain) are
// excluded from the i18n proxy matcher and continue to render their own shells.
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "ALEKSANDRA_BRAIN",
  description: "Pediatric HIE System Integrator",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return children;
}
