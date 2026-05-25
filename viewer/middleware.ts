// Phase 7.5 Rule #1 — Constitutional middleware: MRI / DICOM client-only.
//
// This file is ADDITIVE to the existing `proxy.ts` (Next.js 16 i18n entry).
// Responsibilities (constitutional, NOT i18n):
//
//   1. Inject a strict Content-Security-Policy header on every response so
//      a browser cannot exfiltrate MRI / DICOM bytes to a third party even
//      if a downstream component is compromised.
//
//   2. Inspect every POST to `/api/*` and refuse, with HTTP 415, anything
//      whose Content-Type indicates DICOM or generic binary that could be
//      a MRI upload (`application/dicom`, `application/octet-stream`).
//
// The existing i18n behaviour (locale prefix, routing) is preserved in
// `proxy.ts` — that file owns the `/((?!api|_next|_vercel|.*\\..*).*)`
// matcher; this middleware owns `/api/:path*` plus `/:locale/:path*`
// (CSP-only on the locale side, full inspect on the API side).
//
// Phase 6.1 i18n + Phase 7.5 Rule #1 coexist: proxy.ts handles locale
// rewrites for non-API routes; middleware.ts adds CSP everywhere and
// blocks MRI POSTs to API paths.
//
// Reference:
//   - v7_architecture/70_PHASES/75_PHASE_7_5_CONSTITUTIONAL_2W.md §2.1
//   - .claude/agents/v7-constitution.md Rule #1 row
//   - viewer/proxy.ts (i18n proxy — DO NOT REPLACE)

import {NextRequest, NextResponse} from 'next/server';

// ---------------------------------------------------------------------------
// CSP — strict baseline. Phase 7.6 frontend may relax script-src once a
// nonce-based policy is wired (NiiVue + R3F bundles).
// ---------------------------------------------------------------------------
const CSP_HEADER_VALUE = [
  "connect-src 'self' https://*.supabase.co https://api.anthropic.com",
  "img-src 'self' blob: data:",
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
].join('; ');

// ---------------------------------------------------------------------------
// MRI / DICOM upload detector
// ---------------------------------------------------------------------------
const FORBIDDEN_UPLOAD_CONTENT_TYPES = [
  'application/dicom',
  'application/octet-stream',
];

function isMriUploadAttempt(req: NextRequest): boolean {
  if (req.method !== 'POST') {
    return false;
  }
  const ct = (req.headers.get('content-type') || '').toLowerCase();
  return FORBIDDEN_UPLOAD_CONTENT_TYPES.some((forbidden) =>
    ct.includes(forbidden),
  );
}

// ---------------------------------------------------------------------------
// Entrypoint
// ---------------------------------------------------------------------------
export function middleware(req: NextRequest): NextResponse {
  const pathname = req.nextUrl.pathname;

  // Rule #1 inspector: API uploads carrying DICOM / octet-stream are refused.
  // Body is NOT inspected — header alone is enough; the family upload UI is
  // built on `<input type="file" accept=".nii,.nii.gz">` + client-side parse.
  if (pathname.startsWith('/api/') && isMriUploadAttempt(req)) {
    return NextResponse.json(
      {
        error: 'MRI/DICOM uploads forbidden — client-side only',
        rule: 1,
        phase: '7.5',
      },
      {status: 415},
    );
  }

  // All other requests: pass through with CSP injected on the response.
  const res = NextResponse.next();
  res.headers.set('Content-Security-Policy', CSP_HEADER_VALUE);
  return res;
}

// Matcher: only fire on API routes + locale-prefixed routes. The static-file
// + _next exclusions stay in proxy.ts's matcher; this middleware piggy-backs
// on the request flow without competing for those paths.
export const config = {
  matcher: ['/api/:path*', '/:locale/:path*'],
};

// Exported for unit tests (jest / vitest); not consumed by Next.js itself.
export const __CSP_HEADER_VALUE__ = CSP_HEADER_VALUE;
export const __FORBIDDEN_UPLOAD_CONTENT_TYPES__ = FORBIDDEN_UPLOAD_CONTENT_TYPES;
