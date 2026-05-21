import Link from "next/link";
import { setRequestLocale } from "next-intl/server";

// ALEKSANDRA_BRAIN v4.0 — operational entry page.
// Real MRI viewer arrives later. Until then, this page routes the family to
// the live dashboard and hypothesis validation workflow.
//
// Trust boundary: this file (viewer/app/[locale]/page.tsx) is client-side.
// Per FND-01/FND-02, no imaging library imports and no remote fetch may
// appear here or in any sibling route. The viewer/.eslintrc.json + the
// scripts/check-no-remote-fetch.sh CI step enforce that.

export default async function Home({
  params,
}: {
  params: Promise<{ locale: "en" | "ka" }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <main className="min-h-screen bg-stone-50 text-stone-950">
      <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col justify-center gap-8 px-5 py-10 sm:px-8">
        <header>
          <p className="font-mono text-xs uppercase text-cyan-700">Phase II.5</p>
          <h1 className="mt-2 text-4xl font-semibold tracking-normal sm:text-5xl">
            ALEKSANDRA_BRAIN <span className="text-stone-400">v4.0</span>
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-stone-600">
            Continuous research ingestion, memory, and hypothesis validation for Aleksandra Jincharadze.
            This surface is for family workflow visibility; clinical action stays with physicians.
          </p>
        </header>

        <section className="grid gap-4 md:grid-cols-2">
          <Link
            href="/dashboard"
            className="rounded-md border border-stone-200 bg-white p-5 shadow-sm shadow-stone-200/50 hover:border-cyan-300"
          >
            <p className="font-mono text-xs uppercase text-stone-500">Family-visible layer</p>
            <h2 className="mt-3 text-xl font-semibold">Dashboard</h2>
            <p className="mt-2 text-sm leading-6 text-stone-600">
              Counts, latest workflow events, spend traces, and top-ranked papers in one view.
            </p>
          </Link>
          <Link
            href="/hypotheses"
            className="rounded-md border border-stone-200 bg-white p-5 shadow-sm shadow-stone-200/50 hover:border-cyan-300"
          >
            <p className="font-mono text-xs uppercase text-stone-500">Validation workflow</p>
            <h2 className="mt-3 text-xl font-semibold">Hypotheses</h2>
            <p className="mt-2 text-sm leading-6 text-stone-600">
              Confirm evidence-linked research hypotheses, hold uncertain items, or reject weak ones.
            </p>
          </Link>
        </section>

        <section className="rounded-md border border-stone-200 bg-white p-5">
          <h2 className="text-base font-semibold">Closed foundation</h2>
          <ul className="mt-3 grid gap-2 text-sm text-stone-700 sm:grid-cols-2">
            <li>Phase I Perception closed</li>
            <li>Phase II Memory closed</li>
            <li>Phase II.5A spend instrumentation closed</li>
            <li>Phase II.5B perception scale-up closed</li>
          </ul>
        </section>

        <footer className="text-xs text-stone-500">
          Privacy: MRI data is client-side only. Never persisted on a server.
        </footer>
      </div>
    </main>
  );
}
