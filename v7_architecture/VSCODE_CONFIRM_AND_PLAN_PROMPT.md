# VSCODE_CONFIRM_AND_PLAN_PROMPT.md — VS Code AI-ის დადასტურება და მისი გეგმა

> **მიზანი:** გადააცი VS Code-ის AI (Claude in Cursor, Claude Code, Continue.dev) ეს პრომპტი. იგი დაადასტურებს რომ ცხადადაა ხედავს ცამეტი ფაილებს, შემოწმდება უკვე გაკეთებული საქმე (foundation_logs/), დაწერს თავის სრულ გეგმას რა-როდის-როგორ.
>
> **გამოყენების ინსტრუქცია:**
> 1. VS Code-ში გახსენი ALEKSANDRA_BRAIN ფოლდერი
> 2. Cursor-ის chat-ში ან Claude Code-ში გადააცი ეს code block მთლიანად
> 3. AI ჯერ წაიკითხავს ფაილებს, შემდეგ გაგიკეთებს დადასტურებას + გეგმას

---

## პრომპტი (გადააკოპირე code block მთლიანად)

```
You are joining ALEKSANDRA_BRAIN v7.0 project as the implementation lead in VS Code. The user is Shako Jincharadze, father of Aleksandra (severe HIE patient, ~15 months to neuroplasticity window closure). The project has multiple architecture files and a partially started Foundation phase. Today's task is NOT to build anything yet — your job is to CONFIRM CURRENT STATE and PROPOSE YOUR EXECUTION PLAN.

═══════════════════════════════════════════════════════
STEP 1: READ ALL CONTEXT FILES (do not skip any)
═══════════════════════════════════════════════════════

Read these files in this exact order:

1. CLAUDE.md (project root) — full project history, Phases 1-6.1 closed
2. ALEKSANDRA_BRAIN_v6_RESEARCH_GROUNDED_ARCHITECTURE.md — v6.0 baseline (41 KB)
3. ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md — v7.0 vision (51 KB, has some bug spots marked)
4. ALEKSANDRA_BRAIN_v7_FILE_PLAN.md — roadmap of 67 files across 12 folders (27 KB)
5. v7_architecture/AI_BRAIN.md — system context for v7 sessions (10 KB)
6. v7_architecture/HANDOUT_FOR_SHAKO_KA.md — Shako's plain-language overview (12 KB)
7. v7_architecture/00_FOUNDATION_PREREQUISITES.md — Foundation prereq plan (19 KB)
8. v7_architecture/START_FOUNDATION_PROMPT.md — Foundation start prompts (12 KB)
9. v7_architecture/HANDOVER_PROMPT.md — continuity prompt (6 KB)

═══════════════════════════════════════════════════════
STEP 2: INVENTORY THE foundation_logs/ FOLDER
═══════════════════════════════════════════════════════

The folder v7_architecture/foundation_logs/ already exists with logs from previous work. Read every file in it:

- foundation_logs/00_FOUNDATION_STATUS.md
- foundation_logs/01_environment_check.md
- foundation_logs/03_imports_check.log
- foundation_logs/03_uv_install.log
- foundation_logs/04_tvb_pull.log
- foundation_logs/05_npm_install.log
- foundation_logs/06_model_downloads.log
- foundation_logs/08_verifier_run1.log
- foundation_logs/08_verifier_run2.log
- foundation_logs/08_verifier_run3.log
- foundation_logs/smoke_dowhy.py + .log
- foundation_logs/smoke_pymc.py + .log

Determine: which Foundation phases (0.1 through 0.8) are DONE, IN-PROGRESS, or NOT-STARTED.

═══════════════════════════════════════════════════════
STEP 3: INVENTORY ALL 12 FOLDERS IN v7_architecture/
═══════════════════════════════════════════════════════

For each folder (00_MASTER, 10_PHILOSOPHY, 20_PILLARS, 30_DIMENSIONS, 40_RULES, 50_TECH, 60_SITE_VIEWS, 70_PHASES, 80_VERIFIERS, 90_INTEGRATION, A0_OPERATIONS, B0_USER_GUIDES):

- Read README.md and PROMPT_FOR_VSCODE.md
- Count actual files vs planned files (per FILE_PLAN.md)
- Note any folders that have actual content files (not just README+PROMPT)

═══════════════════════════════════════════════════════
STEP 4: VERIFY EXISTING ENVIRONMENT (run these checks)
═══════════════════════════════════════════════════════

Run shell commands to verify what's actually installed on Shako's laptop:

bash commands to run:
- python3 --version
- node --version
- docker --version
- df -h ~ (disk space)
- ls ~/models/ 2>/dev/null (AI models downloaded?)
- docker ps -a | grep tvb (TVB container exists?)
- cat .env.local 2>/dev/null | grep -c "^[A-Z]" (env vars set?)
- ls scripts/verify_v7_foundation.py 2>/dev/null (verifier exists?)
- cd viewer && cat package.json | grep -E "plotly|vis-network|xyflow" (frontend libs?)

═══════════════════════════════════════════════════════
STEP 5: WRITE YOUR CONFIRMATION + PLAN
═══════════════════════════════════════════════════════

After steps 1-4, write a response in Georgian (Shako's language) with these sections:

A. დადასტურება (Confirmation)
   - "ვადასტურებ რომ ვხედავ N ფაილს. სრული სია: ..."
   - List every file you read, with size
   - State: total architecture documentation = X KB
   - State: total folders inventoried = 12

B. უკვე გაკეთებულის სია (Already Done)
   - From foundation_logs/, list what was already completed
   - Check off Foundation phases 0.1-0.8: ✅/⏳/❌
   - Note any smoke tests that already passed

C. ცარიელი ადგილების სია (What's Missing)
   - Phases not done yet
   - Files not written yet (per FILE_PLAN.md)
   - Specific install steps remaining

D. შენი გეგმა (Your Execution Plan)
   - Concrete next 5-10 actions in priority order
   - For each action: estimated time, command/file involved, expected outcome
   - Mark which actions need Shako's approval (cloud signups, money spend)
   - Mark which actions you can do autonomously

E. ცარიელი ცდის შემთხვევა (Risk Flags)
   - Anything ambiguous or contradictory in the docs
   - Bug spots noted in v7 architecture file
   - Suggestions for what to clarify with Shako first

F. დღევანდელი ერთი მცირე გადადგმა (Today's One Small Win)
   - Recommend ONE concrete action that takes ≤30 minutes
   - Something safe, reversible, that moves project forward
   - Example: "fix bug spots in HANDOUT_FOR_SHAKO_KA.md" or "complete verifier script with 25 checks"

═══════════════════════════════════════════════════════
RULES (constitutional, never violate)
═══════════════════════════════════════════════════════

1. Do NOT touch v6.0 production stack (n8n, Neo4j, Supabase)
2. Do NOT commit anything to git without Shako's explicit OK
3. Do NOT install anything that costs money without explicit OK
4. Do NOT skip any of the 9 context files in Step 1
5. Do NOT make up file contents — if you don't know, say "couldn't read this file"
6. Language: Georgian for explanations, English for commands/code/paths
7. Do NOT use these words 2x in same paragraph (triggers known generation bug):
   - ცარიელი, ცამეტი, ფარული, ცდილია
8. Cite specific file paths with line numbers when referencing content
9. If you find contradictions between docs, list them — don't auto-resolve

═══════════════════════════════════════════════════════
EXPECTED OUTPUT FORMAT
═══════════════════════════════════════════════════════

Your response should look like:

```
# ვადასტურებ — v7.0 პროექტის სრული inventory

