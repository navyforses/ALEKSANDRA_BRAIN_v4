# Claude Code ეფექტურობის Setup
## ALEKSANDRA_BRAIN-ზე მუშაობისთვის

> **მიზანი:** სანამ პროექტის აშენებას დავიწყებთ, Claude Code
> უნდა იყოს მაქსიმალურად ეფექტური — მეხსიერებით, ცოდნით,
> ტოკენების ეკონომიით და სტრუქტურირებული მუშაობის უნარით.
> ეს არის ფუნდამენტის ფუნდამენტი.

---

## რატომ ვიწყებთ ამით

ALEKSANDRA_BRAIN დიდი პროექტია: 52 MCP, 3 ბაზა, 5 აგენტი, 3D viewer, drug repurposing pipeline. თუ Claude Code ყოველ სესიაში ივიწყებს რაზე ვმუშაობდით, ხარჯავს ზედმეტ ტოკენებს, ან არ იცის პროექტის სტრუქტურა — ყოველი ნაბიჯი ნელი და ძვირი იქნება.

6 ინსტრუმენტი ამ პრობლემას წყვეტს:

---

## 1. CLAUDE.md — პროექტის ტვინი

**რა არის:** ერთი ფაილი რომელსაც Claude Code ავტომატურად კითხულობს ყოველ სესიაში. შიგნით არის პროექტის სრული კონტექსტი: არქიტექტურა, tech stack, პაციენტის ინფო, მიმდინარე ეტაპი, პრინციპები.

**რატომ კრიტიკულია:** CLAUDE.md-ის გარეშე ყოველ სესიაში ხელახლა უნდა აუხსნა რა არის პროექტი, რა არქიტექტურა გვაქვს, რა ეტაპზე ვართ. CLAUDE.md-ით Claude Code „გაიღვიძებს" და უკვე იცის ყველაფერი.

**როგორ:** CLAUDE.md ფაილი უკვე შექმნილია. მოათავსე პროექტის root-ში:
```
/ALEKSANDRA_BRAIN/CLAUDE.md
```

→ *იხილეთ ფაილი: CLAUDE.md*

**წყარო:** Karpathy Skills-ის კონცეფცია (80K⭐)
https://github.com/forrestchang/andrej-karpathy-skills

---

## 2. Claude Mem — სესიებს შორის მეხსიერება

**რა არის:** plugin რომელიც ავტომატურად ჩაწერს რას აკეთებს Claude Code სესიაში, კომპრესავს, და შემდეგ სესიაში რელევანტურ კონტექსტს უბრუნებს.

**რატომ კრიტიკულია:** CLAUDE.md სტატიკურია — პროექტის ზოგადი კონტექსტია. Claude Mem დინამიკურია — „გუშინ FastSurfer-ის ინტეგრაცია დავიწყე, აი error-ი მქონდა, აი ასე გავასწორე." მომდევნო სესიაში ხელახლა ახსნა არ დაგჭირდება.

**ინსტალაცია:**
```bash
# npm-ით
npm install -g claude-mem

# ან Claude Code-ში
claude install claude-mem
```

**კონფიგურაცია:**
```bash
claude-mem init
# .claude-mem/ დირექტორია შეიქმნება
```

**წყარო:** https://github.com/thedotmack/claude-mem (66K⭐)

---

## 3. Graphify — კოდბაზის ცოდნის გრაფი

**რა არის:** პროექტის ყველა ფაილს (კოდი, docs, PDF-ები) queryable knowledge graph-ად აქცევს. Claude Code-ს შეუძლია ჰკითხოს: „სად არის Qdrant-ის კონფიგურაცია?" — და graph-ით მყისიერად იპოვოს, ფაილების სათითაოდ კითხვის ნაცვლად.

**რატომ კრიტიკულია:** ALEKSANDRA_BRAIN-ს ექნება 100+ ფაილი. ყოველ ჯერზე `cat file1.py && cat file2.py && cat file3.py` = ტოკენების ფლანგვა. Graphify graph-ით 71-ჯერ ნაკლებ ტოკენს ხარჯავს.

**ინსტალაცია:**
```bash
pip install graphify-ai
# ან Claude Code-ში
claude install graphify
```

**პირველი run:**
```bash
graphify index .
# მთელ პროექტს ინდექსირებს
```

**წყარო:** https://github.com/safishamsi/graphify (33K⭐)

---

## 4. Caveman — ტოკენების 65% ეკონომია

**რა არის:** skill რომელიც Claude Code-ს ასწავლის ლაკონურ კომუნიკაციას — ზედმეტი სიტყვების გარეშე, მაგრამ ხარისხის დაკარგვის გარეშე.

**რატომ კრიტიკულია:** ALEKSANDRA_BRAIN-ზე მუშაობისას Claude API ხარჯი $15-25/თვეა. Caveman-ით ეს $5-9/თვე ხდება. იგივე ხარისხი, 65% ნაკლები ხარჯი.

