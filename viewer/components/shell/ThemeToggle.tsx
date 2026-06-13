"use client";

// Day paper / night vigil. The actual class is set before paint by the
// inline script in the locale layout (no flash); this control only flips
// it and remembers the choice.

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { IconMoon, IconSun } from "@/components/shell/icons";

export default function ThemeToggle() {
  const t = useTranslations("Shell");
  const [dark, setDark] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function toggle() {
    const root = document.documentElement;
    const next = !root.classList.contains("dark");
    root.classList.toggle("dark", next);
    try {
      localStorage.setItem("theme", next ? "dark" : "light");
    } catch {
      /* storage may be blocked — the choice simply won't persist */
    }
    setDark(next);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={dark ? t("theme.toLight") : t("theme.toDark")}
      title={dark ? t("theme.toLight") : t("theme.toDark")}
      className="grid h-9 w-9 place-items-center rounded-full text-muted transition-colors hover:bg-accent-soft hover:text-accent-ink"
    >
      {/* Render a stable icon until mounted to avoid a hydration mismatch. */}
      {mounted && dark ? <IconSun /> : <IconMoon />}
    </button>
  );
}
