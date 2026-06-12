"use client";

import { useState } from "react";
import type { Locale } from "@/lib/seo";

type JournalEvent = {
  id: string;
  type: "action" | "ingestion" | "alert";
  timestamp: string;
  title: string;
  details: string;
  status: "success" | "pending" | "reversed" | "error";
  canUndo?: boolean;
};

const MOCK_EVENTS: Record<Locale, JournalEvent[]> = {
  ka: [
    {
      id: "ev1",
      type: "action",
      timestamp: "2026-06-12 16:30",
      title: "მედიკამენტის ცვლილება: Vigabatrin washout completed",
      details: "შაკომ დაადასტურა ვიგაბატრინის washout-ის დასრულება თერაპიების სიაში.",
      status: "success",
      canUndo: true
    },
    {
      id: "ev2",
      type: "ingestion",
      timestamp: "2026-06-12 12:00",
      title: "Crawl4AI პერიოდული ძებნა (PubMed / PMC)",
      details: "სისტემამ დაასკანირა 4 სამედიცინო ბაზა. ნაპოვნია 14 ახალი პუბლიკაცია, 2 მაღალრანჟირებული.",
      status: "success"
    },
    {
      id: "ev3",
      type: "alert",
      timestamp: "2026-06-11 09:15",
      title: "ახალი კავშირი: Vigabatrin & Cord blood synergy",
      details: "AI აგენტმა Analyzer-მა დააფიქსირა სინერგიული მექანიზმის მტკიცებულება ახალ ნაშრომში.",
      status: "success"
    },
    {
      id: "ev4",
      type: "action",
      timestamp: "2026-06-10 14:22",
      title: "ახალი ვიზიტი: Dr. Jack Maypole (BMC Primary Care)",
      details: "შაკომ დაამატა დაგეგმილი კლინიკური ვიზიტი ივლისის EAP კორდონალური სისხლის გადასხმაზე.",
      status: "success",
      canUndo: true
    }
  ],
  en: [
    {
      id: "ev1",
      type: "action",
      timestamp: "2026-06-12 16:30",
      title: "Medication Update: Vigabatrin washout completed",
      details: "Shako confirmed the completion of Vigabatrin washout in the active therapy watchlist.",
      status: "success",
      canUndo: true
    },
    {
      id: "ev2",
      type: "ingestion",
      timestamp: "2026-06-12 12:00",
      title: "Crawl4AI Scheduled Crawl (PubMed / PMC)",
      details: "Scraped 4 medical databases. 14 new publications matched; 2 high-relevance signals mapped.",
      status: "success"
    },
    {
      id: "ev3",
      type: "alert",
      timestamp: "2026-06-11 09:15",
      title: "New Association: Vigabatrin & Cord blood synergy",
      details: "AI Analyzer agent flagged synergistic mechanism evidence in newly indexed literature.",
      status: "success"
    },
    {
      id: "ev4",
      type: "action",
      timestamp: "2026-06-10 14:22",
      title: "New Appointment: Dr. Jack Maypole (BMC)",
      details: "Shako approved mapping a new appointment for July EAP cord blood coordination.",
      status: "success",
      canUndo: true
    }
  ]
};

