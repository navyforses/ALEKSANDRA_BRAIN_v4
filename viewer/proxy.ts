// next-intl proxy — Next.js 16 file convention (renamed from middleware.ts).
// Per 06-RESEARCH.md Pitfall 1: the file moved to proxy.ts and the function
// renamed `middleware` → `proxy`; the next-intl/middleware module import path
// is unchanged.
//
// Matcher excludes:
//   - api      → JSON endpoints, no UI
//   - _next    → Next.js asset paths
//   - _vercel  → Vercel system paths
//   - .*\\..*   → static files (any path containing a dot in a segment)
//   - minimal  → standalone design preview, intentionally outside localized chrome
//
// audit + brain were previously excluded as "English-only admin tools" but now
// live under [locale]/ so the proxy runs and applies the locale prefix.
import createMiddleware from 'next-intl/middleware';
import {routing} from './i18n/routing';

export default createMiddleware(routing);

export const config = {
  matcher: '/((?!api|_next|_vercel|minimal|.*\\..*).*)'
};
