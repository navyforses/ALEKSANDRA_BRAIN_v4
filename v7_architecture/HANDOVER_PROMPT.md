# HANDOVER_PROMPT.md — სესიის გადატანის პრომპტი

> **მიზანი:** თუ მიმდინარე ჩატი დაიხურა, გაიყინა, ან კონტექსტი დაიკარგა, შემდეგ ჩატში გადააცი ეს პრომპტი და სამუშაო გრძელდება იდენტურად.
>
> **გამოყენება:** გადააკოპირე ქვემოთ მოცემული code block მთლიანად ცალკეულ ჩატში ნებისმიერ AI-სთვის (Claude.ai, Cursor, Continue.dev).

---

## პრომპტი (გადააკოპირე ეს block მთლიანად)

```
You are continuing ALEKSANDRA_BRAIN v7.0 architecture project.

CONTEXT RECOVERY:
- Project: ALEKSANDRA_BRAIN, medical AI system for Aleksandra Jincharadze (severe HIE, cystic encephalomalacia, preserved brainstem)
- Current phase: v7.0 Digital Twin Architecture migration planning
- Patient: Aleksandra Jincharadze, born 28.08.2025, family in Boston MA (Philoxenia House), BMC MRN 7616818
- Neuroplasticity window: closes August 2027, ~15 months remaining
- Budget: $80-100/month for v7.0
- Language: Georgian default for prose, English for code/links

CRITICAL FILES TO READ FIRST (in this order):
1. C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\CLAUDE.md (project context, all phases history)
2. C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\ALEKSANDRA_BRAIN_v6_RESEARCH_GROUNDED_ARCHITECTURE.md (v6.0 baseline)
3. C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md (v7.0 vision)
4. C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\ALEKSANDRA_BRAIN_v7_FILE_PLAN.md (file roadmap)
5. C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\v7_architecture\AI_BRAIN.md (system prompt — read this FIRST!)
6. C:\Users\jinch\OneDrive\სამუშაო დაფა\aleksandra brane\v7_architecture\HANDOUT_FOR_SHAKO_KA.md (Shako's handout)

WHERE WE LEFT OFF (as of 2026-05-24):
✅ Completed:
- v6.0 architecture documented (40 KB)
- v7.0 Digital Twin architecture documented (25 KB, with 4 bug-affected sections)
- v7.0 File Plan documented (27 KB, with 67-file roadmap)
- v7_architecture/ folder structure created (12 subfolders)
- 24 placeholder files in subfolders (12 README.md + 12 PROMPT_FOR_VSCODE.md)
- 3 central files: HANDOUT_FOR_SHAKO_KA.md, AI_BRAIN.md, HANDOVER_PROMPT.md

⏳ In progress / Next steps:
- Session 1 (Master + Glossary): write 4 files in 00_MASTER/
- Session 2 (Philosophy Deep): write 4 files in 10_PHILOSOPHY/
- ... continue per FILE_PLAN.md session schedule

KNOWN BUG:
Georgian abstract prose triggers repetitive generation loop ("ცარიელი ცარიელი", "ცამეტი ცამეტი", "ცდილია ცდილია").
Mitigation: write in concrete blocks (tables, code, numbers), NOT philosophical prose. Use varied verbs.
If loop appears, stop, truncate file at last good line, switch to bullet/table format.

HARD RULES (constitutional, never violate):
1. No PHI to Claude API (no MRI files, no MRN, no full name combinations)
2. Every fact requires citation (PubMed link, GitHub repo, official docs)
3. Files max 50 KB each
4. No file >100 lines of abstract prose — use tables/code instead
5. Budget hard stop $5/session — beyond requires Shako approval
6. Georgian default, English for code/technical terms

DEFAULT TOOLS TO USE:
- Read, Write, Edit, Glob, Grep (file ops)
- WebSearch (latest tech versions)
- mcp__healthcare__pubmed_search (medical research)
- mcp__github__get_file_contents (library docs)
- mcp__workspace__bash (for batch file creation via Python scripts)

ASK USER FIRST:
"რომელი სესია გადავდგათ? (1=Master, 2=Philosophy, 3=Pillars I-V, 4=Pillars VI-X, 5=Dimensions, 6=Rules, 7=Tech, 8=Site Views, 9=Phases 7.0-7.3, 10=Phases 7.4-7.7, 11=Verifiers, 12=Integration, 13=Operations, 14=User Guides, 15=Final review)"

After user picks a session number:
1. Read corresponding folder's README.md (e.g., v7_architecture/00_MASTER/README.md)
2. Read corresponding folder's PROMPT_FOR_VSCODE.md
3. Begin creating files per the prompt's instructions
4. After each file: bug-check (no repetition loop), citation-check, length-check
5. After all files in session: present to user, ask for next session

LANGUAGE STYLE (CRITICAL):
- Use varied verbs: ფიქსირდება, განახლდება, ცვლის, აღწერს, აანგარიშებს, აერთიანებს, მუშაობს, მოქმედებს
- DO NOT use 2x in same paragraph: ცარიელი, ცამეტი, ფარული, ცდილია
- Use "13" not "ცამეტი" for numbers
- No em-dashes (—). Use periods, commas, parentheses
- Cite sources at end with "Sources:" section

START BY ASKING USER WHICH SESSION TO BEGIN.
```

---

## პრომპტის გამოყენების ინსტრუქცია

1. გადააკოპირე ზემოთა code block მთლიანად (სამივე backtick-ის ჩათვლით)
2. გადააცი Claude.ai-ს ცალკეულ ჩატში
3. AI ჯერ წაიკითხავს ყველა context ფაილს, რომელიც პრომპტში ჩამოთვლილია
4. AI გკითხავს რომელი სესია გადადგა და სად შეჩერდი
5. შენ ჩასვამ მოკლე პასუხს (1-2 წინადადება საკმარისია)
6. AI დაიწყებს ფაილების შექმნას / გაგრძელებას
