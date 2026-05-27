import { setRequestLocale, getTranslations } from "next-intl/server";
import { getRows } from "@/lib/supabase";
import { displayField, type BilingualField } from "@/lib/i18n";
import {
  AssistantPanel,
  CommandCenterShell,
  CommandMetricCard,
  DarkGlassPanel,
  DemoDataNotice,
  InsightCard,
  SectionHeader,
  StatusPill,
  TimelineRail,
} from "@/components/prototype/PrototypeKit";

export const dynamic = "force-dynamic";

type Tone = "cyan" | "emerald" | "amber" | "rose" | "violet" | "slate" | "stone";

type TimelineEvent = {
  id: string;
  event_date: string;
  event_type: string;
  title: BilingualField;
  description: BilingualField;
  institution: string | null;
  location: string | null;
  created_at: string;
  updated_at: string;
};

function typeCounts(events: TimelineEvent[]) {
  return events.reduce<Record<string, number>>((acc, event) => {
    acc[event.event_type] = (acc[event.event_type] || 0) + 1;
    return acc;
  }, {});
}

function toneForType(type: string): Tone {
  if (type.includes("therapy") || type.includes("intervention")) return "emerald";
  if (type.includes("assessment") || type.includes("clinical")) return "cyan";
  if (type.includes("risk") || type.includes("warning")) return "amber";
  if (type.includes("research") || type.includes("paper")) return "violet";
  return "slate";
}