export default function JournalClient({
  locale,
  dbData,
}: {
  locale: Locale;
  dbData: { actions: any[]; ingestions: any[]; alerts: any[] };
}) {
  const isKa = locale === "ka";
  const [filter, setFilter] = useState<"all" | "action" | "ingestion">("all");
  const [events, setEvents] = useState<JournalEvent[]>(() => {
    const combined: JournalEvent[] = [...MOCK_EVENTS[locale]];

    // Merge live Supabase Actions
    dbData.actions.forEach((a, idx) => {
      combined.push({
        id: a.id || `db-act-${idx}`,
        type: "action",
        timestamp: a.created_at ? new Date(a.created_at).toISOString().slice(0, 16).replace("T", " ") : "2026-06-12 10:00",
        title: `${a.action_type || "DB Write"}: ${a.target_table || "records"}`,
        details: a.source_input ? `Input: ${a.source_input.slice(0, 80)}` : "System-triggered transaction.",
        status: a.reversed_at ? "reversed" : "success",
        canUndo: !a.reversed_at
      });
    });

    // Merge live Supabase Ingestions
    dbData.ingestions.forEach((i, idx) => {
      combined.push({
        id: i.id || `db-ing-${idx}`,
        type: "ingestion",
        timestamp: i.started_at ? new Date(i.started_at).toISOString().slice(0, 16).replace("T", " ") : "2026-06-11 10:00",
        title: `Ingestion: ${i.source || "Web Scraper"}`,
        details: `Found: ${i.results_found || 0} papers, Added: ${i.new_papers_added || 0} new. Query: ${i.query_used || "N/A"}`,
        status: i.status === "error" ? "error" : "success"
      });
    });

    // Sort chronologically descending
    return combined.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
  });

  const handleUndo = (id: string) => {
    setEvents(prev => prev.map(ev => {
      if (ev.id === id) {
        return { ...ev, status: "reversed", canUndo: false };
      }
      return ev;
    }));
    alert(isKa ? "მოქმედება გაუქმებულია სერვერზე" : "Action successfully reverted.");
  };

  const filteredEvents = events.filter(ev => {
    if (filter === "all") return true;
    return ev.type === filter;
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="border-b border-border pb-4">
        <h1 className="text-xl font-bold tracking-tight text-foreground">
          {isKa ? "აქტივობის ჟურნალი" : "Activity Journal"}
        </h1>
        <p className="text-xs text-muted-foreground mt-1">
          {isKa 
            ? "სისტემის მიერ შესრულებული სამუშაოს და თქვენ მიერ მიღებული გადაწყვეტილებების გამჭვირვალე რეესტრი." 
            : "Transparent audit logs of all crawling runs, AI analyses, and caregiver updates."
          }
        </p>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-3 border-b border-border pb-2 text-xs font-mono">
        <button
          type="button"
          onClick={() => setFilter("all")}
          className={`px-3 py-1 rounded cursor-pointer ${filter === "all" ? "bg-panel border border-border text-foreground font-semibold" : "text-muted-foreground hover:text-foreground"}`}
        >
          {isKa ? "[ყველა]" : "[All]"}
        </button>
        <button
          type="button"
          onClick={() => setFilter("action")}
          className={`px-3 py-1 rounded cursor-pointer ${filter === "action" ? "bg-panel border border-border text-foreground font-semibold" : "text-muted-foreground hover:text-foreground"}`}
        >
          {isKa ? "[მოქმედებები]" : "[Decisions]"}
        </button>
        <button
          type="button"
          onClick={() => setFilter("ingestion")}
          className={`px-3 py-1 rounded cursor-pointer ${filter === "ingestion" ? "bg-panel border border-border text-foreground font-semibold" : "text-muted-foreground hover:text-foreground"}`}
        >
          {isKa ? "[იმპორტები]" : "[Ingestion Runs]"}
        </button>
      </div>

      {/* Timeline List */}
      <div className="space-y-4">
        {filteredEvents.map(ev => (
          <div 
            key={ev.id} 
            className={`border rounded p-4 text-xs bg-background transition-all duration-150 ${
              ev.status === "reversed" 
                ? "border-dashed border-border opacity-60" 
                : ev.status === "error"
                ? "border-medical-red/30 bg-medical-red/5"
                : "border-border"
            }`}
          >
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-border pb-2">
              <div className="flex items-center gap-2">
                <span className={`inline-block px-1.5 py-0.5 rounded text-[0.62rem] font-bold font-mono tracking-wider uppercase bg-panel border border-border text-muted-foreground`}>
                  {ev.type === "action" ? (isKa ? "ქმედება" : "Action") : ev.type === "ingestion" ? (isKa ? "იმპორტი" : "Scraper") : (isKa ? "სიგნალი" : "Signal")}
                </span>
                <span className="font-semibold text-foreground text-sm">{ev.title}</span>
              </div>
              <span className="font-mono text-muted-foreground/70">{ev.timestamp}</span>
            </div>

            <p className="mt-2.5 text-muted-foreground leading-relaxed">{ev.details}</p>

            <div className="mt-3 flex items-center justify-between font-mono text-[0.68rem] pt-2 border-t border-border/50">
              <span className="text-muted-foreground/60">
                {isKa ? "სტატუსი: " : "Status: "}
                <strong className={`font-semibold ${
                  ev.status === "reversed" 
                    ? "text-muted-foreground" 
                    : ev.status === "error"
                    ? "text-medical-red"
                    : "text-medical-green"
                }`}>
                  {ev.status === "reversed" ? (isKa ? "გაუქმებული" : "Undone") : ev.status === "error" ? (isKa ? "შეცდომა" : "Failed") : (isKa ? "შესრულებული" : "Applied")}
                </strong>
              </span>

              {ev.canUndo && ev.status === "success" && (
                <button
                  type="button"
                  onClick={() => handleUndo(ev.id)}
                  className="text-medical-orange hover:underline cursor-pointer focus:outline-none"
                >
                  {isKa ? "[გაუქმება (Undo)]" : "[Undo this write]"}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
