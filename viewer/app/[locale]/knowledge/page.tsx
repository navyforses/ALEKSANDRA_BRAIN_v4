// Phase 5 placeholder. Knowledge surfaces papers, graph, hypotheses,
// and the perception pipeline in a later phase.
// BRAIN panel mounts via root layout.
import { setRequestLocale } from "next-intl/server";

export default async function KnowledgePage({
  params,
}: {
  params: Promise<{ locale: "en" | "ka" }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <div className="flex flex-col h-full space-y-4">
      <header className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Knowledge</h1>
        <p className="mt-2 text-sm text-slate-500">
          Papers, graph, hypotheses, perception pipeline — coming soon.
        </p>
      </header>
      <section className="flex-1 flex items-center justify-center text-sm text-slate-400">
        <p>Until then, use the dashboard for live counts and top papers.</p>
      </section>
    </div>
  )
}
