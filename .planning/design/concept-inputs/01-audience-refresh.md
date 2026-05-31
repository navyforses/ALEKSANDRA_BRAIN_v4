# Concept Input 01 — Audience Refresh

**Author**: design-ux-researcher
**Date**: 2026-05-25
**Wave**: 1 of 3 — strategic refresh
**Status**: handed to design-director for synthesis

---

## 1.1 Personas at month 9 — what's still true, what's drifted

**Shako (developer-operator, KA)** — Still load-bearing, but the persona file undersells the operating context. Nine months in, Shako is no longer "primary user." He is a **single-operator SRE for a 5-agent system that runs without him for 6-hour cron windows.** The cockpit is not where he does the work; it is where he checks whether the system did the work. The persona must shift from "developer who reads dense info" to "operator who triages overnight output in <90 seconds, then drops back into IDE." Implication: `/today` and `/dashboard` are triage surfaces, not exploration surfaces. The 14-route IA was designed for an explorer; Shako is no longer one.

**Wife (warm morning ritual, KA)** — Persona is correct in voice, wrong in surface. The brief states she "reads the weekly brief every Sunday morning" — but the weekly brief is delivered via **Telegram + Gmail digest** (Phase 5/6 evidence: `gmail_digest reads .en`, `telegram_sender reads .ka`). There is no `/weekly-brief` route in the 14 surfaces I enumerated. The wife is not a *site* user; she is a *channel* user. Treating her as a site persona has likely caused us to over-invest in `/today` ornamentation she will never see. **Assumption — flag for Shako**: I have no data showing she has ever opened the viewer URL. The brief itself says "Wave 1 → spot-audit of 5 critical routes (today, dashboard, brain, weekly-brief preview, family-inbox)" but neither `weekly-brief` nor `family-inbox` exists as a route. They exist as **payloads**, not pages.

**Clinician (EN, 2-minute scan)** — Persona is correct but currently un-served by the site. Their artifact is the Family Handover PDF (ReportLab, Phase 3). They have never been a viewer audience. The site has 0 clinician-tuned surfaces. This is an honest gap, not a drift.

**New audience that has emerged: Future-Shako (T+6 months).** The brief names this in passing ("a fourth implicit audience") but it deserves first-class status. The 13 inviolable constitutional rules (Phase 7.5), the 89/89 verifier coverage, the foundation_logs directory — these are not for present-Shako, who wrote them. They are for **a Shako who has forgotten why a rule exists and needs the cockpit to re-teach him.** This persona reads in EN (developer register) but needs *narrative* re-grounding the way the wife does. The cockpit currently fails this audience: there is no "why does this rule exist" surface, only the rule itself.

**Audiences I considered and rejected:**
- *Grandparents / extended family.* No evidence of pull. Telegram digest is sufficient and they don't ask for more.
- *Future therapist (Duke EAP, BMC).* Real future audience but not for v8 — they consume Handover PDF, not the site. Defer to v9.
- *Public / press / fundraiser audience.* Out of scope per privacy posture. Do not let v8 drift here.

---

## 1.2 The Sunday ritual — designed vs. observed

**Designed** (per CLAUDE.md, Phase 4): "first real Weekly Brief Sunday 2026-05-24 09:00 ET — v1 release gate." Compose runs Saturday night, delivers Sunday 09:00 ET via Telegram (KA) + Gmail (EN). The wife reads on her phone in bed; Shako reads on his laptop with coffee. The `/today` surface is meant to be a Monday-morning landing for Shako to dispatch the week's queue.

**Observed (assumption — flag for Shako)**: The first real Sunday brief was yesterday, 2026-05-24. There is no observed ritual yet. What I *can* read from the code:
- `viewer/app/[locale]/today/page.tsx:21` — title `t("title")` followed by `t("comingSoon")` followed by `t("fallback")`. **Three strings of placeholder copy on the entry surface for the daily ritual.** This is a tell: the ritual page was scaffolded but never finished.
- `ActiveQuestionsSection` (Phase 7.4 active learning) is the only live widget on `/today`. The page is otherwise empty.
- `/dashboard` (the surface that *does* work) is operator-facing — runs ledger, hypothesis counts, daily spend — none of which is brief-ritual content.

**Honest read**: the Sunday ritual exists as a *push notification* and an *email*, not as a *site visit*. The "weekly brief preview" route the brief refers to does not exist. If the wife is observed reading it Sunday morning, she is reading Telegram or Gmail — not the cockpit. Shako likely reads the email on phone, opens cockpit only if something flagged.

**What I'd test to confirm**: ask Shako directly — "Did the wife open the viewer URL between 2026-05-24 09:00 and 12:00 ET?" Server logs (Vercel analytics if enabled) will answer in 30 seconds. Until answered, treat the Sunday-ritual-as-site-visit hypothesis as unvalidated.

