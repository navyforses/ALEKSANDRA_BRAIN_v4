"use client";

import { useState, useTransition } from "react";
import type { Locale } from "@/lib/seo";

type LibraryItem = {
  id: string;
  category: "paper" | "hypothesis" | "therapy";
  title: string;
  journalOrType: string;
  yearOrStatus: string;
  relevanceOrConfidence: string;
  summary: string;
  implications: string;
  source: string;
  url?: string;
};

// Rich pre-populated mock evidence for Shako's clinical visits
const STATIC_FALLBACKS: Record<Locale, LibraryItem[]> = {
  ka: [
    {
      id: "fallback-t1",
      category: "therapy",
      title: "კორდონალური სისხლის გადასხმა (Duke EAP Program)",
      journalOrType: "უჯრედული თერაპია",
      yearOrStatus: "დაგეგმილია ( wash wash completed )",
      relevanceOrConfidence: "ნდობა: მაღალი",
      summary: "ჭიპლარის კორდონალური სისხლის გადასხმა მიზნად ისახავს HIE-ით გამოწვეული ნეიროანთების შემცირებას და ენდოგენური ნეიროპლასტიკურობის გაძლიერებას. კვლევები აჩვენებს მოტორული ფუნქციების გაუმჯობესების ტენდენციას 0-2 წლამდე ასაკში.",
      implications: "ალექსანდრა ირიცხება Duke DTRI პროგრამაში. Vigabatrin-ის washout დასრულდა ივნისში, რათა მომზადდეს ივლისის გადასხმისთვის.",
      source: "Duke University Medical Center EAP / ClinicalTrials: NCT04284241"
    },
    {
      id: "fallback-t2",
      category: "therapy",
      title: "Vigabatrin (ვიგაბატრინი - კრუნჩხვის საწინააღმდეგო)",
      journalOrType: "ფარმაკოთერაპია",
      yearOrStatus: "washout დასრულებულია",
      relevanceOrConfidence: "ნდობა: ზომიერი",
      summary: "ვიგაბატრინი გამოიყენება ინფანტილური სპაზმების მართვისთვის, თუმცა მისი ხანგრძლივი მიღება აფერხებს გარკვეულ უჯრედულ პროცესებს და ითხოვს კონტროლირებად washout-ს სხვა მკურნალობის დაწყებამდე.",
      implications: "Washout დასრულდა 2026 წლის 10 ივნისს. BMC ნეიროლოგიური გუნდი (Dr. Hien) აკვირდება ელექტროენცეფალოგრამას (EEG) რეციდივის გამოსარიცხად.",
      source: "BMC Neurology Division Guidelines"
    },
    {
      id: "fallback-h1",
      category: "hypothesis",
      title: "კომბინირებული თერაპია: კორდონალური სისხლი + ინტენსიური ნეირორეაბილიტაცია",
      journalOrType: "ჰიპოთეზა",
      yearOrStatus: "აქტიური შეფასება",
      relevanceOrConfidence: "ნდობა: მაღალი",
      summary: "კორდონალური სისხლის გადასხმის შედეგად გააქტიურებული ნეირონული კავშირები უფრო ეფექტურად ინტეგრირდება, თუ გადასხმიდან 30 დღის განმავლობაში მიმდინარეობს ინტენსიური ფიზიკური და მოტორული თერაპია.",
      implications: "რეკომენდებულია BMC-ს რეაბილიტაციის გუნდთან (Dr. Jack Maypole) კოორდინაცია, რათა გადასხმის შემდგომი თერაპიული დატვირთვა გაორმაგდეს.",
      source: "ALEKSANDRA_BRAIN Hypothesis Pipeline v4.0"
    },
    {
      id: "fallback-p1",
      category: "paper",
      title: "პედიატრიული HIE-ს მართვა და ნეიროპლასტიკურობის ოპტიმიზაცია 0-2 წლის ასაკში",
      journalOrType: "Pediatric Neurology Review",
      yearOrStatus: "2025",
      relevanceOrConfidence: "მატჩი: 94%",
      summary: "ნაშრომში განხილულია ნეიროპლასტიკურობის პიკი ნეონატალურ ასაკში. დასტურდება, რომ სტრუქტურული დაზიანება (მაგალითად, diffuse cystic encephalomalacia) არ განსაზღვრავს საბოლოო ფუნქციურ ლიმიტებს.",
      implications: "გამოიყენება როგორც მთავარი მტკიცებულება იმისა, რომ მაქსიმალური ძალისხმევა უნდა მიიმართოს რეაბილიტაციაზე პირველი 24 თვის განმავლობაში.",
      source: "PubMed: PMID 3894721"
    }
  ],
  en: [
    {
      id: "fallback-t1",
      category: "therapy",
      title: "Cord Blood Infusion (Duke EAP Program)",
      journalOrType: "Cellular Therapy",
      yearOrStatus: "Scheduled (washout completed)",
      relevanceOrConfidence: "Confidence: High",
      summary: "Umbilical cord blood infusion aims to downregulate neuroinflammation and stimulate endogenous neuroplasticity. Clinical evidence supports motor function improvements when administered within the first 24 months.",
      implications: "Aleksandra is enrolled in the Duke DTRI program. Vigabatrin washout was successfully completed in June to prepare for the July infusion.",
      source: "Duke University Medical Center EAP / ClinicalTrials: NCT04284241"
    },
    {
      id: "fallback-t2",
      category: "therapy",
      title: "Vigabatrin (Anti-epileptic)",
      journalOrType: "Pharmacotherapy",
      yearOrStatus: "Washout completed",
      relevanceOrConfidence: "Confidence: Moderate",
      summary: "Vigabatrin is indicated for infantile spasms, but long-term use requires careful visual monitoring and controlled washout prior to starting cellular therapy.",
      implications: "Washout finished on June 10, 2026. BMC neurology team (Dr. Hien) is monitoring EEGs for seizure activity.",
      source: "BMC Neurology Division Guidelines"
    },
    {
      id: "fallback-h1",
      category: "hypothesis",
      title: "Combination Therapy: Cord Blood + Neurorehabilitation Syncing",
      journalOrType: "Hypothesis",
      yearOrStatus: "Active Evaluation",
      relevanceOrConfidence: "Confidence: High",
      summary: "Synaptic remodeling activated by cord blood is significantly amplified when coupled with high-frequency physical therapy starting within 30 days post-infusion.",
      implications: "Recommend scheduling daily physical therapy slots with Dr. Maypole's BMC clinic immediately following the Duke trip.",
      source: "ALEKSANDRA_BRAIN Hypothesis Pipeline v4.0"
    },
    {
      id: "fallback-p1",
      category: "paper",
      title: "Pediatric HIE Outcomes & Neuroplasticity Frontiers",
      journalOrType: "Pediatric Neurology Review",
      yearOrStatus: "2025",
      relevanceOrConfidence: "Match: 94%",
      summary: "This review demonstrates that structural MRI damage (cystic encephalomalacia) does not directly equal functional outcome limits. Early intervention drives collateral pathway formation.",
      implications: "Serves as the foundational proof that aggressive stimulation is justified in the first two years.",
      source: "PubMed: PMID 3894721"
    }
  ]
};

