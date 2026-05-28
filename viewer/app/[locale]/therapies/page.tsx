import { buildPageMetadata, type Locale } from "@/lib/seo";
import type { Metadata } from "next";
import { setRequestLocale, getTranslations } from "next-intl/server";
import { getRows } from "@/lib/supabase";
import { displayField, type BilingualField } from "@/lib/i18n";
import {
  AssistantPanel,
  CommandCenterShell,
  CommandMetricCard,
  DarkGlassPanel,
  DemoDataNotice,
  EvidencePipeline,
  InsightCard,
  SafetyBoundary,
  SectionHeader,
  StatusPill,
} from "@/components/prototype/PrototypeKit";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(locale, "therapies");
}


type Tone = "cyan" | "emerald" | "amber" | "rose" | "violet" | "slate" | "stone";

type Therapy = {
  id: string;
  name: BilingualField;
  therapy_type: string | null;
  mechanism_of_action: string | null;
  evidence_in_hie: string | null;
  evidence_summary: BilingualField;
  clinical_status: string | null;
  available_locations: string[] | null;
  approximate_cost: string | null;
  aleksandra_eligible: boolean | null;
  aleksandra_status: string | null;
  aleksandra_notes: string | null;
  optimal_age_window: string | null;
  time_sensitivity: string | null;
  ai_assessment: string | null;
  confidence_level: string | null;
  created_at: string | null;
};

function tone(value: string | null): Tone {
  if (value === "proven" || value === "receiving" || value === "completed") return "emerald";
  if (value === "promising" || value === "planned" || value === "applied" || value === "evaluating") return "cyan";
  if (value === "disproven" || value === "ineligible" || value === "declined") return "rose";
  if (value === "critical") return "amber";
  return "stone";
}

function extractAssessmentText(raw: string | null): string | null {
  if (!raw) return null;
  const trimmed = raw.trim();
  if (!trimmed.startsWith("{")) return raw;
  try {
    const parsed = JSON.parse(trimmed);
    if (parsed && typeof parsed === "object" && typeof parsed.dossier === "string") return parsed.dossier;
    return null;
  } catch {
    return null;
  }
}

