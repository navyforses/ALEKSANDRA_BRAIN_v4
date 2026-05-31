# Concept Input 03 — Visual + Token Direction

**Author**: design-systems-lead
**Date**: 2026-05-25
**Status**: Wave 1 deliverable for fresh-site-concept-v1
**Scope**: token state audit, register check, dark-mode position, shadcn position, palette open/close call, typography call, three token decisions for Shako

---

## 3.1 Current token state — what holds up, what's brittle

`viewer/app/globals.css` is 129 lines. Honest read: the token foundation is small, disciplined, and **mostly correct** for month 9. What holds:

- The closed semantic palette (`--color-medical-*`, 6 entries) is unambiguous, conservative, and consistent with the constitutional rule that red = lesion / green = confirmed evidence.
- The `--radius: 0.5rem` lock with derived `radius-md` / `radius-sm` via `calc()` is the right way to express a single scale.
- Inter as the single UI face with system fallback is sustainable and ships with workable Georgian glyphs.
- The `--panel: 210 40% 98%` slate-tint for the BRAIN panel is a smart neutral lift — it lets us separate the 35% BRAIN column from the 65% content column without a border.

What is **brittle**:

1. **HSL-only color space.** Every variable is HSL, not OKLCH. This blocks honest dark-mode work (HSL is non-perceptually-uniform; equal lightness steps look unequal across hues), prevents the tinted-neutral discipline Impeccable mandates, and forces ad-hoc contrast math when we add states.
2. **Medical 6 are raw hex literals**, not tokens-in-HSL/OKLCH. They don't participate in the same theming surface as everything else. They cannot be re-derived for dark mode without rewriting each one by hand.
3. **No state tokens.** No hover, focused, pressed, disabled, or selected variants of anything. Components currently hard-code these in TSX — a slow drift bomb.
4. **Shimmer uses `#f5f5f4`** (line 88) — an off-palette hex that bypasses the system entirely. First and only token-system breach in the file. Needs to move to `--color-shimmer-bg`.
5. **`--background: 0 0% 100%`** is pure white. The hard-rule file says we forbid pure white. The token is a violation we have grandfathered. v8 should fix.
6. **No elevation, no shadow, no easing tokens.** Motion lives entirely in component CSS. Once design-motion proposes a canon, it needs a home here.

The system is a **good v1 skeleton** that has not yet earned the right to call itself a design system. v8 is the right moment to upgrade it.

## 3.2 Mayo-clean register at month 9 — keep, evolve, or break?

**Recommendation: evolve, do not break.** Hold the Mayo-clean / Linear-crisp register as the *product* register. Earn a tighter, quieter identity by doing two things v8 has not yet done:

1. **Tinted neutrals**, not pure white / pure gray. Triangulate from Linear (`#010102` faint-blue tint), Vercel (`#fafafa` near-white canvas, never `#ffffff` for body), and Notion (`#fafaf9` warm soft-surface). The current `--background: 0% 100%` is the laziest possible canvas. v8 should adopt a faintly cool-tinted canvas (toward our `--ring` clinical blue at hue ~222) at ~99% lightness — visible only subliminally, but it cures the "AI-generated white site" feel.
2. **Surface ladder**, not single panel. Linear runs four surface steps (canvas → surface-1 → surface-2 → surface-3) and carries all hierarchy from that ladder. We have one panel level. v8 needs two: a card surface (between body and panel) and a deeper-inset surface (for nested code blocks, audit log rows, dataviz cells).

What we **do not** evolve toward: Notion's pastel feature tints (off-register for clinical), Vercel's hero mesh gradient (decorative, off-tone), Linear's pure-dark canvas (we are not a dark product yet). Our distinctive identity at month 9 is **calm clinical density** — and the register that fits is closer to Stripe Docs than to any of the three triangulation references. Keep the Linear-quiet voice. Add Notion-grade surface ladder discipline. Skip Vercel's atmospheric chrome.

## 3.3 Dark mode position for v8

**Recommendation: v8-token-foundation-only. Ship the OKLCH token migration, do NOT ship the dark theme.**

Rationale: dark mode is a six-week project done right (palette redefinition for all 6 medical semantics + neutrals + state colors + dataviz palette + MRI viewer behavior decision + per-component review). The 2-day v7 sprints we've shipped show what we have bandwidth for. Adding "dark mode" to v8 risks shipping it broken (medical-red looking pink on dark, dataviz unreadable, lesion overlays inverted).

But the **token migration is independent** and ships standalone benefit even without a theme switch:

- Migrate HSL → OKLCH for all neutrals (Impeccable: `oklch(L C H)`, neutrals at chroma 0.005-0.015 tinted toward our clinical blue hue ~243).
- Express the medical 6 in OKLCH alongside their hex (keep hex as the canonical chart token for D3/Plotly libraries that don't accept OKLCH directly; OKLCH becomes the source-of-truth for CSS).
- Add the semantic-token layer: `--color-text-primary`, `--color-text-secondary`, `--color-text-tertiary`, `--color-surface-card`, `--color-surface-inset`, `--color-border-default`, `--color-border-strong`. These map to the OKLCH primitives in `:root`. **Only the semantic layer redefines for dark mode** (Impeccable's recommended two-layer pattern).

Then v9 ships dark theme by overriding only the semantic layer. No primitive changes needed. MRI viewer stays dark by default regardless of theme (that's a viewer-tokens decision, separate from app theme).

## 3.4 shadcn adoption position

**Recommendation: yes-when-trigger-X.** The trigger: when we ship our 4th hand-rolled overlay primitive (dropdown menu, command palette, dialog, popover, tooltip).

We currently have zero of these. Phase 7.6 plus the IA proposal from design-product will likely demand: command palette (keyboard-first), `Select` (filters across hypotheses / papers / therapies), `Dialog` (causal SCM editor, simulation studio configuration), `Tooltip` (provenance citations on family-facing surfaces), `DropdownMenu` (action rows in audit log). That is 5 overlay primitives.

Hand-rolling 5 a11y-correct overlays (focus trap, escape handling, scroll lock, portal rendering, ARIA, keyboard nav) is **not** $2/feature — it's $20-40/feature done correctly, and we will get it subtly wrong on at least 2 of them. shadcn (Radix under the hood) gives us the a11y for free. The cost is one large dependency surface (Radix primitives).

**Threshold call**: when the third overlay primitive ships, we adopt shadcn with a migration plan that covers only the primitives we use. We do NOT adopt the full shadcn registry. Cards, buttons, badges stay hand-rolled (they are token-thin and we already own them). Bundle impact: ~30-50KB for tree-shaken Radix primitives — acceptable.

Director sign-off required. I propose: defer adoption decision to Wave 2 (after design-product names how many overlay primitives the IA needs).

## 3.5 Medical 6 palette — open, closed, or expand?

**Recommendation: keep closed at 6. The palette is correctly-sized.**

Audit of usage across 14 routes shows the 6 cover: lesion / urgent (red), confirmed evidence (green), pending / warning (orange), agent reasoning / hypothesis (purple), action / link / brain (blue), info / drug-class neutral (yellow). No surface is starved.

The temptation to add a 7th is **teal** for "treatment / therapy" — but treatment surfaces already use medical-green (confirmed) or medical-purple (hypothesis) appropriately. Adding teal dilutes the distinction.

What v8 SHOULD add is **tonal variants** within the existing 6: each color gets a `-soft` background tint (12-15% lightness lift toward canvas) and a `-deep` text-on-tint pair. So `medical-red-soft` = pale rose for "lesion area chip background"; `medical-red-deep` = a darker red for text on that soft fill. This is not a 7th color — it's the missing intra-color scale that Notion and Vercel both ship. 6 colors × 3 tones = 18 entries, still closed. Justification gets written into `viewer/DESIGN.md` as the v8 expansion.

## 3.6 Typography for v8 — Inter forever, or display face for hero moments?

**Recommendation: Inter forever for the product surface. Do NOT introduce a Mkhedruli display face.**

Reasoning:

- Inter ships competent Georgian glyphs. They are not beautiful — they read as Latin-designer's-take-on-Mkhedruli. But they are correct, hint well at small sizes, and pair visually with the Latin without a family swap.
- Introducing a Mkhedruli display face (BPG Nino Mtavruli, FiraGO, Noto Sans Georgian) means: dual font loading, weight-pair calibration per locale, a parallel type ramp, and an aesthetic decision that we are not staffed to QA across the wife's Mkhedruli weekly-brief surface. Risk-to-reward is bad.
- The hero moments we DO have (landing, weekly brief preview, family handover, MRI first-open, Telegram digest) are quiet — they are typographically still product-register, not brand-register. The brief explicitly says brand-register is reserved for these moments. None of them need display-face heroics. Tighter tracking + larger size in Inter does the job.

What v8 SHOULD do: formalize a **type ramp** in tokens — `--font-size-display-xl` (40px / -1px tracking), `--font-size-display` (28px / -0.5px), `--font-size-h1` (22px / -0.3px), through to `--font-size-caption` (12px / 0). Currently TSX hard-codes Tailwind utility classes for every text element. The ramp lives in `globals.css` as `@theme` entries; component TSX consumes named tokens. This is the most impactful typography improvement for v8, larger than any font choice.

Mkhedruli-specific display face: **revisit at v9** if the wife provides feedback that the Georgian rendering feels off. Until then, the hard rule holds.

## 3.7 Three token decisions Shako must make

These are binary, owner-level calls. design-systems-lead recommends; Shako signs.

1. **Migrate HSL → OKLCH in v8?** (Recommendation: **YES.** Foundation for dark mode v9, fixes contrast math, enables tinted neutrals. ~2 days of work, no visual change. Risk: low.)

2. **Adopt shadcn at the 3rd overlay primitive trigger?** (Recommendation: **YES, conditional.** Defer the trigger-count decision to Wave 2 after design-product names IA overlay needs. Director sign-off required because Radix is a new heavy dep. Risk: medium — bundle growth, but a11y gains outweigh.)

3. **Add tonal `-soft` / `-deep` variants to the medical 6 (6 → 18 entries, still closed) in v8?** (Recommendation: **YES.** This is the missing intra-color scale that unlocks chip backgrounds, banner fills, and text-on-tint without breaking the closed-palette rule. ~1 day of work + DESIGN.md justification entry. Risk: low.)

---

**Hand-off note to design-director**: the three calls above are the load-bearing token-strategy decisions for v8. The other recommendations (surface ladder, type ramp, state tokens, shimmer-bg cleanup, pure-white removal) are systems-lead-owned and ship under the v8 token-foundation phase without requiring Shako-level sign-off.
