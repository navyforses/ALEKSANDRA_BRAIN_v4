// ALEKSANDRA_BRAIN v4.0 — Phase 0+ Foundation page.
// Real MRI viewer arrives in Phase 7. Until then, this page is the
// "system is alive" landing for the family dashboard.
//
// Trust boundary: this file (viewer/app/page.tsx) is client-side.
// Per FND-01/FND-02, no imaging library imports and no remote fetch may
// appear here or in any sibling route. The viewer/.eslintrc.json + the
// scripts/check-no-remote-fetch.sh CI step enforce that.

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-12 bg-zinc-50 dark:bg-black text-black dark:text-zinc-100 font-sans">
      <div className="max-w-2xl w-full space-y-8">
        <header>
          <h1 className="text-4xl font-bold tracking-tight">
            ALEKSANDRA_BRAIN <span className="text-zinc-400">v4.0</span>
          </h1>
          <p className="mt-2 text-zinc-600 dark:text-zinc-400">
            Continuous AI research system for Aleksandra Jincharadze.
          </p>
        </header>

        <section className="rounded-lg border border-zinc-200 dark:border-zinc-800 p-6 space-y-3">
          <h2 className="text-lg font-semibold">Phase 0+ Foundation</h2>
          <ul className="text-sm text-zinc-700 dark:text-zinc-300 space-y-1.5">
            <li>✅ Supabase ledger + RLS + append-only runs</li>
            <li>✅ n8n daily-budget-gate active (cron every 30 min)</li>
            <li>✅ Telegram kill-switch + Anthropic spend cap</li>
            <li>✅ Neo4j + Qdrant (local Docker)</li>
            <li>✅ CrewAI 5-agent crew (tools wired Phase 1+)</li>
            <li>✅ 9 MCP servers configured</li>
          </ul>
        </section>

        <section className="rounded-lg border border-zinc-200 dark:border-zinc-800 p-6 space-y-3">
          <h2 className="text-lg font-semibold">Next: Phase 1 — Perception</h2>
          <p className="text-sm text-zinc-700 dark:text-zinc-300">
            Continuous literature ingest from PubMed, ClinicalTrials.gov, and
            bioRxiv/medRxiv every 6 hours, with full provenance stamped on
            every record.
          </p>
        </section>

        <footer className="text-xs text-zinc-500 pt-8">
          Privacy: MRI data is client-side only. Never persisted on a server.
        </footer>
      </div>
    </main>
  );
}
