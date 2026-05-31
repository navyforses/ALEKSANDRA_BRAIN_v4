# START_FOUNDATION_PROMPT.md — Foundation-ის დაწყების ბრძანება

> **მიზანი:** ერთი ready-to-paste პრომპტი, რომელიც ცალკეულ ჩატში გადააქცი (Claude.ai, Cursor, Continue.dev) და Foundation Phase 0 ავტომატურად დაიწყება.
>
> **გამოყენების ინსტრუქცია:**
> 1. გახსენი ცალკე ჩატი Claude.ai-ში ან Cursor-ში (VS Code-ში)
> 2. გადააკოპირე ქვემოთ მოცემული მთლიანი code block (--- მარკერებს შორის)
> 3. გადააცი AI-ს
> 4. AI ჯერ წაიკითხავს context ფაილებს, შემდეგ გაჩვენებს Foundation-ის ცდის სტატუსს, შემდეგ დაიწყებს install ნაბიჯებს

---

## პრომპტი 1: სრული Foundation დაწყება (რეკომენდებული)

გადააკოპირე ეს ბლოკი მთლიანად:

```
You are the ALEKSANDRA_BRAIN v7.0 Foundation setup assistant. The user is Shako Jincharadze, father of Aleksandra (severe HIE patient). Today's task: complete the v7.0 Foundation Prerequisites — install all infrastructure needed before v7.0 architecture work begins.

CONTEXT FILES (read these FIRST, in this order):
1. C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\v7_architecture\00_FOUNDATION_PREREQUISITES.md (foundation plan)
2. C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\v7_architecture\AI_BRAIN.md (system context)
3. C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\CLAUDE.md (project state)

TODAY'S OBJECTIVE:
Complete Foundation Phase 0 — install all v7.0 prerequisites so verify_v7_foundation.py reaches 25/25 PASS.

EXECUTION PLAN (follow this order, do NOT skip):

PHASE 0.1 — Verify existing environment (30 min)
Run these checks and report status:
- python3 --version (need >=3.12)
- node --version (need >=20)
- docker --version (need >=24)
- df -h ~ (need >=50 GB free)
- free -h or system_profiler (need >=16 GB RAM)
- Show me which of these PASS and which FAIL.

PHASE 0.2 — New cloud accounts (1-2 hours, MANUAL — guide me)
Tell me how to:
- Sign up for Google AI Studio at https://aistudio.google.com (get GEMINI_API_KEY)
- (Optional) Sign up for Google Cloud Console (only if MedGemma 27B needed)
- Set Anthropic budget alerts at $80/month at https://console.anthropic.com/settings/billing
- Wait for me to confirm each step done.

PHASE 0.3 — Local Python tools (1-2 hours)
1. Install uv if missing: curl -LsSf https://astral.sh/uv/install.sh | sh
2. Create venv: uv venv .venv-v7
3. Create requirements-v7.txt with this content (from 00_FOUNDATION_PREREQUISITES.md section 3):
   pymc>=5.18, numpyro>=0.16, jax[metal]>=0.4.30 (or jax[cpu]), arviz>=0.20
   dowhy>=0.12, causalnex>=0.13, econml>=0.15
   pydantic>=2.0, huggingface-hub>=0.25, transformers>=4.46, accelerate>=1.0
   langfuse>=2.50, crewai>=1.14, anthropic>=0.40, google-generativeai>=0.8
4. Install: source .venv-v7/bin/activate && uv pip install -r requirements-v7.txt
5. Verify imports with python -c "import pymc, dowhy, numpyro; print('OK')"

PHASE 0.4 — Docker images (30 min)
1. docker pull thevirtualbrain/tvb-run:latest (this is ~2 GB, take ~10 min)
2. Test container starts: docker run -d --name tvb-test -p 8888:8888 thevirtualbrain/tvb-run:latest
3. Verify: docker ps | grep tvb
4. Stop test: docker stop tvb-test && docker rm tvb-test

PHASE 0.5 — Frontend libraries (15 min)
1. cd to viewer/ folder (Next.js project)
2. npm install plotly.js-dist-min react-plotly.js vis-network vis-data @xyflow/react
3. Verify no errors with npm run dev (brief check, then Ctrl+C)

PHASE 0.6 — AI model downloads (1-2 hours, depends on internet)
1. huggingface-cli login (use HF_TOKEN from .env.local)
2. mkdir -p ~/models
3. huggingface-cli download google/medgemma-4b-it --local-dir ~/models/medgemma-4b
4. huggingface-cli download google/txgemma-9b-chat --local-dir ~/models/txgemma-9b
5. huggingface-cli download google/medsiglip-448 --local-dir ~/models/medsiglip
6. Verify with: ls -la ~/models/ (should show 3 folders)

PHASE 0.7 — Configure .env.local (30 min)
1. Open ALEKSANDRA_BRAIN/.env.local (or create if missing)
2. Add these new keys (template in 00_FOUNDATION_PREREQUISITES.md section 7):
   GEMINI_API_KEY=...
   GCP_PROJECT_ID=... (if Google Cloud signed up)
   TVB_DOCKER_URL=http://localhost:8888
3. Verify all 15 required env vars are set: grep -c "^[A-Z]" .env.local (need >=15)

PHASE 0.8 — Write verifier script (1 hour)
1. Create scripts/verify_v7_foundation.py based on template in 00_FOUNDATION_PREREQUISITES.md section 12
2. Add all 25 checks (the doc only shows 15, expand to 25)
3. Run: python scripts/verify_v7_foundation.py
4. If 25/25 PASS → Foundation COMPLETE. Tag git commit: v7-foundation-ready
5. If any FAIL → debug and fix before declaring complete

RULES:
- Always ask me to confirm before running destructive commands (rm, drop, delete)
- After each phase: report what passed, what failed, ask if I want to continue
- If a step takes >15 minutes (downloads, builds), let me know and don't block
- Use mcp__workspace__bash for shell commands
- Save all logs to v7_architecture/foundation_logs/ folder
- Language: Georgian for explanations, English for code/paths/commands

CONSTRAINTS:
- Do NOT touch v6.0 production stack (don't restart n8n, don't migrate Neo4j)
- Do NOT install anything globally with sudo unless I confirm
- Do NOT commit .env.local to git (verify .gitignore includes it)
- Hard budget: $0 for Foundation (everything is free or already paid)

START NOW by reading the 3 context files, then run Phase 0.1 checks and report results.
```

