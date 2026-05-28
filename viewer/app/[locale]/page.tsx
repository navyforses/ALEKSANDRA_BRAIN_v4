import { buildPageMetadata, type Locale } from "@/lib/seo";
import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";
import {
  AssistantPanel,
  FamilyJourneyStepper,
  FamilyPortalShell,
  GlassPanel,
  InsightCard,
  SafetyBoundary,
  SectionHeader,
  StatusPill,
} from "@/components/prototype/PrototypeKit";


function copy(locale: Locale) {
  const isKa = locale === "ka";
  return {
    eyebrow: isKa ? "Family-safe research journey · pediatric HIE" : "Family-safe research journey · pediatric HIE",
    title: isKa
      ? "ერთ სივრცეში ჩანს კვლევა, პროგრესი და ექიმთან გადასამოწმებელი შემდეგი ნაბიჯი."
      : "One calm workspace for research, progress, and clinician-reviewed next steps.",
    subtitle: isKa
      ? "ეს გვერდი უკვე გადაკეთებულია იმ გენერირებული family-safe mockup-ის მიხედვით: რბილი პორტალი, უსაფრთხოების საზღვარი, კვლევის გზა, ოჯახის კითხვები და AI copilot-ის არადიაგნოსტიკური დახმარება."
      : "This page follows the generated family-safe mockup: a soft portal, visible safety boundary, research journey, family questions, and a non-diagnostic AI copilot.",
    steps: [
      {
        label: isKa ? "ახლა" : "Now",
        title: isKa ? "რა ხდება დღეს" : "What is happening today",
        body: isKa ? "მოკლე, ადამიანური განმარტება მიმდინარე ფოკუსზე, პროგრესზე და შეკითხვებზე ექიმისთვის." : "A human-readable view of the current focus, progress, and questions for the clinician.",
        tone: "cyan" as const,
      },
      {
        label: isKa ? "კვლევა" : "Research",
        title: isKa ? "რა ამბობს evidence" : "What the evidence says",
        body: isKa ? "წყაროები იყოფა დადასტურებულად, პერსპექტიულად და ჯერ მხოლოდ ჰიპოთეზად." : "Sources are separated into established, promising, and hypothesis-only evidence.",
        tone: "violet" as const,
      },
      {
        label: isKa ? "თერაპია" : "Therapy",
        title: isKa ? "რა არის უსაფრთხო ნაბიჯი" : "What is a safe next step",
        body: isKa ? "თერაპიული იდეები არ ხდება ავტომატური რეკომენდაცია; ისინი გადადის კლინიკურ განხილვაზე." : "Therapy ideas do not become automatic recommendations; they move into clinical review.",
        tone: "emerald" as const,
      },
      {
        label: isKa ? "ქრონოლოგია" : "Timeline",
        title: isKa ? "რა იცვლება დროში" : "What changes over time",
        body: isKa ? "timeline აერთიანებს დაკვირვებებს, ვიზიტებს, ჰიპოთეზებს და follow-up ამოცანებს." : "The timeline connects observations, visits, hypotheses, and follow-up tasks.",
        tone: "amber" as const,
      },
    ],
    cards: [
      {
        label: isKa ? "ოჯახისთვის" : "For family",
        title: isKa ? "სამედიცინო ტექსტი გადაიქცევა გასაგებ კითხვებად" : "Medical text becomes understandable questions",
        body: isKa ? "მშობელი ხედავს: რა ვიცით, რა არ ვიცით, რა უნდა ვკითხოთ ექიმს და რა არ უნდა შევცვალოთ დამოუკიდებლად." : "The parent sees what is known, unknown, what to ask the clinician, and what should not be changed independently.",
        tone: "emerald" as const,
      },
      {
        label: isKa ? "ექიმისთვის" : "For clinician",
        title: isKa ? "ყველა იდეას აქვს evidence და risk context" : "Every idea has evidence and risk context",
        body: isKa ? "სისტემა ამზადებს მოკლე clinical brief-ს, რათა განხილვა იყოს სწრაფი, დოკუმენტირებული და ფრთხილი." : "The system prepares a concise clinical brief so review is faster, documented, and careful.",
        tone: "cyan" as const,
      },
      {
        label: isKa ? "კვლევისთვის" : "For research",
        title: isKa ? "ჰიპოთეზა აღარ იკარგება" : "Hypotheses do not get lost",
        body: isKa ? "ყველა კვლევითი იდეა ინახება სტატუსით, წყაროებით, next action-ით და follow-up თარიღით." : "Every research idea is stored with status, sources, next action, and follow-up timing.",
        tone: "violet" as const,
      },
    ],
  };
}


export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return buildPageMetadata(locale, "home");
}

