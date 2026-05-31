'use client';

// Phase 6 LanguageSwitcher — uses createNavigation-typed router from @/i18n/navigation.
// The typed router auto-strips/applies the locale prefix on router.replace, so the
// canonical next-intl 4 swap idiom is router.replace(pathname, {locale: newLocale}).
import { usePathname, useRouter } from '@/i18n/navigation';
import { useLocale } from 'next-intl';

export default function LanguageSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  const switchLocale = (newLocale: 'en' | 'ka') => {
    router.replace(pathname, {locale: newLocale});
  };

  return (
    <div className="flex w-full shrink-0 items-center gap-2 overflow-x-auto sm:w-auto" aria-label={locale === 'ka' ? 'ენის გადართვა' : 'Language switcher'}>
      <button
        type="button"
        onClick={() => switchLocale('en')}
        aria-label="Switch to English"
        aria-pressed={locale === 'en'}
        lang="en"
        className={`rounded-full px-3 py-2 text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-200 ${locale === 'en' ? 'bg-blue-600 text-white' : 'bg-white/90 text-slate-800 hover:bg-cyan-50'}`}
      >
        English
      </button>
      <button
        type="button"
        onClick={() => switchLocale('ka')}
        aria-label="გადართვა ქართულზე"
        aria-pressed={locale === 'ka'}
        lang="ka"
        className={`rounded-full px-3 py-2 text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-200 ${locale === 'ka' ? 'bg-blue-600 text-white' : 'bg-white/90 text-slate-800 hover:bg-cyan-50'}`}
      >
        ქართული
      </button>
    </div>
  );
}
