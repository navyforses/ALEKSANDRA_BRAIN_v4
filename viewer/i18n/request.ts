// Phase 6 i18n request config — locked decision D-01 in 06-CONTEXT.md.
// next-intl 4 surface: getRequestConfig({requestLocale}), NOT ({locale}).
// Source: https://next-intl.dev/docs/getting-started/app-router/with-i18n-routing
import {getRequestConfig} from 'next-intl/server';
import {hasLocale} from 'next-intl';
import {routing} from './routing';

export default getRequestConfig(async ({requestLocale}) => {
  const requested = await requestLocale;
  const locale = hasLocale(routing.locales, requested)
    ? requested
    : routing.defaultLocale;

  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default
  };
});