export default async function TimelinePage({ params }: { params: Promise<{ locale: "en" | "ka" }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("Timeline");
  const tShared = await getTranslations("Shared");
  const tEvt = await getTranslations("TimelineEventType");
  const isKa = locale === "ka";

  function formatDate(value: string | null) {
    if (!value) return tShared("notListed");
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toISOString().slice(0, 10);
  }

  const events = await getRows<TimelineEvent>("aleksandra_timeline", {
    select: "id,event_date,event_type,title,description,institution,location,created_at,updated_at",
    order: "event_date.desc",
    limit: 100,
  });
  const counts = typeCounts(events.rows);
  const latestDate = formatDate(events.rows[0]?.event_date ?? null);

  const railEvents = events.rows.map((event) => {
    const typeLabel = tEvt.has(event.event_type) ? tEvt(event.event_type) : event.event_type;
    const location = [event.institution, event.location].filter(Boolean).join(" | ") || t("locationPending");
    const description = displayField(event.description, locale);
    return {
      time: formatDate(event.event_date),
      title: `${displayField(event.title, locale)} · ${typeLabel}`,
      body: description ? `${description} ${location}` : location,
      tone: toneForType(event.event_type),
    };
  });

  return (
    <CommandCenterShell>
      <section className="grid gap-5 xl:grid-cols-[1.3fr_0.7fr]">
        <DarkGlassPanel className="p-6 sm:p-8">
          <StatusPill tone="cyan" dark>{t("phaseLabel")}</StatusPill>
          <h1 className="mt-5 max-w-5xl text-4xl font-semibold tracking-[-0.055em] text-white sm:text-6xl">{t("title")}</h1>
          <p className="mt-5 max-w-4xl text-sm leading-7 text-slate-300">{t("subtitle")}</p>
        </DarkGlassPanel>
        <AssistantPanel title={isKa ? "Longitudinal tracker" : "Longitudinal tracker"} body={isKa ? "Timeline ახლა ჰგავს generated journey mockup-ს: ცალკე ჩანაწერები გადაიქცა readable progress rail-ად." : "The timeline now follows the generated journey mockup: isolated records become a readable progress rail."} items={isKa ? ["რა მოხდა ადრე?", "რა შეიცვალა ჩარევის შემდეგ?", "რა კითხვას აჩენს შემდეგი review-სთვის?"] : ["What happened before?", "What changed after intervention?", "What question does this raise for the next review?"]} />
      </section>

      {events.error ? <DemoDataNotice title={isKa ? "Timeline data channel" : "Timeline data channel"} body={events.error} /> : null}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <CommandMetricCard label={t("shown")} value={events.rows.length} hint={isKa ? "ქრონოლოგიური ჩანაწერი" : "longitudinal records"} tone="cyan" />
        <CommandMetricCard label={t("latest")} value={latestDate} hint={isKa ? "ბოლო დაფიქსირებული მოვლენა" : "most recent recorded event"} tone="emerald" />
        <CommandMetricCard label={isKa ? "Event types" : "Event types"} value={Object.keys(counts).length} hint={isKa ? "დაჯგუფებული კატეგორიები" : "grouped categories"} tone="violet" />
        <CommandMetricCard label={isKa ? "Clinical memory" : "Clinical memory"} value={railEvents.length > 0 ? "on" : "—"} hint={isKa ? "გუნდისთვის და ოჯახისთვის" : "for team and family"} tone="amber" />
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <InsightCard dark label={isKa ? "Progress" : "Progress"} title={isKa ? "პროგრესი ჩანს დროში, არა მხოლოდ ცალკე ჩანაწერებად." : "Progress is visible over time, not as isolated notes."} body={isKa ? "Timeline აერთიანებს მკურნალობას, შეფასებებს, კვლევით იდეებს და observation data-ს, რათა გუნდი ხედავდეს ცვლილების მიმართულებას." : "The timeline connects therapies, assessments, research ideas, and observation data so the team can see the direction of change."} tone="cyan" />
        <InsightCard dark label={isKa ? "Context" : "Context"} title={isKa ? "ყოველ მოვლენას აქვს წყარო და ადგილი." : "Every event keeps source and place."} body={isKa ? "institution/location metadata ეხმარება ოჯახს გაიხსენოს სად მოხდა შეფასება ან ჩარევა." : "Institution and location metadata help the family recall where an assessment or intervention happened."} tone="slate" />
        <InsightCard dark label={isKa ? "Clinical review" : "Clinical review"} title={isKa ? "გადაწყვეტილება ეფუძნება ცვლილების ისტორიას." : "Decision-making uses the history of change."} body={isKa ? "როდესაც ახალი ჰიპოთეზა ან თერაპია განიხილება, timeline აჩვენებს რა შეიცვალა მანამდე და შემდეგ." : "When a hypothesis or therapy is reviewed, the timeline shows what changed before and after."} tone="emerald" />
      </section>

      {Object.keys(counts).length > 0 ? (
        <DarkGlassPanel>
          <SectionHeader dark eyebrow={isKa ? "Event mix" : "Event mix"} title={isKa ? "მოვლენები დაჯგუფებულია ტიპების მიხედვით." : "Events are grouped by type."} subtitle={isKa ? "ეს ჯგუფები ეხმარება გუნდს დაინახოს არის თუ არა timeline therapy-heavy, assessment-heavy ან research-heavy." : "These groups help the team see whether the timeline is therapy-heavy, assessment-heavy, or research-heavy."} />
          <div className="mt-5 flex flex-wrap gap-2">
            {Object.entries(counts).map(([type, count]) => <StatusPill key={type} tone={toneForType(type)} dark>{tEvt.has(type) ? tEvt(type) : type}: {count}</StatusPill>)}
          </div>
        </DarkGlassPanel>
      ) : null}

      <DarkGlassPanel>
        <SectionHeader dark eyebrow={isKa ? "Longitudinal tracker" : "Longitudinal tracker"} title={t("events")} subtitle={isKa ? "ქრონოლოგია უნდა იყოს ოჯახისათვის გასაგები და კლინიკური გუნდისთვის საკმარისად დეტალური." : "The chronology should be understandable for the family and detailed enough for the clinical team."} />
        <div className="mt-6">{railEvents.length > 0 ? <TimelineRail dark events={railEvents} /> : <DemoDataNotice title={isKa ? "Timeline ჯერ ცარიელია" : "Timeline is empty"} body={t("emptyList")} />}</div>
      </DarkGlassPanel>
    </CommandCenterShell>
  );
}
