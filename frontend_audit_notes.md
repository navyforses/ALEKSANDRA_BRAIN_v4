# Frontend audit notes — ALEKSANDRA_BRAIN_v4

Visual checks were performed locally on `http://localhost:3000/en/dashboard` and `http://localhost:3000/en/hypotheses` after a successful `npm run build`.

## Confirmed technical state

The app builds successfully with Next.js 16.2.6 and Turbopack. `npm ci` fails because `package-lock.json` is not synchronized with `package.json`; `npm install` updates dependencies and allows the build to pass. There is no `lint` script in `package.json`, although ESLint dependencies are present.

## Key UX observations

Both dashboard and hypotheses pages have duplicated navigation: the shared top navigation in `app/[locale]/layout.tsx` plus an in-page navigation block inside each page. This consumes vertical space, creates two competing active-navigation concepts, and is especially inefficient because the main content already has a persistent right BRAIN panel.

The layout uses a 65% main content / 35% sidebar split on desktop. This is useful for a persistent research assistant panel, but in the current state the BRAIN panel mostly shows an unreachable Activity Log HTTP 503 message and an email draft input, so it takes substantial screen space without enough operational value.

The dashboard is clean and readable, but empty-state messaging is too repetitive when Supabase is not configured. Each metric card repeats the same configuration error, making the page feel broken rather than intentionally in setup mode.

The hypotheses page has a practical curator workflow in code, but with no data it only shows the setup warning and empty list. When data is present, the current card design is likely to become dense because each hypothesis includes status, metadata scores, supporting-paper count, textarea, and three review buttons in one card.

## Initial implementation priorities

1. Remove or replace duplicated in-page nav with a compact page header/action bar, relying on the shared top navigation.
2. Add reusable UI primitives for cards, alerts, metric cards, and status badges to reduce repeated Tailwind class strings.
3. Improve setup and empty states so missing Supabase config appears once as a clear system banner, not repeated in every metric.
4. Make the BRAIN side panel more practical: either collapse it by default when inactive/erroring or add actionable quick commands and a more resilient activity feed state.
5. Add developer workflow scripts: `lint`, `typecheck`, and maybe `check` so future changes are safer.

## 2026-05-27 frontend pass

After removing duplicated page-level navigation from `dashboard` and `hypotheses`, both pages now show only the global application navigation in the shell. The setup and empty states are clearer when Supabase variables are absent: dashboard metric cards show a neutral configuration-pending message, and the hypotheses page avoids exposing raw environment-variable error text to family users.

Visual check paths:

- Dashboard screenshot: `/home/ubuntu/screenshots/localhost_2026-05-27_01-08-54_1675.webp`
- Hypotheses screenshot: `/home/ubuntu/screenshots/localhost_2026-05-27_01-09-04_7364.webp`

Validation: `npm run build` passed successfully in `viewer` after the changes.

Developer workflow improvement: added `lint`, `typecheck`, and `check` scripts to `viewer/package.json`. The full `npm run check` chain passed: ESLint, TypeScript no-emit check, and production build all completed successfully.
