"use client";

// One gesture → the doctor's copy. The browser's print dialog saves to PDF
// on every platform, and the print stylesheet (globals.css) strips the app
// chrome so only the brief sheet remains.

import { useTranslations } from "next-intl";
import { IconPrint } from "@/components/shell/icons";

export default function PrintButton() {
  const t = useTranslations("Brief");
  return (
    <button
      type="button"
      onClick={() => window.print()}
      className="inline-flex items-center gap-2 rounded-full bg-ink px-4 py-2.5 text-sm font-medium text-paper transition-colors hover:bg-accent-ink"
    >
      <IconPrint className="h-4 w-4" />
      {t("print")}
    </button>
  );
}
