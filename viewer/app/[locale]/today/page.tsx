// Phase 5 placeholder. Today's full clinical view ships in a later phase.
// BRAIN panel mounts via root layout.

export default function TodayPage() {
  return (
    <div className="flex flex-col h-full space-y-4">
      <header className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Today</h1>
        <p className="mt-2 text-sm text-slate-500">Daily clinical view — coming soon.</p>
      </header>
      <section className="flex-1 flex items-center justify-center text-sm text-slate-400">
        <p>Awaiting calendar pipeline, vitals stream, and observation log.</p>
      </section>
    </div>
  )
}