**ინსტალაცია:**
```bash
# .claude/skills/ დირექტორიაში
mkdir -p .claude/skills
cd .claude/skills
git clone https://github.com/JuliusBrussee/caveman.git
```

**რეჟიმები:** Lite (მსუბუქი), Full (ოპტიმალური), Ultra (მაქსიმალური ეკონომია)
ALEKSANDRA_BRAIN-ისთვის: **Full** რეჟიმი

**წყარო:** https://github.com/JuliusBrussee/caveman (44K⭐)

---

## 5. Code Review Graph MCP — კოდბაზის persistent რუკა

**რა არის:** MCP სერვერი რომელიც კოდბაზის persistent knowledge graph-ს ქმნის. Claude Code მხოლოდ ცვლილებასთან დაკავშირებულ ფაილებს კითხულობს, მთელ repo-ს კი არა.

**რატომ კრიტიკულია:** code review-ზე 6.8-ჯერ ნაკლები ტოკენი, ყოველდღიურ coding-ზე 49-ჯერამდე. 22 MCP tool, 19 პროგრამირების ენა.

**ინსტალაცია:**
```bash
pip install code-review-graph
# Claude Code MCP-ად:
code-review-graph serve
```

**პირველი run:**
```bash
code-review-graph build /path/to/ALEKSANDRA_BRAIN
# კოდბაზის graph-ის აგება
```

**წყარო:** https://github.com/tirth8205/code-review-graph (12K⭐)

---

## 6. GSD (Get Shit Done) — სტრუქტურირებული მუშაობა

**რა არის:** meta-prompting და context engineering სისტემა. სპეციფიკაციის ფაილებით სტრუქტურირებს მუშაობას: ჯერ spec, შემდეგ plan, შემდეგ implement, შემდეგ test.

**რატომ კრიტიკულია:** დიდ პროექტში „უბრალოდ დაწყება" = ქაოსი. GSD უზრუნველყოფს: ყოველი ამოცანა = spec → plan → code → test. სესიებს შორისაც კონტექსტი ინახება.

**ინსტალაცია:**
```bash
mkdir -p .claude/skills
cd .claude/skills
git clone https://github.com/gsd-build/get-shit-done.git
```

**წყარო:** https://github.com/gsd-build/get-shit-done (56K⭐)

---

## ინსტალაციის თანმიმდევრობა

```
ნაბიჯი 1: CLAUDE.md მოთავსება repo root-ში
           └→ Claude Code იცის პროექტის კონტექსტი

ნაბიჯი 2: Claude Mem ინსტალაცია
           └→ სესიებს შორის მეხსიერება

ნაბიჯი 3: Caveman skill (Full mode)
           └→ 65% ტოკენის ეკონომია

ნაბიჯი 4: GSD skill
           └→ spec-driven workflow

ნაბიჯი 5: Graphify
           └→ კოდბაზის knowledge graph

ნაბიჯი 6: Code Review Graph MCP
           └→ persistent კოდბაზის რუკა, 49x ეკონომია

ყველა ეს → Claude Code მზადაა ALEKSANDRA_BRAIN-ზე მუშაობისთვის
```

---

## დამატებითი skills (სურვილისამებრ)

| Skill | ⭐ | რისთვის | ლინკი |
|-------|-----|---------|-------|
| Everything Claude Code | 165K | ყოვლისმომცველი optimization | https://github.com/affaan-m/everything-claude-code |
| Superpowers | 165K | spec-driven methodology | https://github.com/obra/superpowers |
| Spec Kit (GitHub official) | 90K | /specify /plan /tasks /implement | https://github.com/github/spec-kit |
| Matt Pocock Skills | 55K | TypeScript/React best practices | https://github.com/mattpocock/skills |
| Agent Skills (Addy Osmani) | 21K | production-grade engineering | https://github.com/addyosmani/agent-skills |
| n8n Skills | 4.6K | n8n workflow expert | https://github.com/czlonkowski/n8n-skills |
| Architecture Diagram Gen | 4.3K | არქიტექტურის დიაგრამები | https://github.com/Cocoon-AI/architecture-diagram-generator |
| Headroom | 1.5K | context 70-95% optimization | https://github.com/chopratejas/headroom |
| Oh My ClaudeCode | 30K | multi-agent orchestration | https://github.com/yeachan-heo/oh-my-claudecode |

---

## შედეგი

ეს 6 ინსტრუმენტი ერთად უზრუნველყოფს:

**მეხსიერება:** CLAUDE.md (სტატიკური) + Claude Mem (დინამიკური) = Claude Code არასოდეს იწყებს ნულიდან

**ეკონომია:** Caveman (65%) + Graphify (71×) + Code Review Graph (49×) = API ხარჯი მინიმუმამდე

**სტრუქტურა:** GSD (spec→plan→code→test) = ყოველი ამოცანა ორგანიზებული

**ეფექტურობა:** ნაცვლად 5 საათისა per ამოცანა → 1-2 საათი

ფუნდამენტის ფუნდამენტი მზადაა. შემდეგ → ბაზები, n8n, CrewAI, MCP-ები.
