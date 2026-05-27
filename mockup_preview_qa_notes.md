# Mockup-driven frontend preview QA notes

## 2026-05-27

The Georgian home page preview was opened at the public temporary preview URL. The generated Concept B family-safe portal is visible: left family map panel, central soft glass hero, right AI copilot panel, journey map, insight cards, and safety boundary.

A visual issue was found on the first pass: the Georgian hero headline was too large for the three-column layout and clipped horizontally. The hero title class was updated from fixed `sm:text-6xl lg:text-7xl` sizing to a controlled clamp-based typography with `break-words`, `leading-[0.98]`, and `max-w-none`.

After the fix, the Georgian hero headline renders inside the central card without horizontal clipping. It remains visually large and close to the generated image mockup style while being readable in the browser viewport.

Preview screenshots recorded by the browser:

- Before fix: `/home/ubuntu/screenshots/3000-im1fpejvr6f3yt0_2026-05-27_02-35-08_4630.webp`
- After fix: `/home/ubuntu/screenshots/3000-im1fpejvr6f3yt0_2026-05-27_02-36-26_4588.webp`

## Additional page checks

The Georgian Dashboard page was opened at `/ka/dashboard`. It renders as the dark Concept A clinical command center: left operations summary, central glowing network/brain card, right assistant panel, KPI tiles, pipeline, hypothesis status, activity rail, and evidence intelligence sections. No visible runtime error appeared. Screenshot: `/home/ubuntu/screenshots/3000-im1fpejvr6f3yt0_2026-05-27_02-37-28_1764.webp`.

The Georgian Brain page was opened at `/ka/brain`. It renders as the Concept C digital twin lab: large dark hero, view-mode pills, layer controls, central glowing brain/lab visual, evidence links, scan scrubber, viewer status, and safety boundary. No visible runtime error appeared. Screenshot: `/home/ubuntu/screenshots/3000-im1fpejvr6f3yt0_2026-05-27_02-37-41_1488.webp`.
