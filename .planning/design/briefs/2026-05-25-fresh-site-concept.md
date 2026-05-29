# Brief: ALEKSANDRA_BRAIN Fresh Site Concept

**Date**: 2026-05-25
**Author**: design-director (drafted via Shako instruction)
**Status**: ACTIVE — Wave 1 dispatch authorized

---

## Why this brief exists

ALEKSANDRA_BRAIN has shipped 14 routes across 6 closed phases (Perception → Memory → Cognition → First Family Value → Manager → i18n + polish) plus an in-progress v7 sprint (Bayesian / Causal / Simulation / Active Learning / Constitution / Site Refactor / Acceptance). The product works. Shako uses it daily. The wife reads it weekly. Phase 7.6 will add 4 new routes + refactor 4. But the **visual + structural concept** has accreted feature-by-feature; it has never been re-drawn from a fresh-start vision.

Shako has called the design studio for a **strategic concept session**. The goal is a single document that answers: **what kind of site do we want, three years from now, given what we now know about the family's daily reality + the v7 capabilities coming online?**

This is **not** a redesign commitment. It is a vision exercise that will inform v8 planning, Phase 7.6 layout decisions, and the dark-mode + shadcn + framer-motion adoption questions that have been deferred.

---

## Output: ONE document

`.planning/design/concept/2026-05-25-fresh-site-concept-v1.md`

The director composes the final doc by synthesizing specialist deliverables. The doc has these sections (specialist-owned columns indicated):

| Section | Owned by | Length |
|---|---|---|
| 1. Audience refresh | design-ux-researcher | ~800 words |
| 2. Voice + register strategy | design-content-bilingual | ~600 words |
| 3. Visual + token direction | design-systems-lead | ~800 words |
| 4. Information architecture proposal | design-product | ~1000 words |
| 5. Dataviz strategy across surfaces | design-dataviz | ~500 words |
| 6. Motion language | design-motion | ~400 words |
| 7. 3D / MRI viewer strategy | design-webgl-3d | ~600 words |
| 8. Accessibility-first principles | design-a11y | ~400 words |
| 9. Synthesis: 5 site-level decisions to make | design-director | ~600 words |
| 10. Technical capability gaps to fill | design-director (with specialist input) | ~500 words |

Target total: **~6200 words, ~30KB single doc**. Family-readable in EN, with KA section headings.

**No UI-SPECs. No mockup TSX. No code.** This round is strategy only. The next round (after Shako reviews this doc) will produce specs for the top-priority surfaces.

---

## Scope of the concept

### IN scope

- The full family-facing surface area (14 current routes + the 4 Phase 7.6 NEW routes once they exist)
- Visual concept: tokens, type, color, density, register
- Information architecture: route map, nav patterns, surface relationships
- Voice: EN tone + KA voice direction across audiences
- Dataviz strategy: where charts matter, what semantics, what library choices
- Motion language: canon of timings/easings, restraint policy, hero moments
- 3D / MRI viewer strategy: when to introduce NiiVue + R3F, prioritization
- Accessibility-first principles
- Technical capability gaps (dark mode? shadcn? framer-motion? PWA? offline? real-time?)

### OUT of scope (deferred for future rounds)

- Per-surface UI-SPECs
- Mockup TSX
- Production component implementations
- Backend API changes (the data contracts from v7-bayes / v7-causal / v7-neurosim are taken as given)
- Brand identity work (logo, mark)
- Phase 7.6 execution plan (already exists)

---

## Audience context (read before drafting)

These three personas are the load-bearing constraints. The concept must serve all three without diluting any one of them.

1. **Shako (developer-operator, KA)** — Primary daily user. Edits code, dispatches agents, decides what to ship. Reads dense info, keyboard-first, tolerates jargon. Surfaces: today, dashboard, audit, hypotheses, papers, therapies, timeline, twin, drift, causal, simulate, brain, inbox.

2. **Wife (warm morning ritual, KA)** — Reads weekly brief every Sunday morning. Occasional Telegram alerts. Audience for Family Inbox + Family Handover. Reads narrative, not tables. Plain language. No clinical jargon. Voice: warm, concrete, hopeful but evidence-based. Pain: emotional load is high; UI must not add cognitive burden on top of grief/hope cycle.