---

## 1.3 Three painful moments in Shako's daily cockpit

Reading the routes as Shako-the-operator would, the three highest-friction moments:

1. **The `/today` placeholder problem.** `viewer/app/[locale]/today/page.tsx:21-28` ships `t("comingSoon")` + `t("fallback")` as the body of the daily landing page. The one live widget is `ActiveQuestionsSection` (line 24), which is Phase 7.4 content (EIG questions). The page promises "today" and delivers "an active-questions widget plus two placeholder strings." For a daily ritual this is a broken contract. Severity: BLOCK (Nielsen #1, Visibility of system status — the page does not tell the operator what happened overnight).

2. **The dashboard nav doesn't include the routes Shako uses.** `viewer/app/[locale]/dashboard/page.tsx:142-153` — the in-page nav lists only `dashboard, hypotheses, papers, therapies, timeline`. Five of fourteen. Missing: `today, audit, twin, drift, causal, simulate, brain, knowledge, hypotheses/[id]`. Shako has to use the brain panel (35% horizontal real-estate per the brief) or URL-type. This is exactly the "future-Shako forgets the IA" failure mode. Severity: FLAG (Nielsen #6, Recognition over recall — Shako can no longer recognize his own product's IA from its own dashboard).

3. **No surface answers "what changed since I last looked."** No `/today` recent-activity feed (only `/dashboard` `latestEvents` for `runs`, not for hypotheses or papers). No "since-cursor" anywhere. Shako-the-operator wants a one-screen diff: "since Sunday 09:00, here is what is new, what was dispatched, what failed, what needs a decision." This surface does not exist. Severity: BLOCK (Cognitive Load Theory — operator must visit 6 routes to assemble the diff manually).

---

## 1.4 The wife and the weekly brief — Telegram-only or full-read?

**Inference**: Telegram-only with occasional Gmail. Evidence chain:
- Phase 6 (i18n): `telegram_sender reads .ka` (CLAUDE.md). The KA channel is Telegram. The wife reads KA. Therefore the wife reads Telegram.
- `gmail_digest reads .en`. Gmail is EN. The wife reads KA. Therefore Gmail is not her primary channel.
- The wife is not the operator. The viewer URL is a desktop / laptop surface; Telegram is a phone surface; the wife's morning ritual is on her phone.
- There is no `/weekly-brief` route in the 14 surfaces. The "weekly brief" lives in `compose_bilingual` output that ships to Telegram + Gmail. It is not a destination URL.

**What I'd test to confirm**: (a) ask Shako directly; (b) check Vercel/Telegram-bot logs for Sunday-morning traffic from a non-Shako device; (c) ask the wife herself in a 2-question survey — "Do you tap the link in the Telegram message? Do you ever open the site URL?" One conversation, 5 minutes.

**Design implication if confirmed**: v8 should treat the wife's surface as **the Telegram message body itself**, not as a route. The "weekly brief preview" specialists in Wave 1 are auditing should be the *message preview* (what the wife sees in her Telegram lock-screen notification + first 200 chars of the message), not a `/weekly-brief` page. If we want her to land on a site surface, we need a deep-link from the Telegram message into a *phone-first, no-jargon, single-scroll* route that does not exist today.

---

## 1.5 Recommended audience model for v8

**Consolidate to two site personas + two channel personas.**

| Persona | Surface | Why |
|---|---|---|
| Shako-operator (site) | All 14+ routes, keyboard-first, dense | Real daily user |
| Future-Shako (site) | Re-grounding surfaces: `/audit`, constitution viewer, "why does this rule exist" | The forgetting curve is real at month 9+ |
| Wife (channel) | Telegram message body, Gmail digest, optional phone-first deep-link target | She is not a site user |
| Clinician (channel) | Family Handover PDF, doctor session prep doc, optional citation-only landing | Not a site user, but a future deep-link target |

**This is a re-frame, not an addition.** The current model treats all four as site personas and under-serves all four. The recommendation: build for the two who actually visit URLs (Shako-now, Shako-later), and treat the wife + clinician as channel-first audiences whose deep-link landing pages are designed *as message destinations*, not as standalone routes in the nav.

**One immediate consequence**: the `/today` placeholder is not a "needs finishing" page — it's a category error. It was designed as if Shako-operator and wife-warm-morning shared a surface. They don't. `/today` should be Shako-operator-only and dense; the wife's "today" is the Telegram message that arrived at 09:00.

**Open question kicked to design-director**: does the recommendation to demote wife + clinician from site-personas to channel-personas conflict with anything in section 9 (5 site-level decisions)? If yes, surface to Shako before synthesis.
