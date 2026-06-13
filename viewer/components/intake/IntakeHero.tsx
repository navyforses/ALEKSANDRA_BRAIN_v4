"use client";

// The centerpiece of Today. A single inviting field that, on touch, opens
// the full intake console. The intake doesn't live in a side panel any
// more — it stands at the middle of the screen, the first thing offered.

import { useTranslations } from "next-intl";
import {
  IconArrowUp,
  IconAttach,
  IconMic,
} from "@/components/shell/icons";
import { useIntake } from "@/components/shell/intake-context";

export default function IntakeHero() {
  const t = useTranslations("Intake");
  const { setOpen } = useIntake();

  return (
    <button
      type="button"
      onClick={() => setOpen(true)}
      className="group block w-full rounded-xl border border-line bg-surface p-2 text-left transition-colors hover:border-accent-line focus:outline-none"
    >
      <div className="flex items-center gap-3 px-3 py-3">
        <span className="flex-1 text-[0.98rem] text-faint">{t("heroPrompt")}</span>
        <span className="hidden items-center gap-2 text-faint sm:flex">
          <IconAttach className="h-5 w-5" />
          <IconMic className="h-5 w-5" />
        </span>
        <span className="grid h-9 w-9 place-items-center rounded-full bg-accent-soft text-accent-ink transition-colors group-hover:bg-accent group-hover:text-white">
          <IconArrowUp className="h-4 w-4" />
        </span>
      </div>
    </button>
  );
}