export default async function HomePage({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const c = copy(locale);
  const isKa = locale === "ka";

  return (
    <FamilyPortalShell>
      <section className="grid gap-5 xl:grid-cols-[0.72fr_1.7fr_0.78fr]">
        <GlassPanel className="self-start p-5">
          <StatusPill tone="emerald">{isKa ? "უსაფრთხო პორტალი" : "Safe portal"}</StatusPill>
          <h2 className="mt-4 text-xl font-semibold tracking-[-0.035em] text-slate-950">{isKa ? "ოჯახის ხედვა" : "Family view"}</h2>
          <p className="mt-3 text-sm leading-7 text-slate-600">
            {isKa ? "Concept B-ის მარცხენა პანელი აქ გადაიქცა ოჯახისთვის გასაგებ რუკად: ახლა, კვლევა, თერაპია, დრო." : "The Concept B left panel becomes a readable family map: now, research, therapy, time."}
          </p>
          <div className="mt-5 grid gap-2 text-sm text-slate-700">
            {[isKa ? "დღევანდელი ფოკუსი" : "Today’s focus", isKa ? "ექიმთან კითხვები" : "Questions for clinician", isKa ? "უსაფრთხოების საზღვარი" : "Safety boundary", isKa ? "პროგრესის დროითი ხაზი" : "Progress timeline"].map((item) => (
              <div key={item} className="rounded-2xl border border-slate-100 bg-white/70 px-4 py-3">{item}</div>
            ))}
          </div>
        </GlassPanel>

        <GlassPanel className="overflow-hidden p-0">
          <div className="relative min-h-[31rem] p-7 sm:p-10">
            <div className="absolute -right-20 -top-20 h-72 w-72 rounded-full bg-cyan-200/40 blur-3xl" />
            <div className="absolute -bottom-24 left-10 h-72 w-72 rounded-full bg-emerald-200/35 blur-3xl" />
            <div className="relative z-10">
              <StatusPill tone="cyan">{c.eyebrow}</StatusPill>
              <h1 className="mt-5 max-w-none break-words text-[clamp(2.35rem,5.2vw,4.9rem)] font-semibold leading-[0.98] tracking-[-0.055em] text-slate-950">{c.title}</h1>
              <p className="mt-6 max-w-3xl text-base leading-8 text-slate-600 sm:text-lg">{c.subtitle}</p>
              <div className="mt-8 flex flex-wrap gap-3">
                <a href={`/${locale}/dashboard`} className="rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white shadow-xl shadow-slate-950/15 transition hover:-translate-y-0.5">{isKa ? "ნახე მართვის პანელი" : "Open clinical dashboard"}</a>
                <a href={`/${locale}/brain`} className="rounded-full border border-slate-200 bg-white/82 px-5 py-3 text-sm font-semibold text-slate-800 shadow-sm transition hover:-translate-y-0.5 hover:border-cyan-300">{isKa ? "ნახე ციფრული ტვინის ლაბორატორია" : "Open digital twin lab"}</a>
              </div>
            </div>
            <div className="relative z-10 mt-10 grid gap-3 sm:grid-cols-3">
              {[
                [isKa ? "Research loop" : "Research loop", "24/7"],
                [isKa ? "Clinical gate" : "Clinical gate", isKa ? "ექიმი" : "clinician"],
                [isKa ? "Scope" : "Scope", "HIE"],
              ].map(([label, value]) => (
                <div key={label} className="rounded-3xl border border-white/75 bg-white/75 p-5 shadow-xl shadow-slate-950/[0.05] backdrop-blur">
                  <p className="font-mono text-[0.65rem] uppercase tracking-[0.18em] text-slate-500">{label}</p>
                  <p className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-slate-950">{value}</p>
                </div>
              ))}
            </div>
          </div>
        </GlassPanel>

        <AssistantPanel
          dark={false}
          title={isKa ? "AI copilot არ სვამს დიაგნოზს" : "AI copilot does not diagnose"}
          body={isKa ? "იგი მხოლოდ აწყობს წყაროებს, ამზადებს კითხვებს და აჩვენებს რა საჭიროებს ექიმის review-ს." : "It only organizes sources, prepares questions, and shows what requires clinician review."}
          items={isKa ? ["რა შეიცვალა ბოლო კვირაში?", "რომელი იდეაა მხოლოდ ჰიპოთეზა?", "რა უნდა გადავამოწმოთ ექიმთან?"] : ["What changed this week?", "Which idea is hypothesis-only?", "What should we ask the clinician?"]}
        />
      </section>

      <GlassPanel>
        <SectionHeader eyebrow={isKa ? "მოგზაურობის რუკა" : "Journey map"} title={isKa ? "Concept B-ის visual journey ახლა frontend კომპონენტებია." : "The Concept B visual journey is now real frontend components."} subtitle={isKa ? "თითოეული ეტაპი აჩვენებს არა მხოლოდ მონაცემს, არამედ რას ნიშნავს ეს ოჯახისთვის და გუნდისთვის." : "Each step shows not just data, but what it means for the family and the team."} />
        <div className="mt-6"><FamilyJourneyStepper steps={c.steps} /></div>
      </GlassPanel>

      <section className="grid gap-4 lg:grid-cols-3">{c.cards.map((item) => <InsightCard key={item.title} {...item} />)}</section>

      <SafetyBoundary
        title={isKa ? "ეს არის გადაწყვეტილების სამუშაო სივრცე, არა ექიმის ჩანაცვლება." : "This is a decision workspace, not a clinician replacement."}
        body={isKa ? "ნებისმიერი მკურნალობა, დოზა, თერაპია ან ინტერვენცია რჩება ექიმის/კლინიკური გუნდის კონტროლში. პლატფორმა ეხმარება კითხვების, წყაროების და პროგრესის ორგანიზებას." : "Any treatment, dosage, therapy, or intervention remains under clinician control. The platform helps organize questions, sources, and progress."}
        items={isKa ? ["Human-in-the-loop", "Evidence confidence", "Family-safe language"] : ["Human-in-the-loop", "Evidence confidence", "Family-safe language"]}
      />
    </FamilyPortalShell>
  );
}