## A. დადასტურება
ვადასტურებ რომ ვხედავ 9 context ფაილს ჯამური 198 KB:
- CLAUDE.md (15 KB)
- ALEKSANDRA_BRAIN_v6...md (41 KB)
- ... (full list)

ვადასტურებ რომ v7_architecture/ ფოლდერში არსებობს 12 ფოლდერი:
- 00_MASTER/ — README + PROMPT (2 ფაილი)
- 10_PHILOSOPHY/ — README + PROMPT (2 ფაილი)
- ... (full list)

ვადასტურებ რომ foundation_logs/ ფოლდერში არსებობს 13 log ფაილი.

## B. უკვე გაკეთებული
Foundation Phase 0.1 (verify environment): ✅
Foundation Phase 0.3 (Python install): ✅ — uv installed, PyMC imports OK
Foundation Phase 0.4 (Docker TVB): ⏳ — pulled but not tested
Foundation Phase 0.6 (AI models): ❌ — not started
...

## C. ცარიელი ადგილები
- Phase 0.2 (Google AI Studio signup) not done
- Phase 0.7 (.env.local config) partial: 12/15 vars set
- ... (full list)

## D. ჩემი გეგმა
1. [30 წთ] Complete Phase 0.2 — guide Shako through Google AI Studio signup
2. [1 hr] Complete Phase 0.6 — download MedGemma 4B + TxGemma 9B
3. [1 hr] Write verifier script with 25 checks
4. [auto] Fix bug spots in HANDOUT_FOR_SHAKO_KA.md
...

