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
    <div className="flex items-center gap-2">
      <button
        onClick={() => switchLocale('en')}
        aria-label="Switch to English"
        className={`px-3 py-1 text-sm rounded transition-colors ${locale === 'en' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-800 hover:bg-gray-300'}`}
      >
        English
      </button>
      <button
        onClick={() => switchLocale('ka')}
        aria-label="გადართვა ქართულზე"
        className={`px-3 py-1 text-sm rounded transition-colors ${locale === 'ka' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-800 hover:bg-gray-300'}`}
      >
        ქართული
      </button>
    </div>
  );
}
