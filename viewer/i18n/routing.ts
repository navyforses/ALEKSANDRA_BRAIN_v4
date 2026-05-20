// Phase 6 i18n routing — locked decision D-01 in 06-CONTEXT.md.
// Source: https://next-intl.dev/docs/getting-started/app-router/with-i18n-routing
import {defineRouting} from 'next-intl/routing';

export const routing = defineRouting({
  locales: ['en', 'ka'],
  defaultLocale: 'en'
});
