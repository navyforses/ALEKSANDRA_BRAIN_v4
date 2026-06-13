"use client";

// One gesture, context preserved. The typed next-intl router swaps only
// the locale segment of the current path, so the doctor and the family
// land on the same screen in their own language. Both languages carry
// equal visual weight — neither is the "translation" of the other.

import { useLocale } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";

export default function LanguageToggle() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  function to(next: "en" | "ka") {
    if (next !== locale) router.replace(pathname, { locale: next });
  }

  const pill =
    "rounded-full px-3 py-1 text-[0.8rem] font-medium transition-colors";
  const on = "bg-ink text-paper";
  const off = "text-muted hover:text-ink";

  return (
    <div
      role="group"
      aria-label={locale === "ka" ? "ენის გადართვა" : "Language"}
      className="flex items-center gap-0.5 rounded-full border border-line p-0.5"
    >
      <button
        type="button"
        lang="ka"
        onClick={() => to("ka")}
        aria-pressed={locale === "ka"}
        className={`${pill} ${locale === "ka" ? on : off}`}
      >
        ქარ
      </button>
      <button
        type="button"
        lang="en"
        onClick={() => to("en")}
        aria-pressed={locale === "en"}
        className={`${pill} ${locale === "en" ? on : off}`}
      >
        EN
      </button>
    </div>
  );
}