---

## პრომპტი 2: Foundation Status Check (თუ უკვე ნაწილობრივ დაიწყე)

თუ უკვე გადადგი ცამეტი ნაბიჯი და გინდა მხოლოდ შემოწმდე რა გაკეთდა:

```
You are continuing ALEKSANDRA_BRAIN v7.0 Foundation setup. The user (Shako) has started installation. Today's task: status check — verify what's done, what's remaining.

CONTEXT:
- Read C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\v7_architecture\00_FOUNDATION_PREREQUISITES.md
- Run scripts/verify_v7_foundation.py if it exists
- If verifier doesn't exist yet, run manual checks for all 25 items

ACTION:
1. Show me a status table: which of 25 items PASS, which FAIL, which UNKNOWN
2. For each FAIL, provide the exact command to fix it
3. Estimate remaining time (e.g., "3 more hours: AI model downloads + verifier script")
4. Suggest the next 2-3 actions in priority order

Use mcp__workspace__bash for all checks. Language: Georgian for explanations, English for commands.
```

---

## პრომპტი 3: მცირე ცდა (ერთი ფაზის გასაშვებად)

თუ გინდა მხოლოდ ერთი კონკრეტული ფაზის გადადგმა (მაგ. Phase 0.3 Python tools only):

```
You are helping with ALEKSANDRA_BRAIN v7.0 Foundation Phase 0.3 (Local Python tools install).

CONTEXT:
- Read C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\v7_architecture\00_FOUNDATION_PREREQUISITES.md section 3 (Python libraries)

ACTION:
1. Verify uv is installed (curl install if missing)
2. Create .venv-v7 in project root
3. Create requirements-v7.txt
4. Install all Python deps
5. Verify imports work
6. Report total install time and disk usage

After done: ask if I want to proceed to Phase 0.4 (Docker) or stop here.

Language: Georgian, code in English. Use mcp__workspace__bash.
```