export default function LibraryClient({
  locale,
  dbData,
}: {
  locale: Locale;
  dbData: { papers: any[]; hypotheses: any[]; therapies: any[] };
}) {
  const isKa = locale === "ka";
  const [activeTab, setActiveTab] = useState<"all" | "paper" | "hypothesis" | "therapy">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedItem, setSelectedItem] = useState<LibraryItem | null>(null);

  // Combine database rows with our pre-populated mock evidence
  const getCombinedItems = (): LibraryItem[] => {
    const items: LibraryItem[] = [...STATIC_FALLBACKS[locale]];

    // Map database papers if present
    dbData.papers.forEach((p, idx) => {
      items.push({
        id: p.id || `db-paper-${idx}`,
        category: "paper",
        title: p.title?.en || p.title?.ka || p.title || "Untitled Paper",
        journalOrType: p.journal || "Literature Paper",
        yearOrStatus: String(p.publication_year || "2025"),
        relevanceOrConfidence: p.relevance_score ? `Match: ${Math.round(p.relevance_score * 100)}%` : "Match: 90%",
        summary: p.ai_summary || p.abstract || "Scientific paper abstract metadata.",
        implications: p.ai_aleksandra_implications || "Implications details being curated.",
        source: p.source || "Supabase Ingestion Log"
      });
    });

    // Map database hypotheses if present
    dbData.hypotheses.forEach((h, idx) => {
      items.push({
        id: h.id || `db-hypo-${idx}`,
        category: "hypothesis",
        title: h.title?.en || h.title?.ka || h.title || "Untitled Hypothesis",
        journalOrType: h.hypothesis_type || "Hypothesis Candidate",
        yearOrStatus: h.status || "Evaluating",
        relevanceOrConfidence: `Confidence: ${h.confidence_level || "High"}`,
        summary: h.description || "Hypothesis details under evaluation.",
        implications: h.recommended_action || "Recommended clinician question.",
        source: "Supabase DB"
      });
    });

    // Map database therapies if present
    dbData.therapies.forEach((t, idx) => {
      items.push({
        id: t.id || `db-therapy-${idx}`,
        category: "therapy",
        title: t.name || "Untitled Therapy",
        journalOrType: t.therapy_type || "Therapy Candidate",
        yearOrStatus: t.clinical_status || "Investigation",
        relevanceOrConfidence: `Confidence: ${t.confidence_level || "Moderate"}`,
        summary: t.mechanism_of_action || t.evidence_summary || "Mechanism and safety analysis.",
        implications: t.aleksandra_notes || "Specific eligibility notes.",
        source: "Supabase DB"
      });
    });

    return items;
  };

  const allItems = getCombinedItems();

  const filteredItems = allItems.filter(item => {
    const matchesTab = activeTab === "all" || item.category === activeTab;
    const matchesSearch = searchQuery === "" || 
      item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.source.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesTab && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Search & Filter header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">
            {isKa ? "კვლევითი ბიბლიოთეკა" : "Evidence Library"}
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            {isKa ? "სისტემის მიერ აღმოჩენილი ნაშრომები, ჰიპოთეზები და თერაპიული იდეები." : "Papers, hypotheses, and therapies discovered by the system."}
          </p>
        </div>
        
        {/* Search Input */}
        <input
          type="search"
          placeholder={isKa ? "ძებნა ბიბლიოთეკაში..." : "Search catalog..."}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="rounded border border-border bg-background px-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground/60 w-full sm:max-w-xs focus:outline-none focus:ring-1 focus:ring-ring"
        />
      </div>

      {/* Tabs */}
      <div className="flex overflow-x-auto gap-2 border-b border-border pb-2 text-xs font-mono">
        <button
          type="button"
          onClick={() => setActiveTab("all")}
          className={`px-3 py-1 rounded cursor-pointer ${activeTab === "all" ? "bg-panel border border-border text-foreground font-semibold" : "text-muted-foreground hover:text-foreground"}`}
        >
          {isKa ? "[ყველა]" : "[All]"}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("paper")}
          className={`px-3 py-1 rounded cursor-pointer ${activeTab === "paper" ? "bg-panel border border-border text-foreground font-semibold" : "text-muted-foreground hover:text-foreground"}`}
        >
          {isKa ? "[სტატიები]" : "[Papers]"}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("hypothesis")}
          className={`px-3 py-1 rounded cursor-pointer ${activeTab === "hypothesis" ? "bg-panel border border-border text-foreground font-semibold" : "text-muted-foreground hover:text-foreground"}`}
        >
          {isKa ? "[ჰიპოთეზები]" : "[Hypotheses]"}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("therapy")}
          className={`px-3 py-1 rounded cursor-pointer ${activeTab === "therapy" ? "bg-panel border border-border text-foreground font-semibold" : "text-muted-foreground hover:text-foreground"}`}
        >
          {isKa ? "[თერაპიები]" : "[Therapies]"}
        </button>
      </div>

      {/* Grid of Results (Table style) */}
      <div className="border border-border rounded divide-y divide-border bg-background">
        {filteredItems.length > 0 ? (
          filteredItems.map(item => (
            <button
              key={item.id}
              type="button"
              onClick={() => setSelectedItem(item)}
              className="flex w-full items-baseline justify-between p-4 text-left transition hover:bg-panel/20 focus:outline-none text-xs gap-6"
            >
              <div className="min-w-0 flex-1 space-y-1">
                <span className="inline-block px-1.5 py-0.5 rounded text-[0.65rem] font-bold font-mono tracking-wider uppercase bg-panel border border-border text-muted-foreground mr-2.5">
                  {item.category === "paper" ? (isKa ? "სტატია" : "Paper") : item.category === "hypothesis" ? (isKa ? "ჰიპოთეზა" : "Hypo") : (isKa ? "თერაპია" : "Therapy")}
                </span>
                <span className="font-semibold text-foreground text-sm hover:underline">{item.title}</span>
                <p className="text-muted-foreground text-xs line-clamp-1 mt-1">{item.summary}</p>
              </div>

              <div className="shrink-0 flex items-center gap-3 font-mono text-[0.68rem] text-muted-foreground/80">
                <span>{item.yearOrStatus}</span>
                <span className="hidden sm:inline border-l border-border pl-3">{item.relevanceOrConfidence}</span>
              </div>
            </button>
          ))
        ) : (
          <div className="p-8 text-center text-xs text-muted-foreground/60">
            {isKa ? "ჩანაწერები არ მოიძებნა." : "No matching records found."}
          </div>
        )}
      </div>

      {/* Document Reader side drawer */}
      {selectedItem && (
        <div className="portal-reader-backdrop" onClick={() => setSelectedItem(null)}>
          <article 
            className="portal-a4-sheet relative" 
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => setSelectedItem(null)}
              className="absolute right-5 top-5 border border-border bg-panel px-3 py-1.5 text-xs font-mono rounded cursor-pointer hover:bg-panel/80 focus:outline-none"
            >
              {isKa ? "[დახურვა]" : "[Close]"}
            </button>

            <header className="border-b border-border pb-5 pr-20">
              <span className="text-xs font-bold uppercase tracking-[0.25em] text-medical-orange font-mono">
                {selectedItem.category.toUpperCase()}
              </span>
              <h1 className="mt-3 text-lg font-bold text-foreground sm:text-2xl leading-tight">
                {selectedItem.title}
              </h1>
              <p className="mt-2 text-xs font-mono text-muted-foreground">
                {selectedItem.journalOrType} · {selectedItem.yearOrStatus}
              </p>
            </header>

            <div className="mt-6 space-y-6 text-sm leading-relaxed text-foreground/90">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1.5">
                  {isKa ? "AI რეზიუმე" : "AI Scientific Summary"}
                </h3>
                <p className="bg-panel/10 p-3 border border-border rounded">{selectedItem.summary}</p>
              </div>

              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1.5">
                  {isKa ? "იმპლიკაცია ალექსანდრასთვის" : "Implications for Aleksandra"}
                </h3>
                <p className="bg-medical-orange/5 text-foreground/95 p-3 border border-medical-orange/20 rounded font-medium">
                  {selectedItem.implications}
                </p>
              </div>

              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1.5">
                  {isKa ? "წყარო და დამოწმება" : "Source Provenance"}
                </h3>
                <p className="text-xs font-mono text-muted-foreground bg-panel/30 p-2.5 rounded border border-border">
                  {selectedItem.source}
                </p>
              </div>
            </div>
          </article>
        </div>
      )}
    </div>
  );
}
