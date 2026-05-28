import { buildPageMetadata, type Locale } from "@/lib/seo";
import type { Metadata } from "next";
import { setRequestLocale, getTranslations } from "next-intl/server";
import {
  AssistantPanel,
  CommandCenterShell,
  DarkGlassPanel,
  DigitalTwinLab,
  InsightCard,
  SafetyBoundary,
  SectionHeader,
  StatusPill,
} from "@/components/prototype/PrototypeKit";


export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(locale, "brain");
}

export default async function BrainViewerPage({ params }: { params: Promise<{ locale: "en" | "ka" }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Brain");
  const isKa = locale === "ka";

  return (
    <CommandCenterShell>
      <section className="grid gap-5 xl:grid-cols-[1fr_0.55fr]">
        <DarkGlassPanel className="p-6 sm:p-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <StatusPill tone="violet" dark>{isKa ? "Digital twin brain lab" : "Digital twin brain lab"}</StatusPill>
              <h1 className="mt-5 max-w-5xl break-words text-[clamp(2.25rem,10vw,4.25rem)] font-semibold tracking-[-0.055em] text-white sm:text-6xl">{t("title")}</h1>
              <p className="mt-5 max-w-3xl text-sm leading-7 text-slate-300">
                {isKa
                  ? "ეს ეკრანი გადაკეთებულია Concept C-ის მიხედვით: მარცხენა MRI layer controls, ცენტრში glowing brain lab, მარჯვნივ evidence links და ქვემოთ scan timeline scrubber."
                  : "This screen now follows Concept C: MRI layer controls on the left, a glowing brain lab in the center, evidence links on the right, and a scan timeline scrubber below."}
              </p>
            </div>
            <div className="flex min-w-0 flex-wrap gap-2">
              <StatusPill tone="emerald" dark>{t("doctorView")}</StatusPill>
              <StatusPill tone="cyan" dark>{t("parentView")}</StatusPill>
              <StatusPill tone="violet" dark>{t("researcherView")}</StatusPill>
            </div>
          </div>
        </DarkGlassPanel>
        <AssistantPanel
          title={isKa ? "ჰიპოთეზის ინსპექტორი" : "Hypothesis inspector"}
          body={isKa ? "Mockup-ის მარჯვენა inspector პანელი აჩვენებს signal → evidence → safe question კავშირს." : "The mockup right inspector panel shows the signal → evidence → safe question relationship."}
          items={isKa ? ["Motor learning signal: დაკვირვება", "Sleep/recovery trend: საჭიროებს მეტ მონაცემს", "Clinical gate: ნებისმიერი ინტერპრეტაცია ექიმთან"] : ["Motor learning signal: observed", "Sleep/recovery trend: needs more data", "Clinical gate: clinician interpretation only"]}
        />
      </section>

      <DigitalTwinLab locale={locale} />

      <section className="grid gap-4 lg:grid-cols-3">
        <InsightCard dark label={isKa ? "Layer 01" : "Layer 01"} title={isKa ? "MRI viewer placeholder აღარ არის ცარიელი" : "MRI viewer placeholder is no longer empty"} body={isKa ? "ვიზუალიზაცია ჯერ prototype-ია, მაგრამ უკვე იმეორებს mockup-ის lab structure-ს და აჩვენებს სად განთავსდება რეალური viewer." : "The visualization remains prototype-only, but it now reproduces the mockup lab structure and shows where the real viewer belongs."} tone="cyan" />
        <InsightCard dark label={isKa ? "Layer 02" : "Layer 02"} title={isKa ? "Clinical signal overlay" : "Clinical signal overlay"} body={isKa ? "ფენები უკავშირდება თერაპიებს, timeline მოვლენებს და ჰიპოთეზებს, რათა brain lab იყოს workflow და არა მხოლოდ სურათი." : "Layers connect therapies, timeline events, and hypotheses so the brain lab is a workflow, not just an image."} tone="emerald" />
        <InsightCard dark label={isKa ? "Layer 03" : "Layer 03"} title={isKa ? "Family-safe explanation" : "Family-safe explanation"} body={isKa ? "მშობლის ხედვა რთულ ნეიროლოგიურ ინფორმაციას გარდაქმნის უსაფრთხო კითხვებად ექიმისთვის." : "The parent view turns complex neurological information into safe clinician questions."} tone="amber" />
      </section>

      <DarkGlassPanel>
        <SectionHeader dark eyebrow={isKa ? "Viewer status" : "Viewer status"} title={t("inDevelopment")} subtitle={t("dropMriHint")} />
        <div className="mt-6 grid gap-3 sm:grid-cols-4">
          {[t("controls"), t("toggleLayers"), t("fullscreen"), isKa ? "Evidence overlay" : "Evidence overlay"].map((item) => (
            <div key={item} className="rounded-2xl border border-white/10 bg-white/[0.055] p-4 text-sm font-medium text-slate-200">{item}</div>
          ))}
        </div>
      </DarkGlassPanel>

      <SafetyBoundary
        dark
        title={isKa ? "Brain viewer არ ცვლის ნეიროლოგს ან რადიოლოგს." : "The Brain viewer does not replace a neurologist or radiologist."}
        body={isKa ? "ეს არის კვლევითი ინტერფეისი. ნებისმიერი ინტერპრეტაცია, დიაგნოზი ან მკურნალობის ცვლილება უნდა გააკეთოს შესაბამისმა სპეციალისტმა." : "This is a research interface. Any interpretation, diagnosis, or treatment change must be made by an appropriate specialist."}
        items={isKa ? ["Client-side privacy boundary", "Clinician interpretation", "Family-safe explanation"] : ["Client-side privacy boundary", "Clinician interpretation", "Family-safe explanation"]}
      />
    </CommandCenterShell>
  );
}
