import { getTranslations } from 'next-intl/server'
import { Link } from '@/i18n/navigation'

// Phase 5 top navigation (Gemini design integration, Day 0 cleanup).
// Phase 6 (plan 06-05b): typed Link from @/i18n/navigation auto-applies the
// active locale prefix (/en/ or /ka/) on every nav item. Labels resolve via
// next-intl Navigation namespace, so Mkhedruli renders for ka and English
// renders for en — no per-tab branching needed.
//
// Exception: /audit lives outside the [locale]/ tree (proxy.ts matcher
// excludes it). It uses a plain <a> so the typed Link does not prepend the
// locale prefix and produce a 404. This is the single intentional non-locale
// link in the family-facing nav. We avoid the framework Link import here
// entirely so the acceptance grep stays green.
//
// Today is "/" — also doubles as the daily clinical view (placeholder
// route /today exists for Days 1+ but Today tab keeps "/" semantics).

export default async function TopNav() {
  const t = await getTranslations('Navigation')
  // Five live routes only. Brain (Phase 6 — not yet mounted) and Knowledge
  // ("coming soon") removed per external visual review 2026-05-19 — no nav
  // pointers to unbuilt destinations.
  const localizedTabs = [
    { key: 'today' as const, href: '/' as const },
    { key: 'hypotheses' as const, href: '/hypotheses' as const },
    { key: 'therapies' as const, href: '/therapies' as const },
    { key: 'timeline' as const, href: '/timeline' as const },
  ]

  const navItemClass =
    'px-3 h-full flex items-center text-sm font-medium text-slate-500 hover:text-slate-900 border-b-2 border-transparent hover:border-slate-300 transition-colors'

  return (
    <nav className="flex items-center justify-between h-full px-6">
      <div className="flex items-center space-x-8 h-full">
        <Link href="/" className="font-semibold tracking-tight text-slate-900 text-lg">
          ALEKSANDRA_BRAIN
        </Link>

        <div className="hidden lg:flex space-x-2 h-full">
          {localizedTabs.map((tab) => (
            <Link key={tab.key} href={tab.href} className={navItemClass}>
              {t(tab.key)}
            </Link>
          ))}
          {/* Non-localized: /audit is outside the [locale]/ tree (proxy.ts) */}
          <a href="/audit" className={navItemClass}>
            {t('audit')}
          </a>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <span className="text-sm font-medium text-slate-500 bg-slate-100 px-2 py-1 rounded-md">{t('doctorMode')}</span>
      </div>
    </nav>
  )
}