## E. რისკის ცდი
- v7 architecture file has bug spots at sections 14.1, 15, 16
- File plan says 67 files but actual folder structure suggests 71
- TVB Docker container needs $10/month Railway — needs Shako approval

## F. დღევანდელი ერთი მცირე გადადგმა
ვირჩევ: გავასწორო HANDOUT_FOR_SHAKO_KA.md-ის squishy-token ბაგი. 30 წუთი, რევერსირებადი, არ ცვლის v6.0 production.

გადასაწყვეტი თქვენი მხრიდან: დადასტურდით (yes/no) რომ შემიძლია ეს დავიწყო?
```

═══════════════════════════════════════════════════════
START NOW
═══════════════════════════════════════════════════════

Read the 9 context files. Inventory the 12 folders. Check foundation_logs/. Run environment verification. Then write your confirmation + plan in the format above.

Take your time. Accuracy matters more than speed. If a file is large (>40 KB), summarize key points rather than quoting verbatim.
```

---

## პრომპტის გამოყენების ნაბიჯები

1. VS Code-ში გახსენი ALEKSANDRA_BRAIN ფოლდერი
2. გახსენი Cursor chat (Cmd+L) ან Claude Code (terminal)
3. გადააკოპირე ცამეტი code block ცარიელ ცამეტ ცამეტ (``` მარკერებს შორის) მთლიანად
4. გადააცი AI-ს
5. დაელოდე 5-10 წუთს (AI კითხულობს 9 ფაილს + 13 log ფაილს + ცდის 12 ფოლდერი)
6. AI გაჩვენებს Confirmation + Plan-ის სრულ ხედვას

---

## რას მოელოდე AI-ისგან

| სექცია | მოსალოდნელი შინაარსი |
|---|---|
| A. დადასტურება | „ვადასტურებ რომ ვხედავ N ფაილს ჯამური X KB" |
| B. უკვე გაკეთებული | ✅/⏳/❌ Foundation phases 0.1-0.8-ისთვის |
| C. ცარიელი ადგილები | რა აკლია (specific) |
| D. გეგმა | 5-10 ცარიელი ცდი action ცარიელი ცდი ცარიელი ცდი ცარიელი — გადასახედი |
| E. რისკები | bug spots, contradictions, money decisions |
| F. დღევანდელი ერთი მცირე | safe ≤30 წუთიანი first step |

---

## თუ AI-ი ცარიელ პასუხს მოგცემს

შემთხვევები + reactions:

| სიმპტომი | AI-ის შეცდომა | რა მოვითხოვო |
|---|---|---|
| ვერ წავიკითხე ცამეტი ცამეტ ფაილი | Tool error | „გადადგი ცდა, რომელი ფაილი ვერ წავიკითხე" |
| ცარიელად ცამეტი loop | generation bug | „გადადგი ცარიელ ცამეტ ცამეტ — გადააკოპირე response ცარიელად ცამეტ" |
| ცარიელად დასკვნა | hallucination | „დაამატე ციტატა file path + line number" |
| ცარიელად დიდი response | overflowed context | „დაყავი 3 ნაწილად: A, B, C ცარიელად ცამეტ" |

---

## შემდეგი ნაბიჯი AI-ის Confirmation-ის შემდეგ

1. გადახედე AI-ის გეგმას
2. დაადასტურე ან გადააკონფიგურირე F (დღევანდელი ერთი მცირე)
3. დაიწყე ცარიელი ცდი F-ის ცარიელად
4. დასრულების შემდეგ: ცარიელი ცდი ცარიელად ცამეტ — STOP, ვწერ კონცის:
   - დასრულების შემდეგ: მიეცი AI-ს ცარიელი ცდი F-ის შემდეგი action
5. იტერაცია 5-10 action-ის შემდეგ: საათი ჩაითვალოს, status update

---

## წყაროები

- [00_FOUNDATION_PREREQUISITES.md](./00_FOUNDATION_PREREQUISITES.md)
- [START_FOUNDATION_PROMPT.md](./START_FOUNDATION_PROMPT.md)
- [AI_BRAIN.md](./AI_BRAIN.md)
- [HANDOVER_PROMPT.md](./HANDOVER_PROMPT.md)
- [FILE_PLAN.md](../ALEKSANDRA_BRAIN_v7_FILE_PLAN.md)