3. **Clinician (EN, 2-minute scan)** — Reads Family Handover PDF + occasionally doctor session prep doc. Time-boxed. Skims for citations and structure. Voice: clinical register, citation-forward, structural. Pain: distrusts AI-summarized medical content; only trusts surfaces that show provenance.

A fourth implicit audience: **future Shako six months from now** — when context has decayed and the system must explain itself to its own creator. The IA must serve this.

---

## Constraints the concept must honor

1. **Privacy**: MRI / DICOM data client-side only. Never persisted on a server. Any 3D viewer concept respects this absolute.
2. **Budget**: $20–30/mo MVP, $120/mo full. Adding heavy dependencies (shadcn, framer-motion, GSAP, Three.js outside R3F, lottie) requires justification.
3. **Tech stack** (current): Next.js 16.2.6 · React 19.2.4 · Tailwind 4 · next-intl 4 · @xyflow/react 12 · vis-network 10 · plotly.js-dist-min 3.5 · lucide-react · react-dropzone. **No shadcn yet. No framer-motion. No NiiVue/R3F yet.**
4. **Source integrity**: Every surfaced fact carries provenance. The concept must reinforce this discipline, not undercut it.
5. **Bilingual parity**: Every UI string lives in both `en.json` and `ka.json`. Mkhedruli runs ~10–15% longer than English; layout concept must absorb this.
6. **Decision authority**: Clinician makes every medical decision. System surfaces, ranks, explains. The concept must make this hierarchy visually unambiguous.
7. **HIPAA-aware**: Even though not a covered entity, posture is privacy-first.
8. **Time pressure**: Neuroplasticity window 0–2 years (Aleksandra is ~9 months as of May 2026). Concept ordering must front-load research throughput over polish.
9. **Tone**: "Unknown potential" never "limited outcomes." Calm, hopeful, evidence-based. Never decorative.
10. **Register policy** (from design-director.md): product-register default; brand-register accents reserved for hero moments (landing, weekly brief preview, family handover, MRI first-open, Telegram digest).

---

## Open questions for the team to explore

Each specialist picks the questions in their lane. The director synthesizes answers in section 9.

### For design-ux-researcher
- Are the three personas (Shako / wife / clinician) still right at month 9 of operation? Have new audiences emerged (extended family, grandparents, future therapist)?
- What does the Sunday weekly brief ritual actually look like now vs. how it was designed? Has it become habit, or is it ignored?
- What are the 3 most painful moments in Shako's daily ritual using the cockpit?
- Is the wife persona actually reading the weekly brief, or just receiving it on Telegram?

### For design-content-bilingual
- Where has voice drifted across the 14 routes? Which surfaces feel like a different product?
- Is "Unknown potential" reading as hopeful or as evasive at month 9?
- What's the right voice for the Telegram weekly digest preview message specifically? (it's the most-seen surface)
- How do we surface evidence provenance in copy without becoming citation-heavy on family-facing surfaces?

### For design-systems-lead
- Is the Mayo-clean palette + Linear-crisp white still the right register, or has the project earned a more distinctive identity?
- Dark mode: should v8 ship it? What's the OKLCH token strategy?
- shadcn adoption: at what cost/benefit threshold do we say yes?
- The medical 6-color semantic palette is closed; is it under-supplying? over-supplying?
- Typography: Inter has been the workhorse. Is a Mkhedruli-specific display face warranted for hero moments?

### For design-product
- IA: 14 routes is at the edge of memorable. Should v8 consolidate? Re-group? Add a top-level workspace concept?
- Brain panel takes ~35% of horizontal real estate on every authenticated route. Is this the right ratio at month 9? Should it collapse / dock / reposition?
- Cross-surface navigation: are users (Shako) building habits, or scrambling? What's the keyboard-shortcut layer look like?
- Hero surface (landing `/[locale]/` root): is it doing the job of orienting the wife / a clinician / a future helper?

### For design-dataviz
- Across all surfaces, what's the chart inventory? Which charts work? Which are decorative?
- Semantic palette discipline: where has medical-red been used aesthetically (chartjunk)?
- The Phase 7.6 NEW routes will need: TwinStatus (13-dim histograms small-multiples), CausalGraph (vis-network DAG, ~571 nodes), SimulationStudio (@xyflow/react scenario builder), BeliefDrift (Plotly posterior timeline). What's the unifying viz language across all four?
- Should we propose a chart library budget cap (e.g., "no more than 3 chart libs in the bundle")?

