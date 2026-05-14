# Phase 0 Exit Report

> ფაზის გასაშვები ანგარიში. ROADMAP-ის Phase-exit gate-ი მოითხოვს, რომ ეს ფაილი
> ხელით შევსებული იყოს სანამ Phase 1 დაიწყება. ცარიელი ფაილი = ფაზა დახურული არ არის.

---

## სათაური ინფორმაცია

| ველი | მნიშვნელობა |
|------|-------------|
| ფაზის სტატუსი | _open / closed_ |
| Drill ჩატარდა | _YYYY-MM-DD HH:MM_ |
| Drill ჩატარა | _ვინ_ |
| Git commit hash | _e.g. abc1234_ |

---

## 1. CI-ის 8-პუნქტიანი ჩეკლისტი

ROADMAP-ის Phase 0 success criteria. ცოცხალი screenshot-ი / log-ი ან მითითება სად ვნახო.

| # | ტესტი | სტატუსი | მტკიცებულება |
|---|-------|---------|--------------|
| 1 | MRI-leak import-lint — ცრუ PR `@niivue/*` server route-ში → CI ✗ | ☐ | _Actions URL_ |
| 2 | MRI-leak fetch-lint — `viewer/`-ში remote `fetch` → CI ✗ | ☐ | _Actions URL_ |
| 3 | Telegram `/stop` — 60წ-ში halt + Supabase row | ☐ | _runs row id_ |
| 4 | n8n budget gate — `BUDGET_LOCKED=true` ⇒ Anthropic call ✗ | ☐ | _n8n run url_ |
| 5 | Supabase RLS — ცრუ anon → `denied` | ☐ | _Supabase log_ |
| 6 | Supabase runs append-only — `UPDATE`/`DELETE` ✗ | ☐ | _SQL error msg_ |
| 7 | MCP allowlist — spider → niivue ⇒ `BLOCKED` | ☐ | _terminal log_ |
| 8 | Secret scan — ცრუ `sk-ant-...` → pre-commit ✗ + Actions ✗ | ☐ | _Actions URL_ |

**ჯამში: 0 / 8** (← შეცვალე როცა drill ჩატარდება)

---

## 2. Fire Drill — Telegram kill-switch

```text
< paste output of `python -m scripts.fire_drill --telegram` here >
```

ნამდვილი ცეცხლსაქრობი ვარჯიში — ვინმე ხელით უგზავნის `/stop`-ს ჯგუფში
ცეცხლის ჩამქრობის გაშვებისთანავე.

- **დაწყება:** _HH:MM:SS_
- **`/stop` გაგზავნა:** _HH:MM:SS_
- **სკრიპტი გაჩერდა:** _HH:MM:SS_
- **დახარჯული ხარჯი:** $_X.XXXX_
- **Supabase row id:** _UUID_
- **შედეგი:** ☐ PASS / ☐ FAIL

---

## 3. Fire Drill — n8n budget gate

```text
< paste output of `python -m scripts.fire_drill --budget` here >
```

გავუშვით `daily-budget-gate`-ის variable `BUDGET_LOCKED` ხელით `true`-ზე.

- **დაწყება:** _HH:MM:SS_
- **`BUDGET_LOCKED=true` ჩაიწერა:** _HH:MM:SS_
- **სკრიპტი გაჩერდა:** _HH:MM:SS_
- **დახარჯული ხარჯი:** $_X.XXXX_
- **Supabase row id:** _UUID_
- **შედეგი:** ☐ PASS / ☐ FAIL

---

## 4. Phase-exit Gates (ROADMAP)

ROADMAP.md-ის Phase 0 თავი ცალკე ორ gate-ს ითხოვს — სავალდებულოა Phase 1-ის
დაწყებამდე:

### MRI-leak gate (CATASTROPHIC)
- Pull request რომელშიც `viewer/app/api/*.ts` იყენებს `@niivue/*` უნდა იყოს
  ავტომატურად დახურული CI-ის მიერ.
- **ბოლო ცრუ PR URL:** _e.g. https://github.com/.../pull/N_
- **შედეგი:** ☐ მწვანე-ი main-ში

### Cost-runaway gate (HIGH)
- Fire drill (§2 ან §3) უნდა იყოს „ცოცხალი" — სკრიპტი ნამდვილ Anthropic-ის
  call-ებს უშვებდა, ნამდვილი `/stop` ან BUDGET_LOCKED-ი მას ხურავდა.
- **შედეგი:** ☐ მწვანე main-ში

---

## 5. რა იკითხება შემდეგ

თუ ყველა checkbox მწვანეა:

```bash
git checkout -b phase-1
/gsd:plan-phase 1
```

თუ ერთიც წითელია — **არ გადახვიდე Phase 1-ში**. შესწორება ჯერ.

---

## 6. ცნობარი

- დაკავშირებული გეგმა: [.planning/PROJECT.md](../.planning/PROJECT.md), [.planning/ROADMAP.md](../.planning/ROADMAP.md), [.planning/REQUIREMENTS.md](../.planning/REQUIREMENTS.md)
- კოდი: [mcp/panic_stop.py](../mcp/panic_stop.py), [workflows/daily-budget-gate.json](../workflows/daily-budget-gate.json), [scripts/fire_drill.py](../scripts/fire_drill.py)
- RUNBOOK-ი: [docs/RUNBOOK-kill-switch.md](RUNBOOK-kill-switch.md), [docs/RUNBOOK-supabase.md](RUNBOOK-supabase.md)
