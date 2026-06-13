"use client";

// Dynamic-import wrapper for MriViewerInner. @niivue/niivue touches
// window/document/WebGL2 at construction, so it MUST NOT server-render. In
// Next.js 16, dynamic(..., { ssr: false }) is only legal inside a Client
// Component — hence this thin "use client" wrapper. The Server Component
// page renders <MriViewer /> directly.

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";

function ViewerLoading() {
  const t = useTranslations("Brain");
  return (
    <div
      role="status"
      aria-live="polite"
      className="grid h-[520px] w-full place-items-center rounded-xl border border-line bg-surface text-sm text-faint"
    >
      <span className="sr-only">{t("loading")}</span>
      <span aria-hidden className="motion-safe:animate-pulse">
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
