# ALEKSANDRA_BRAIN: Core Design System & AI Guidelines

## 1. Aesthetic Philosophy (Linear + Notion + Mayo Clinic)
- **Primary Vibe:** Clinical, absolute clarity, ultra-minimal, high data density.
- **Never Sci-Fi:** NO purple/pink gradients, NO neon glows, NO dark mode as default, NO bouncy animations.
- **UI Language:** Drop standard "SaaS" aesthetics. Think of this as a critical dashboard in a modern hospital.

## 2. Anti-Patterns (pbakaus/impeccable rules)
- **BANNED:** `bg-gradient-to-r`, `shadow-[...glow...]`, excessive rounded corners (`rounded-2xl`, `rounded-full` on cards).
- **BANNED:** standard AI fonts (Roboto, Arial). Use **Inter** exclusively for UI.
- **BANNED:** Lorem Ipsum. Always use real clinical/medical data placeholders.
- **BANNED:** "Bouncy" transitions. Use strict, linear, fast easing (`ease-out duration-150`).

## 3. Web Interface Guidelines (vercel-labs/agent-skills)
- **Accessibility First:** Minimum contrast ratios must be met. Status colors must always be accompanied by icons or text (color alone is not enough).
- **Structure:** Use semantic HTML tags (`<nav>`, `<main>`, `<aside>`, `<section>`).
- **Spacing System:** Strict 8px grid (Tailwind `p-2`, `p-4`, `p-8`, `gap-4`, `gap-6`). No arbitrary pixel values (`p-[17px]`).

## 4. Specific Component Execution (VoltAgent/awesome-design-md / Linear style)

### Cards & Panels
- Background: `bg-white` or `bg-slate-50`.
- Border: `border border-slate-200`. NO thick borders.
- Shadow: Extremely subtle or none. Use `shadow-sm` maximally.
- Radius: `rounded-md` or `rounded-lg`. Never excessive.

### Typography (Hierarchy is everything)
- Page Titles: `text-2xl font-semibold tracking-tight text-slate-900`.
- Section Headers: `text-sm font-medium uppercase tracking-wider text-slate-500`.
- Body Text: `text-sm text-slate-700 leading-relaxed`.

### Colors (Semantic Medical Palette)
- Only use these for actionable or status items:
  - `medical-red`: `text-red-600 bg-red-50 border-red-200` (Urgent / Damaged)
  - `medical-green`: `text-emerald-600 bg-emerald-50 border-emerald-200` (Preserved / Success)
  - `medical-orange`: `text-amber-600 bg-amber-50 border-amber-200` (Partial / Therapy)
  - `medical-purple`: `text-violet-600 bg-violet-50 border-violet-200` (Imaging / Today)

## 5. Layout Constraints
- **Main Layout:** Rigid 65% / 35% split.
- **Whitespace:** Generous padding. If a screen looks crowded, remove elements or use collapsible sections, do not shrink font sizes.
- **Borders over Backgrounds:** Prefer separating sections with subtle `border-b border-slate-200` rather than using different background colors, to keep the "document" feel (Notion style).

## 6. AI Agent Execution Directive
- Read this file before generating ANY React component.
- If asked to create a "Dashboard", do not generate standard metric cards with random charts. Generate a clinical "Today" view as specified in the project architecture.
- DO NOT USE `lucide-react` icons redundantly; use them only where they genuinely aid navigation or denote status.