### For design-motion
- The current motion palette is 2 keyframes (`shimmer`, `pulse-soft`) + SVG chart micro-interactions. Is this restraint correct, or under-supplying?
- Should v8 introduce a formal canon (the 3 timings × 3 easings the design-motion agent has standardized)?
- Page transitions: currently absent. Should v8 add a 100ms fade between routes?
- framer-motion: at what cost/benefit threshold do we say yes? Or is CSS-first the permanent answer?

### For design-webgl-3d
- The brain route currently exists but NiiVue + R3F are NOT yet installed. When should v8 commit to this stack?
- What's the minimum viable MRI viewer surface (volume render + slice navigation + lesion overlay)?
- Should v8 prioritize the MRI viewer or defer to v9? (it's a hero surface but expensive in time)
- FastSurfer-LIT + BIBSnet outputs: how do they enter the viewer? When does the family see segmentations?

### For design-a11y
- WCAG 2.2 AA across the 14 current routes: spot-audit findings — where are we failing?
- What 5 a11y-first principles should v8 bake into every new surface?
- KA `lang` attribute hygiene across the 14 current routes — spot check.
- Cognitive load on family-facing surfaces: is the wife's read of the weekly brief mentally cheap, or expensive?

---

## Dispatch plan (the director's responsibility, not Shako's)

The director sequences specialist invocations as follows. Each Wave is one parallel batch.

**Wave 1 — strategic refresh (4 specialists in parallel)**

These specialists work from existing artifacts; no inter-dependencies.

- design-ux-researcher → personas refresh + ritual audit + new-audience scan
- design-systems-lead → token state audit + register check + dark-mode + shadcn position
- design-content-bilingual → voice drift audit + tone strategy proposal
- design-a11y → spot-audit of 5 critical routes (today, dashboard, brain, weekly-brief preview, family-inbox)

**Wave 2 — structural + visual proposals (3 specialists in parallel)**

After Wave 1 lands; these specialists need Wave 1 inputs.

- design-product → IA proposal informed by audience refresh + voice strategy + a11y findings
- design-dataviz → cross-surface chart inventory + Phase 7.6 viz language proposal
- design-motion → motion language canon proposal (3 timings × 3 easings + restraint policy)

**Wave 3 — specialty positioning (1 specialist + director)**

- design-webgl-3d → MRI viewer strategy + NiiVue/R3F adoption position
- design-director → synthesis: read all 8 deliverables, write sections 9–10, compose final doc

**Estimated total**: 8 specialist invocations + 1 director synthesis. Per-agent budget caps sum to ~$22. Within studio budget.

---

## Success criteria for the final doc

The concept doc is successful when:

1. **Shako can read it in 20 minutes** and feel the team has surfaced decisions he didn't know to make.
2. **Every specialist has contributed** in their lane; no section feels written by committee.
3. **5 specific site-level decisions** are named (section 9), each with a recommendation + 1-line rationale + a single owner.
4. **Technical capability gaps** (section 10) name concrete adoption decisions (shadcn yes/no, framer-motion yes/no, dark mode v8/v9, NiiVue v8/v9, PWA yes/no, real-time yes/no) with cost/benefit.
5. **Audience constraints honored**: no recommendation that breaks privacy, budget, bilingual parity, or "Unknown potential" tone.
6. **The doc is itself a quiet artifact** — product-register prose, no marketing language, no impeccable-banned vocabulary, no em-dashes.

---

## Hand-off

After the director composes the doc, hand to Shako with:
- Path: `.planning/design/concept/2026-05-25-fresh-site-concept-v1.md`
- Summary (3 sentences): what shipped, what decisions Shako must make, what the next planning round would unlock.
- Ask: "Do you want a v2 with 1-3 specific decisions argued in more depth, or are we ready to spec the top-priority surfaces?"

---

## Notes for the director

- Do NOT auto-write the doc. Wait for specialist deliverables; synthesize after Wave 3.
- Run the gate (systems-lead + a11y + content-bilingual) as a final pass on the synthesized doc itself.
- If a specialist hits an open question they cannot answer without Shako input, surface it to me (Shako) immediately — don't let the team invent answers.
- Budget aggregation: report total spend at hand-off.
- Do not produce parallel Mkhedruli of the full doc; KA section headings are sufficient. Final KA polish is a v7-i18n job for a separate round.
