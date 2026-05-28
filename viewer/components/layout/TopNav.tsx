import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";

export default async function TopNav() {
  const t = await getTranslations("Navigation");
  const localizedTabs = [
    { key: "today" as const, href: "/" as const },
    { key: "dashboard" as const, href: "/dashboard" as const },
    { key: "brain" as const, href: "/brain" as const },
    { key: "hypotheses" as const, href: "/hypotheses" as const },
    { key: "therapies" as const, href: "/therapies" as const },
    { key: "timeline" as const, href: "/timeline" as const },
    { key: "audit" as const, href: "/audit" as const },
  ];

  return (
    <nav aria-label={t("primaryLabel")} className="flex w-full min-w-0 flex-none flex-wrap items-center gap-3 lg:flex-1 xl:flex-nowrap">
      <Link href="/" className="group flex shrink-0 items-center gap-3 rounded-full border border-cyan-300/25 bg-white/[0.06] px-3.5 py-2.5 shadow-[0_0_35px_rgba(34,211,238,0.12)] backdrop-blur-xl transition hover:border-cyan-200/60 hover:bg-cyan-300/10 focus:outline-none focus:ring-2 focus:ring-cyan-200">
        <span className="relative flex h-8 w-8 items-center justify-center rounded-full border border-cyan-300/40 bg-cyan-300/10" aria-hidden="true">
          <span className="h-2.5 w-2.5 rounded-full bg-cyan-300 shadow-[0_0_22px_rgba(103,232,249,0.95)]" />
        </span>
        <span className="text-sm font-semibold tracking-[-0.02em] text-white">ALEKSANDRA_BRAIN</span>
      </Link>

      <div className="order-3 flex w-full min-w-0 flex-1 items-center gap-1 overflow-x-auto rounded-full border border-white/10 bg-white/[0.045] p-1 shadow-sm shadow-slate-950/[0.03] backdrop-blur-xl md:order-none md:w-auto">
        {localizedTabs.map((tab) => (
          <Link
            key={tab.key}
            href={tab.href}
            className="whitespace-nowrap rounded-full px-3.5 py-2 text-xs font-semibold text-slate-300 transition hover:bg-cyan-300/15 hover:text-cyan-100 focus:outline-none focus:ring-2 focus:ring-cyan-200"
          >
            {t(tab.key)}
          </Link>
        ))}
      </div>

      <div className="hidden shrink-0 items-center gap-2 rounded-full border border-emerald-300/25 bg-emerald-300/10 px-3 py-2 text-xs font-semibold text-emerald-100 shadow-[0_0_24px_rgba(16,185,129,0.10)] md:flex">
        <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_14px_rgba(110,231,183,0.85)]" aria-hidden="true" />
        {t("doctorMode")}
      </div>
    </nav>
  );
}
