import Link from 'next/link'

// Phase 5 top navigation (Gemini design integration, Day 0 cleanup).
// Today is "/" — also doubles as the daily clinical view (placeholder
// route /today exists for Days 1+ but Today tab keeps "/" semantics).

export default function TopNav() {
  // Five live routes only. Brain (Phase 6 — not yet mounted) and Knowledge
  // ("coming soon") removed per external visual review 2026-05-19 — no nav
  // pointers to unbuilt destinations.
  const tabs = [
    { name: 'Today', href: '/' },
    { name: 'Hypotheses', href: '/hypotheses' },
    { name: 'Therapies', href: '/therapies' },
    { name: 'Timeline', href: '/timeline' },
    { name: 'Audit', href: '/audit' },
  ]

  return (
    <nav className="flex items-center justify-between h-full px-6">
      <div className="flex items-center space-x-8 h-full">
        <Link href="/" className="font-semibold tracking-tight text-slate-900 text-lg">
          ALEKSANDRA_BRAIN
        </Link>

        <div className="hidden lg:flex space-x-2 h-full">
          {tabs.map((tab) => (
            <Link
              key={tab.name}
              href={tab.href}
              className="px-3 h-full flex items-center text-sm font-medium text-slate-500 hover:text-slate-900 border-b-2 border-transparent hover:border-slate-300 transition-colors"
            >
              {tab.name}
            </Link>
          ))}
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <span className="text-sm font-medium text-slate-500 bg-slate-100 px-2 py-1 rounded-md">Doctor Mode</span>
      </div>
    </nav>
  )
}