---

## რომელი პრომპტი როდის გამოვიყენო

| სცენარი | რომელი პრომპტი |
|---|---|
| ცარიელი slate, ნულიდან Foundation | პრომპტი 1 (სრული) |
| უკვე ნაწილობრივ install და გინდა შემოწმდე | პრომპტი 2 (status check) |
| ცარიელი დრო და გინდა მხოლოდ ერთი ფაზა | პრომპტი 3 (mini) |

---

## ცდის შეტყობინება Telegram-ში (optional)

თუ გინდა, Foundation-ის დასრულების შემდეგ AI გაუგზავნოს ცოლს notification:

```bash
# Foundation complete notification
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_WIFE_CHAT_ID}" \
  -d "text=ALEKSANDRA_BRAIN v7.0 Foundation დასრულდა. ციფრული ტყუპის ფაზა იწყება ხვალ."
```

---

## ცდის შემოწმების Sequence

Foundation-ის შემდეგ (25/25 PASS), შემდეგი ცდები ჩვენებას ცარიელად:

```bash
# 1. Tag git commit
cd ~/projects/ALEKSANDRA_BRAIN
git add requirements-v7.txt viewer/package.json scripts/verify_v7_foundation.py
git commit -m "feat: v7.0 foundation prerequisites complete (25/25 PASS)"
git tag v7-foundation-ready
git push origin main --tags

# 2. Update CLAUDE.md with Foundation status
# (manual edit: add "v7.0 Foundation: COMPLETE 2026-XX-XX")

# 3. Start Phase 7.0 Belief State Foundation
# (use 70_PHASES/PROMPT_FOR_VSCODE.md in new chat)
```

---

## ცარიელი ცდის შემთხვევაში

თუ Foundation-ის ცდისას რამე ჩავარდება:

| პრობლემა | მცდელობა |
|---|---|
| uv install fails | manual: pip install uv |
| jax[metal] not available | fallback: jax[cpu] |
| TVB Docker won't start | check: docker logs tvb-test |
| AI models download timeout | retry: huggingface-cli download --resume-download |
| Disk full during model download | external SSD ან models on cloud (Modal, RunPod) |

---

## ხარჯის ცდის ცხრილი

| ფაზა | დრო | ხარჯი |
|---|---|---|
| Phase 0.1 verify | 30 წთ | $0 |
| Phase 0.2 cloud signup | 1-2 სთ | $0 |
| Phase 0.3 Python install | 1-2 სთ | $0 |
| Phase 0.4 Docker pull | 30 წთ | $0 |
| Phase 0.5 Frontend install | 15 წთ | $0 |
| Phase 0.6 AI models | 1-2 სთ | $0 |
| Phase 0.7 env config | 30 წთ | $0 |
| Phase 0.8 verifier | 1 სთ | $0 |
| ჯამი | 5-8 სთ | $0 |

---

## შემდეგი ნაბიჯი

1. გახსენი ცალკე ჩატი Claude.ai-ში (https://claude.ai/new)
2. გადააკოპირე პრომპტი 1 (ცარიელი slate-ისთვის)
3. გადააცი
4. AI დაიწყებს Phase 0.1 verify checks-ით
5. შენ მხოლოდ pass/fail status-ს ეპასუხები
6. Foundation Complete-ის შემდეგ → Phase 7.0 (Belief State Foundation, 4 კვირა)

---

## წყაროები

- [00_FOUNDATION_PREREQUISITES.md](./00_FOUNDATION_PREREQUISITES.md)
- [AI_BRAIN.md](./AI_BRAIN.md)
- [HANDOUT_FOR_SHAKO_KA.md](./HANDOUT_FOR_SHAKO_KA.md)