export default async function TherapiesPage({ params }: { params: Promise<{ locale: "en" | "ka" }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Therapies");
  const tShared = await getTranslations("Shared");
  const isKa = locale === "ka";

  function yesNo(value: boolean | null) {
    if (value == null) return tShared("unknown");
    return value ? tShared("yes") : tShared("no");
  }

  function listValue(values: string[] | null) {
    return values && values.length > 0 ? values.join(", ") : tShared("notListed");
  }

  const therapies = await getRows<Therapy>("therapies", {
    select: "id,name,therapy_type,mechanism_of_action,evidence_in_hie,evidence_summary,clinical_status,available_locations,approximate_cost,aleksandra_eligible,aleksandra_status,aleksandra_notes,optimal_age_window,time_sensitivity,ai_assessment,confidence_level,created_at",
    order: "name.asc",
    limit: 100,
  });

  const active = therapies.rows.filter((tr) => tr.aleksandra_status === "receiving").length;
  const watching = therapies.rows.filter((tr) => ["planned", "applied", "evaluating"].includes(tr.aleksandra_status || "")).length;
  const promising = therapies.rows.filter((tr) => tr.evidence_in_hie === "promising").length;
  const eligible = therapies.rows.filter((tr) => tr.aleksandra_eligible).length;
  const critical = therapies.rows.filter((tr) => tr.time_sensitivity === "critical").length;

  return (
    <CommandCenterShell>
      <section className="grid gap-5 xl:grid-cols-[1.3fr_0.7fr]">
        <DarkGlassPanel className="p-6 sm:p-8">
          <StatusPill tone="emerald" dark>{t("phaseLabel")}</StatusPill>
          <h1 className="mt-5 max-w-5xl text-4xl font-semibold tracking-[-0.055em] text-white sm:text-6xl">{t("title")}</h1>
          <p className="mt-5 max-w-4xl text-sm leading-7 text-slate-300">{t("subtitle")}</p>
        </DarkGlassPanel>
        <AssistantPanel title={isKa ? "Therapy pathway copilot" : "Therapy pathway copilot"} body={isKa ? "Generated mockup-ის იდეა აქ გამოიყენება თერაპიებისთვის: evidence, access, age window, status და safety boundary ერთ card-ში ჩანს." : "The generated mockup language is applied to therapies: evidence, access, age window, status, and safety boundary sit inside one card."} items={isKa ? ["არ არის რეკომენდაცია", "არის decision support", "ყველა გზა საჭიროებს ექიმის approval-ს"] : ["Not a recommendation", "Decision support only", "Every path needs clinician approval"]} />
      </section>

      {therapies.error ? <DemoDataNotice title={isKa ? "Therapies data channel" : "Therapies data channel"} body={therapies.error} /> : null}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <CommandMetricCard label={t("shown")} value={therapies.rows.length} hint={isKa ? "თერაპიული ჩანაწერი" : "therapy records"} tone="slate" />
        <CommandMetricCard label={t("active")} value={active} hint={isKa ? "მიმდინარე ჩართული გზა" : "currently active pathways"} tone="emerald" />
        <CommandMetricCard label={t("watching")} value={watching} hint={isKa ? "დაგეგმილი ან შესაფასებელი" : "planned or under evaluation"} tone="cyan" />
        <CommandMetricCard label={t("eligibleYes")} value={eligible} hint={isKa ? "ინდივიდუალური განხილვისთვის" : "for individual review"} tone="violet" />
        <CommandMetricCard label={t("timeCritical")} value={critical} hint={isKa ? "სწრაფი review" : "fast review"} tone="amber" />
      </section>

      <DarkGlassPanel>
        <SectionHeader dark eyebrow={isKa ? "Therapy workflow" : "Therapy workflow"} title={isKa ? "თერაპია წარმოდგენილია როგორც evidence-backed pathway, არა რეკლამა." : "Therapy is presented as an evidence-backed pathway, not an ad."} subtitle={isKa ? "მიზანია პრაქტიკული decision support: რა არის, რატომ შეიძლება იყოს მნიშვნელოვანი, სად არის ხელმისაწვდომი და რა უნდა გადაწყვიტოს ექიმმა." : "The purpose is practical decision support: what it is, why it may matter, where it is available, and what the clinician must decide."} />
        <div className="mt-6"><EvidencePipeline dark steps={[
          { label: "Evidence", title: isKa ? "მტკიცებულების დონე" : "Evidence level", body: isKa ? "HIE evidence და confidence ჩანს card-ის ზედა ნაწილში." : "HIE evidence and confidence are visible at the top of every card.", tone: "cyan" },
          { label: "Access", title: isKa ? "პრაქტიკული დეტალები" : "Practical details", body: isKa ? "ადგილმდებარეობა, ღირებულება და ასაკობრივი ფანჯარა არ იკარგება." : "Location, cost, and age window are not lost.", tone: "violet" },
          { label: "Status", title: isKa ? "გზის მდგომარეობა" : "Pathway status", body: isKa ? "active/planned/evaluating ფერები სწრაფად აჩვენებს მოძრაობას." : "Active/planned/evaluating colors quickly show motion.", tone: "emerald" },
          { label: "Safety", title: isKa ? "ექიმის gate" : "Clinician gate", body: isKa ? "არცერთი pathway არ ხდება ავტომატური დანიშნულება." : "No pathway becomes an automatic prescription.", tone: "amber" },
        ]} /></div>
      </DarkGlassPanel>

      <section className="grid gap-4 lg:grid-cols-3">
        <InsightCard dark label={isKa ? "Evidence" : "Evidence"} title={isKa ? "მტკიცებულების დონე მკაფიოდ ჩანს" : "Evidence level is explicit"} body={isKa ? "თითოეული თერაპია გამოყოფს HIE evidence-ს, confidence-ს და AI assessment-ს ისე, რომ ოჯახმა და გუნდმა ერთსა და იმავე ინფორმაციას უყურონ." : "Each therapy exposes HIE evidence, confidence, and AI assessment so family and team can read the same information."} tone="cyan" />
        <InsightCard dark label={isKa ? "Pathway" : "Pathway"} title={isKa ? "სტატუსი და დრო ერთმანეთთან არის მიბმული" : "Status and timing stay connected"} body={isKa ? "აქტიური, დაგეგმილი, შესაფასებელი და დრო-სენსიტიური გზები ერთ ფერად სისტემაში ჩანს." : "Active, planned, evaluative, and time-sensitive pathways are shown in one color system."} tone="emerald" />
        <InsightCard dark label={isKa ? "Access" : "Access"} title={isKa ? "პრაქტიკული დეტალები არ იკარგება" : "Practical details are not lost"} body={isKa ? "ადგილმდებარეობა, სავარაუდო ღირებულება, ასაკობრივი ფანჯარა და eligibility სწრაფად ჩანს decision brief-ში." : "Location, approximate cost, age window, and eligibility are visible in the decision brief."} tone="violet" />
      </section>

      <DarkGlassPanel>
        <SectionHeader dark eyebrow={isKa ? "Therapy pathways" : "Therapy pathways"} title={isKa ? "ყველა therapy card გადაკეთდა mockup-ის command card სტილში." : "Every therapy card now uses the mockup command-card style."} subtitle={isKa ? "Live Supabase ველები შენარჩუნებულია, მაგრამ ვიზუალი შეესაბამება generated prototype მიმართულებას." : "Live Supabase fields are preserved while the visual language matches the generated prototype direction."} />
        <div className="mt-6 grid gap-4">
          {therapies.rows.map((therapy) => {
            const assessment = extractAssessmentText(therapy.ai_assessment);
            const evidence = displayField(therapy.evidence_summary, locale);
            const hasAny = evidence || assessment || therapy.aleksandra_notes;
            return (
              <article key={therapy.id} className="overflow-hidden rounded-[1.75rem] border border-white/10 bg-white/[0.055] p-5 shadow-2xl shadow-slate-950/20 backdrop-blur-xl">
                <div className="grid gap-5 xl:grid-cols-[1fr_auto]">
                  <div>
                    <div className="flex flex-wrap items-center gap-2"><StatusPill tone={tone(therapy.aleksandra_status)} compact dark>{therapy.aleksandra_status || t("statusNotConsidered")}</StatusPill><StatusPill tone={tone(therapy.evidence_in_hie)} compact dark>{t("evidenceLabel")} {therapy.evidence_in_hie || t("evidenceUnknown")}</StatusPill><StatusPill tone="slate" compact dark>{therapy.therapy_type || t("typePending")}</StatusPill></div>
                    <h2 className="mt-4 text-xl font-semibold leading-8 tracking-[-0.02em] text-white">{displayField(therapy.name, locale)}</h2>
                    {therapy.mechanism_of_action ? <p className="mt-3 max-w-4xl text-sm leading-7 text-slate-300">{therapy.mechanism_of_action}</p> : null}
                  </div>
                  <dl className="grid gap-3 text-sm sm:grid-cols-3 xl:w-[28rem]"><div className="rounded-2xl border border-white/10 bg-slate-950/35 p-3"><dt className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-slate-500">{t("eligible")}</dt><dd className="mt-2 font-semibold text-white">{yesNo(therapy.aleksandra_eligible)}</dd></div><div className="rounded-2xl border border-white/10 bg-slate-950/35 p-3"><dt className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-slate-500">{t("ageWindow")}</dt><dd className="mt-2 font-semibold text-white">{therapy.optimal_age_window || tShared("na")}</dd></div><div className="rounded-2xl border border-white/10 bg-slate-950/35 p-3"><dt className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-slate-500">{t("timing")}</dt><dd className="mt-2 font-semibold text-white">{therapy.time_sensitivity || tShared("na")}</dd></div></dl>
                </div>
                <div className="mt-5 grid gap-4 border-t border-white/10 pt-5 xl:grid-cols-3"><div><p className="font-mono text-[0.68rem] uppercase tracking-[0.16em] text-slate-500">{t("clinicalStatus")}</p><p className="mt-2 text-sm leading-6 text-slate-300">{therapy.clinical_status || tShared("unknown")}</p></div><div><p className="font-mono text-[0.68rem] uppercase tracking-[0.16em] text-slate-500">{t("locations")}</p><p className="mt-2 text-sm leading-6 text-slate-300">{listValue(therapy.available_locations)}</p></div><div><p className="font-mono text-[0.68rem] uppercase tracking-[0.16em] text-slate-500">{t("cost")}</p><p className="mt-2 text-sm leading-6 text-slate-300">{therapy.approximate_cost || t("costUnknown")}</p></div></div>
                {hasAny ? <div className="mt-5 grid gap-3 rounded-3xl border border-white/10 bg-slate-950/35 p-4">{evidence ? <p className="text-sm leading-7 text-slate-300">{evidence}</p> : null}{assessment ? <p className="text-sm leading-7 text-slate-300">{assessment}</p> : null}{therapy.aleksandra_notes ? <p className="text-sm leading-7 text-slate-300">{therapy.aleksandra_notes}</p> : null}</div> : null}
              </article>
            );
          })}
          {therapies.rows.length === 0 ? <DemoDataNotice title={isKa ? "თერაპიები ჯერ არ ჩანს" : "No therapies yet"} body={t("emptyList")} /> : null}
        </div>
      </DarkGlassPanel>

      <SafetyBoundary dark title={isKa ? "თერაპიული გზა ყოველთვის საჭიროებს ექიმის კონტროლს." : "Every therapy pathway requires clinician control."} body={isKa ? "პლატფორმა არ ნიშნავს ბავშვის მკურნალობის ავტომატურ არჩევას. ის აჩვენებს კითხვებს, evidence-ს და პრაქტიკულ რისკებს, რომ ექიმმა და ოჯახმა უკეთესად იმსჯელონ." : "The platform does not automatically choose a child’s treatment. It surfaces questions, evidence, and practical risks so clinician and family can reason better together."} items={isKa ? ["No automatic prescription", "Clinician approval required", "Risk and evidence visible"] : ["No automatic prescription", "Clinician approval required", "Risk and evidence visible"]} />
    </CommandCenterShell>
  );
}
