# Concept Input 06 — Motion Language for v8

**Author**: design-motion
**Date**: 2026-05-25
**Status**: Wave 2 deliverable for fresh-site-concept-v1
**Scope**: current motion inventory, reduced-motion BLOCK response, 3×3 canon proposal, page-transition call, framer-motion threshold, two binary decisions for Shako

---

## 6.1 Current state — restraint or under-supply?

The inventory is genuinely small: two keyframes (`shimmer` 1.8s, `pulse-soft` 50% scale) and one SVG `.group`-scoped hover (`circle r`, `rect scaleY(1.03)`, both `cubic-bezier(0.4, 0, 0.2, 1)` over 250ms). Outside `globals.css`, dashboard uses Tailwind's stock `animate-pulse` / `animate-ping` on live-status dots. That is the entire palette across 14 routes.

**Verdict: the restraint is correct, the discipline is broken.** Restraint is the right philosophy for a medical-family product — Linear ships near-zero motion in its marketing surface and reads as luxurious because of it, not in spite of it. Under-supply is not the problem; the problem is that none of this motion is reduced-motion-aware (Grep: zero `prefers-reduced-motion` matches anywhere in the repo, confirmed in a11y BLOCK B4), there is no canon to govern future additions, and the two surviving keyframes use ad-hoc cubic-beziers that no one else can reuse. We are restrained for the wrong reason — we have not built a motion system, so motion is rare by accident.

## 6.2 Reduced-motion BLOCK response (the load-bearing answer)

This is the first-order concern. v8 ships ONE rule before any other motion work, dropped into `globals.css` immediately after the `body` block:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

This is the WCAG-compliant default — **instant state change, not slow**. `0.01ms` is the convention (zero can break listeners that expect `transitionend`). It uses `!important` because component-level transition utilities will otherwise outrank it under Tailwind 4's cascade order. The `scroll-behavior` clause closes the scroll-jacking door before we ever open it.

Companion utility for cases where a static "live" indicator must still convey *liveness* without motion (dashboard status dots fall into this — they should not silently die when reduced motion kicks in):

```css
@utility motion-safe-pulse {
  @media (prefers-reduced-motion: no-preference) {
    animation: pulse-soft 2s ease-standard infinite;
  }
}
```

Pattern: every animated component opts IN via `motion-safe-*` rather than opting OUT via `motion-reduce:`. The global rule above is the hard floor; utilities are the explicit lift. Components that need "live" semantics without motion (status dot) use a static-state visual treatment (slightly darker fill, `aria-label="live"`) that survives the reduce. No motion sneaks through unaccounted.

## 6.3 v8 canon proposal — codify the 3 × 3?

**Recommendation: YES.** Add seven tokens to `globals.css`. They cost nothing at runtime and convert the agent's standard into something component code can actually consume.

```css
@theme {
  --duration-reactive: 100ms;
  --duration-transitional: 200ms;
  --duration-emphasized: 300ms;

  --ease-standard: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-emphasized: cubic-bezier(0.2, 0, 0, 1);
  --ease-decelerate: cubic-bezier(0, 0, 0.2, 1);

  --color-shimmer-bg: hsl(var(--muted));
}
```

Three migrations land alongside: (a) the SVG `.group` rules switch from inline `0.25s cubic-bezier(0.4, 0, 0.2, 1)` to `var(--duration-transitional) var(--ease-standard)`; (b) `shimmer-loading` uses `var(--color-shimmer-bg)` instead of the off-palette `#f5f5f4` (closes systems-lead's brittleness item 4); (c) any new `transition:` in component CSS or Tailwind arbitrary value must reference these tokens — lint rule recommended. Adding a 4th timing or 4th easing requires written sign-off from design-director + design-systems-lead. The canon is closed.

## 6.4 Page transitions for v8 — add or stay absent?

**Recommendation: stay absent.** Do not add a route fade.

Rationale: Next.js 16 App Router gives instant navigation; a 100ms fade adds perceived latency where none existed, and the wife persona on a phone with intermittent connectivity benefits from the current honesty (page paints when it can). Linear ships zero route motion. Raycast ships zero route motion. Our cockpit-register peers ship zero. If a specific surface later earns a transition (the MRI viewer's first-open hero is the only candidate I can defend), it is a per-surface decision routed through design-director — not a global default. Reserve the 300ms `emphasized` slot for true attention moments (new question arrival, agent finishing a long-running task) where the motion *informs*, not decorates.

## 6.5 framer-motion threshold (or permanent no?)

**Recommendation: permanent no for v8 and v9. Conditional yes after that, on ONE trigger only.**

The trigger: **layout-aware shared-element transitions on the MRI viewer** (e.g., a thumbnail expanding into a full-volume render while preserving its bounding box). CSS cannot orchestrate FLIP-style cross-component transitions; framer-motion's `LayoutGroup` + `motion.div layoutId` is the canonical solution. No other use case justifies the bundle (~30–40KB gzipped) or the React-render overhead.

Anything else framer would buy us — spring physics, scroll-linked animation, gesture choreography — is a sign we are doing the wrong thing. Spring physics on a medical surface is decorative. Scroll-linked motion is parallax by another name. Gestures are out-of-register for a keyboard-first cockpit.

So the answer is: CSS-first is the permanent default. framer-motion is invoked only if and when the MRI viewer ships shared-element morphing — and even then, it is scoped to the viewer route, not loaded globally. Until that trigger fires, treat any framer-motion PR as a regression.

## 6.6 Two motion decisions Shako must make

1. **Land the global `prefers-reduced-motion` block in `globals.css` as part of the v8 token-foundation phase (NOT as a follow-on)?**
   *Recommendation: **YES.*** This is the a11y BLOCK B4 fix and the prerequisite for any other motion work. ~10 lines of CSS, no visual change for default users, no risk. It must ship before any new animated component lands or we re-accrue debt instantly. Pair with the global `*:focus-visible` rule the a11y input flagged as F9 — same `globals.css` change, same review.

2. **Lock the 3 timings × 3 easings as the canon and forbid framer-motion until the MRI shared-element trigger fires?**
   *Recommendation: **YES.*** Codify the seven tokens, write the rule into `viewer/DESIGN.md` under § Motion (design-motion contributes that section per the agent canon), and treat any future motion-library proposal as a director-gated decision. The cost of saying yes to framer-motion early is high (bundle + render + Pandora's box of "while we're here let's animate this"); the cost of saying yes late is zero (CSS keyframes are easy to delete when framer takes over a specific surface).

---

**Hand-off note to design-director**: the two calls above are the load-bearing motion-strategy decisions for v8. Items in 6.2 (reduced-motion global), 6.3 (token additions), and the SVG migration in 6.3 are design-motion-owned and ship under the v8 token-foundation phase without Shako sign-off. The Sunday-morning brief surface explicitly inherits the reduced-motion default — wife persona reads on phone, often in low light, never wants pulsing chrome.
