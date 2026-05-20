// Phase 6 i18n proxy — Next.js 16 file convention (renamed from middleware.ts).
// Per 06-RESEARCH.md Pitfall 1: the file moved to proxy.ts and the function
// renamed `middleware` → `proxy`; the next-intl/middleware module import path
// is unchanged.
//
// Matcher excludes:
//   - api      → JSON endpoints, no UI
//   - audit    → internal admin tooling (English only per 06-SPEC.md)
//   - brain    → NiiVue MRI viewer (clinical-English by convention)
//   - _next    → Next.js asset paths
//   - _vercel  → Vercel system paths
//   - .*\..*   → static files (any path containing a dot in a segment)
import createMiddleware from 'next-intl/middleware';
import {routing} from './i18n/routing';

export default createMiddleware(routing);

export const config = {
  matcher: '/((?!api|audit|brain|_next|_vercel|.*\\..*).*)'
};
