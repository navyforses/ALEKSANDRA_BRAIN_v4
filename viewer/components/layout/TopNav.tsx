import { getTranslations } from 'next-intl/server'
import { Link } from '@/i18n/navigation'

// Top navigation. typed Link from @/i18n/navigation auto-applies the active
// locale prefix (/en/ or /ka/) on every nav item. Labels resolve via the
// next-intl Navigation namespace, so Mkhedruli renders for ka and English
// renders for en — no per-tab branching needed.
//
// Today is "/" — also doubles as the daily clinical view (placeholder
// route /today exists but Today tab keeps "/" semantics).

export default async function TopNav() {
  const t = await getTranslations('Navigation')
  const localizedTabs = [
    { key: 'today' as const, href: '/' as const },
    { key: 'hypotheses' as const, href: '/hypotheses' as const },
    { key: 'therapies' as const, href: '/therapies' as const },
    { key: 'timeline' as const, href: '/timeline' as const },
    { key: 'audit' as const, href: '/audit' as const },
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
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <span className="text-sm font-medium text-slate-500 bg-slate-100 px-2 py-1 rounded-md">{t('doctorMode')}</span>
      </div>
    </nav>
  )
}
