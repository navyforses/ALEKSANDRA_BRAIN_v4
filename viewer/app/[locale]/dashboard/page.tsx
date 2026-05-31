// viewer/app/[locale]/dashboard/page.tsx — v7 tools hub.
//
// Repurposed during the Manus AI portal reconciliation merge (2026-05-30).
// Manus's version called <PortalTopicPage pageKey="dashboard"/>; the user
// chose to repurpose this URL as the v7 launcher hub since /dashboard is
// already in TopNav (viewer/components/layout/TopNav.tsx:8). Manus's
// PortalTopicPage(dashboard) content can be restored at a different URL
// in a follow-up phase if executive-overview-style content is desired.
//
// 8-card grid linking the 4 Phase 7.6 analytical routes (twin / causal /
// simulate / drift), the 2 widget routes orphaned by Manus's portal
// rewrites (active-questions, snapshot), and 2 Manus portal pages most
// relevant to clinician audience (hypotheses, papers).
//
// Not flag-gated — the hub itself is always reachable; individual route
// flags handle their own NO-GO via notFound().

import { getTranslations, setRequestLocale } from "next-intl/server";
import { Link } from "@/i18n/navigation";

export const dynamic = "force-dynamic";

type HubCard = {
  key:
    | "twin"
    | "causal"
    | "simulate"
    | "drift"
    | "activeQuestions"
    | "snapshot"
    | "hypotheses"
    | "papers";
  href:
    | "/twin"
    | "/causal"
    | "/simulate"
    | "/drift"
    | "/active-questions"
    | "/snapshot"
    | "/hypotheses"
    | "/papers";
  group: "analytical" | "widget" | "portal";
};

const CARDS: HubCard[] = [
  { key: "twin", href: "/twin", group: "analytical" },
  { key: "causal", href: "/causal", group: "analytical" },
  { key: "simulate", href: "/simulate", group: "analytical" },
  { key: "drift", href: "/drift", group: "analytical" },
  { key: "activeQuestions", href: "/active-questions", group: "widget" },
  { key: "snapshot", href: "/snapshot", group: "widget" },
  { key: "hypotheses", href: "/hypotheses", group: "portal" },
  { key: "papers", href: "/papers", group: "portal" },
];

function groupTone(group: HubCard["group"]): string {
  switch (group) {
    case "analytical":
      return "border-cyan-300/50 bg-cyan-50 hover:border-cyan-400 hover:bg-cyan-100";
    case "widget":
      return "border-emerald-300/50 bg-emerald-50 hover:border-emerald-400 hover:bg-emerald-100";
    case "portal":
      return "border-stone-300 bg-stone-50 hover:border-stone-400 hover:bg-stone-100";
  }
}

function groupLabel(group: HubCard["group"], locale: "en" | "ka"): string {
  if (locale === "ka") {
    switch (group) {
      case "analytical":
        return "ანალიტიკური";
      case "widget":
        return "ვიჯეტი";
      case "portal":
        return "პორტალი";
    }
  }
  switch (group) {
    case "analytical":
      return "Analytical";
    case "widget":
      return "Widget";
    case "portal":
      return "Portal";
  }
}

export default async function DashboardHubPage({
  params,
}: {
  params: Promise<{ locale: "en" | "ka" }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);

  const t = await getTranslations({ locale, namespace: "DashboardHub" });

  return (
    <main className="min-h-screen bg-stone-50 text-stone-950">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-5 py-6 sm:px-8">
        <header>
          <p className="font-mono text-xs uppercase text-cyan-700">
            {t("phaseLabel")}
          </p>
          <h1 className="mt-1 text-3xl font-semibold tracking-normal sm:text-4xl">
            {t("title")}
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-stone-600">
            {t("subtitle")}
          </p>
        </header>

        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {CARDS.map((card) => (
            <Link
              key={card.key}
              href={card.href}
              className={`flex flex-col gap-2 rounded-md border p-4 transition ${groupTone(
                card.group,
              )}`}
            >
              <span className="font-mono text-[10px] uppercase text-stone-500">
                {groupLabel(card.group, locale)}
              </span>
              <span className="text-base font-semibold text-stone-900">
                {t(`cards.${card.key}.title`)}
              </span>
              <span className="text-xs leading-5 text-stone-600">
                {t(`cards.${card.key}.description`)}
              </span>
            </Link>
          ))}
        </section>

        <footer className="text-xs text-stone-500">{t("footer")}</footer>
      </div>
    </main>
  );
}
