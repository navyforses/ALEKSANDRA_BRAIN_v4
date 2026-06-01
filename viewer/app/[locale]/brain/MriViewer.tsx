"use client";

// viewer/app/[locale]/brain/MriViewer.tsx — Phase 11 Client Component.
//
// Dynamic-import wrapper for MriViewerInner. @niivue/niivue touches
// window/document/WebGL2 at construction, so it MUST NOT server-render.
// In Next.js 16, dynamic(..., { ssr: false }) is only legal inside a Client
// Component — hence this thin "use client" wrapper, mirroring the established
// causal/Network.tsx + NetworkInner.tsx split. The Server Component page
// (brain/page.tsx via PortalTopicPage) renders <MriViewer /> directly.

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";

// Bilingual loading fallback. Rendered inside NextIntlClientProvider (set up
// in [locale]/layout.tsx), so useTranslations resolves. The visible ellipsis
// is decorative (aria-hidden); the sr-only text carries the meaning.
function ViewerLoading() {
  const t = useTranslations("Brain");
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex h-[560px] w-full items-center justify-center rounded-[2rem] border border-white/10 bg-white/[0.045] text-sm text-slate-400"
    >
      <span className="sr-only">{t("loading")}</span>
      <span aria-hidden="true" className="motion-safe:animate-pulse">
        …
      </span>
    </div>
  );
}

const Inner = dynamic(() => import("./MriViewerInner"), {
  ssr: false,
  loading: () => <ViewerLoading />,
});

export default function MriViewer() {
  return <Inner />;
}
