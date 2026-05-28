# Local Visual Validation Notes

Date: 2026-05-28

## Local `/ka` dashboard

The Georgian dashboard at `http://127.0.0.1:3002/ka` renders as a dark command-center interface. The left sidebar contains the compact navigation groups, the top bar shows the live data stream controls, and the right BRAIN assistant panel remains visible. The central content shows the new animated/data-oriented dashboard: neural field hero, live metric tiles, evidence-to-hypothesis pipeline, donut-style source charts, research domain bars, and timeline. The visual style is dark, neon-accented, data-dense, and aligned with the requested command-center direction.

## Local `/ka/hypotheses` submenu page

The Georgian hypotheses page at `http://127.0.0.1:3002/ka/hypotheses` renders with the same shell and a dark topic dashboard. The page shows the hero block, live metric tiles, an operational matrix, checked aside items, and compact data cards. Navigation remains functional and the right assistant panel remains present.

## Build and route status

`npm run build` completed successfully. HTTP smoke tests returned `200` for `/ka`, all Georgian menu pages, and `/minimal`.


## Final local visual validation — 2026-05-28

Local production server: `http://127.0.0.1:3002`.

| Route | Result | Notes |
|---|---:|---|
| `/ka` | Pass | Dark animated command-center dashboard rendered correctly. Georgian-first sidebar, metric cards, timeline status, assistant panel, and research-only notice are visible. Remaining `English` label is the intentional language switch button. Screenshot: `/home/ubuntu/screenshots/127_0_0_1_2026-05-28_18-44-31_5724.webp`. |
| `/ka/hypotheses` | Pass | Dark topic layout rendered correctly with Georgian heading, metrics cards, operational matrix, checklist cards, and right-side BRAIN assistant panel. Screenshot: `/home/ubuntu/screenshots/127_0_0_1_2026-05-28_18-44-41_5474.webp`. |

Additional final validation completed after the Georgian-first label fixes:

| Check | Result |
|---|---:|
| `npm run build` | Pass |
| Georgian route HTTP smoke tests | Pass, all tested routes returned `200` |
| `/minimal` HTTP smoke test | Pass, returned `200` |

Tested routes: `/ka`, `/ka/dashboard`, `/ka/brain`, `/ka/hypotheses`, `/ka/hypotheses/mitochondrial-dysfunction`, `/ka/evidence-map`, `/ka/therapies`, `/ka/cohorts`, `/ka/data-integrations`, `/ka/papers`, `/ka/alerts`, `/ka/resources`, `/ka/how-it-works`, `/ka/support`, `/ka/audit`, `/ka/settings`, `/ka/timeline`, `/minimal`.


## Production verification — 2026-05-28

Production URL: `https://viewer-sigma-two.vercel.app`.

| Route | Result | Notes |
|---|---:|---|
| `/ka` | Pass | Production dashboard renders the dark animated command-center interface with Georgian-first navigation, metric tiles, evidence-to-hypothesis pipeline, research charts, live timeline, and right-side BRAIN assistant panel. Screenshot: `/home/ubuntu/screenshots/viewer-sigma-two_ver_2026-05-28_18-47-30_3174.webp`. |
| `/ka/hypotheses` | Pass | Production hypotheses submenu renders the dark topic layout with Georgian hero copy, metric cards, operational matrix, checklist blocks, and BRAIN assistant panel. Screenshot: `/home/ubuntu/screenshots/viewer-sigma-two_ver_2026-05-28_18-47-41_6850.webp`. |

Production HTTP smoke tests returned `200` for every tested route: `/ka`, `/ka/dashboard`, `/ka/brain`, `/ka/hypotheses`, `/ka/hypotheses/mitochondrial-dysfunction`, `/ka/evidence-map`, `/ka/therapies`, `/ka/cohorts`, `/ka/data-integrations`, `/ka/papers`, `/ka/alerts`, `/ka/resources`, `/ka/how-it-works`, `/ka/support`, `/ka/audit`, `/ka/settings`, `/ka/timeline`, and `/minimal`.

## Typography refinement validation — 2026-05-28

After the Georgian typography/copy refinement, the local production dashboard at `http://127.0.0.1:3002/ka` was visually checked again. The hero heading is now title case (`Aleksandra Brain`) instead of spaced uppercase branding, Georgian labels are shorter, the right assistant panel uses `კვლევის ასისტენტი` and `ჰკითხე ასისტენტს...` instead of BRAIN-heavy Georgian copy, and the UI reads as calmer and less crowded while retaining the dark command-center layout.

Build validation: `npm run build` completed successfully after the final copy fixes. Local HTTP smoke tests returned `200` for `/ka`, `/ka/dashboard`, `/ka/brain`, `/ka/hypotheses`, `/ka/therapies`, `/ka/timeline`, `/ka/evidence-map`, `/ka/cohorts`, `/ka/data-integrations`, `/ka/papers`, `/ka/alerts`, `/ka/resources`, `/ka/how-it-works`, `/ka/support`, `/ka/audit`, `/ka/settings`, and `/minimal`.

Local screenshot: `/home/ubuntu/screenshots/127_0_0_1_2026-05-28_19-02-54_8244.webp`.

## Production typography refinement verification — 2026-05-28

Production URL: `https://viewer-sigma-two.vercel.app`.

| Route | Result | Notes |
|---|---:|---|
| `/ka?typography_check=verified` | Pass | Live dashboard shows the refined typography: `Aleksandra Brain` instead of uppercase spaced branding, shorter Georgian labels, calmer hero copy, and the right panel now reads `კვლევის ასისტენტი`. Screenshot: `/home/ubuntu/screenshots/viewer-sigma-two_ver_2026-05-28_19-04-53_3716.webp`. |
| `/ka/hypotheses?typography_check=verified` | Pass | Live hypotheses page shows shorter Georgian headline/copy and the same calmer assistant panel and navigation. Screenshot: `/home/ubuntu/screenshots/viewer-sigma-two_ver_2026-05-28_19-05-05_4082.webp`. |

GitHub workflow checks for commit `2774d1a` completed successfully: Secret Scan and Trust Boundary Lint both passed. Production HTTP checks returned `200` for `/ka`, `/ka/hypotheses`, and `/minimal` after the typography refinement push.
