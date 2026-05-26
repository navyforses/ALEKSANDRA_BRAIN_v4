// next-intl proxy (Next.js 16 + next-intl 4.x file convention) +
// Phase 7.5 Rule #1 constitutional middleware merged in.
//
// Why a single file: Next.js 16 + next-intl 4.x mandate one of
// {middleware.ts, proxy.ts} per project, not both. Phase 7.5 originally
// shipped a sibling middleware.ts; the build then refused with
// "Both middleware file and proxy file are detected". Merge resolves it.
//
// Responsibilities (in order):
//   1. Rule #1 — reject MRI/DICOM POSTs to /api/* with HTTP 415.
//   2. next-intl locale routing for non-API paths.
//   3. Inject strict Content-Security-Policy on every response.
//
// Reference:
//   - v7_architecture/70_PHASES/75_PHASE_7_5_CONSTITUTIONAL_2W.md §2.1
//   - .claude/agents/v7-constitution.md Rule #1
//   - viewer/proxy.ts pre-merge (next-intl-only)
//   - viewer/middleware.ts pre-merge (deleted post-merge)
import createMiddleware from 'next-intl/middleware';
import {NextRequest, NextResponse} from 'next/server';
import {routing} from './i18n/routing';

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
// Wrapped next-intl proxy
// ---------------------------------------------------------------------------
const intlProxy = createMiddleware(routing);

function injectCsp(res: NextResponse): NextResponse {
  res.headers.set('Content-Security-Policy', CSP_HEADER_VALUE);
  return res;
}

export default function proxy(
  req: NextRequest,
): NextResponse | Promise<NextResponse> {
  const pathname = req.nextUrl.pathname;

  // Rule #1 inspector — fires before any routing.
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

  // API paths skip next-intl (no locale prefix needed) but still get CSP.
  if (pathname.startsWith('/api/')) {
    return injectCsp(NextResponse.next());
  }

  // Everything else: next-intl handles locale routing, then CSP layered on.
  const intlResult = intlProxy(req);
  if (intlResult instanceof Promise) {
    return intlResult.then(injectCsp);
  }
  return injectCsp(intlResult);
}

// Matcher: broad enough to cover API (for Rule #1) + locale routes + every
// non-asset path needing CSP. Excludes static files + _next + _vercel.
export const config = {
  matcher: '/((?!_next|_vercel|.*\\..*).*)',
};

// Exported for unit tests; not consumed by Next.js itself.
export const __CSP_HEADER_VALUE__ = CSP_HEADER_VALUE;
export const __FORBIDDEN_UPLOAD_CONTENT_TYPES__ = FORBIDDEN_UPLOAD_CONTENT_TYPES;
