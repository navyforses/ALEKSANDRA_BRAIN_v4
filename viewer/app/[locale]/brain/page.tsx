import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import MriViewer from "./MriViewer";
import { IconLock } from "@/components/shell/icons";
import { buildPageMetadata, type Locale } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(locale, "brain");
}

export default async function BrainPage({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Brain");

  return (
    <div className="space-y-8">
      <header className="u-rise max-w-2xl">
        <h1 className="font-serif text-[1.9rem] leading-tight tracking-tight text-ink">
          {t("pageTitle")}
        </h1>
        <p className="mt-3 text-[0.98rem] leading-relaxed text-muted">{t("pageSubtitle")}</p>
      </header>

      {/* Privacy is the foundation of trust here, not a footnote — so it
          leads, stated as a promise the architecture keeps. */}
      <section className="u-rise u-rise-1 rounded-xl border border-signal-line bg-signal-soft p-5">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-full bg-signal/10 text-signal">
            <IconLock />
          </span>
          <div>
            <p className="font-serif text-base text-ink">{t("privacyHeading")}</p>
            <p className="mt-1.5 text-sm leading-relaxed text-muted">{t("privacyBody")}</p>
          </div>
        </div>
      </section>

      <section className="u-rise u-rise-2">
        <MriViewer />
      </section>
    </div>
  );
}
