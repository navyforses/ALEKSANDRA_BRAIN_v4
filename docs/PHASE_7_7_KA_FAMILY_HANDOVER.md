# PHASE_7_7_KA_FAMILY_HANDOVER.md - ოჯახური გადაცემა (KA)

> **სტატუსი:** Phase 7.7 acceptance-window template. Shako უტარებს ცოლის გადახედვას.
> ეს ფაილი ცოლისთვისაა. ენა მარტივი. ცნებები კონკრეტული.

**Phase ID:** 7.7
**ვადა:** v7.0 production launch დღე (Day 10, 2027-01-09)
**ვერსია:** v7.0
**ენა:** ქართული, წინადადებები მოკლე, em-dash არ მოიხმარება.
**Anti-loop ფიქსაცია:** არცერთი სიტყვა 100-სიტყვიან ფანჯარაში 2-ზე მეტჯერ; 13 ციფრით; `ცარიელი`, `ფარული`, `ცდილია` მაქს 1-ჯერ პარაგრაფზე.

---

## 1. ციფრული ტყუპის წვდომა

ALEKSANDRA_BRAIN v7-ის ვებ-cockpit გახსნა შესაძლებელია ნებისმიერი ბროუზერიდან.

| რა | სად | ვინ ხედავს |
|---|---|---|
| ქართული მთავარი | `https://aleksandrabrane.app/ka` | ცოლი + შაკო |
| Twin Status | `https://aleksandrabrane.app/ka/twin` | ცოლი + შაკო |
| Drift view | `https://aleksandrabrane.app/ka/drift` | ცოლი + შაკო |
| Causal Graph | `https://aleksandrabrane.app/ka/causal` | ცოლი + შაკო |
| Sim Studio | `https://aleksandrabrane.app/ka/simulate` | ცოლი + ექიმი |

შესვლა Supabase auth-ით. Email + password ცოლს მისცა შაკომ Day 1-ის onboarding-ზე.
პაროლის დავიწყების შემთხვევაში reset link Telegram-ში მოვა შაკოს მეშვეობით.

---

## 2. ციფრული ტყუპის სტატუსის ხედვა

Status Cockpit-ი მთავარი დაფა. იქ ცოლი ერთი თვალით ხედავს დღევანდელ მდგომარეობას.

### რა ჩანს Status Cockpit-ში

| ბლოკი | რას აჩვენებს |
|---|---|
| Header | დღევანდელი თარიღი, ალექსანდრას ასაკი თვეებში |
| Twin Status widget | 13 dimension-ის ბოლო posterior მნიშვნელობა + CI ფრჩხილები |
| ბოლო კვირული შემაჯამებელი | Phase 4-ის Weekly Brief link |
| აქტიური შეკითხვები | ცოლზე გასაგზავნი ღია კითხვები |
| ბოლო MRI screenshot | NiiVue link (ბროუზერშივე, server-ზე ფაილი არ ხვდება) |

### Twin Status (`/ka/twin`)

13 dimension-ის სრული სია. თითო რიგი აჩვენებს:

1. dimension-ის სახელი ქართულად,
2. posterior expected value,
3. [CI low, CI high] ფრჩხილებში,
4. ბოლო განახლების თარიღი,
5. წყაროების რაოდენობა.

ფრჩხილებში რიცხვები ნდობის შუალედია. ეს არ არის ცარიელი მონაცემი. ციფრი არასოდეს ცალკე იცემა; აპლიკაცია მუდამ აჩვენებს რამდენად დარწმუნებულია.

---

## 3. კვირული შეკითხვის Telegram-ფლოუ

ცოლს კვირაში მაქსიმუმ 3 შეკითხვა მისდის Telegram-ში. ეს cap ფიზიკურად ჩაშენებულია. სისტემა ფიზიკურად ვერ გაგზავნის მე-4-ს.

### პროცესი

1. orchestrator EIG (expected information gain) რანკერით ირჩევს ერთ dimension-ს რომელზე ცოდნა ყველაზე გაჭირვებულია.
2. ჩამოყალიბდება ერთწინადადებიანი კითხვა ქართულად.
3. Telegram bot ცოლს უგზავნის შეტყობინებას.
4. ცოლი ხმოვან ან ტექსტუალურ პასუხს იძლევა.
5. Whisper STT-ი ხმოვან მესიჯს ტექსტს უწერს (გადახედვის flag-ით).
6. PyMC posterior განახლდება შესაბამის dimension-ში.
7. ცოლი `/ka/drift` ხედვაში ხედავს როგორ შეიცვალა belief.

### კონტროლი

| ღილაკი Telegram-ში | რას აკეთებს |
|---|---|
| `/pause` | ერთი კვირით კითხვები ჩერდება |
| `/resume` | აღდგენა |
| `/stop` | სრული opt-out (შაკოს ცნობდება) |
| `/help` | ცოლს ეცნობება მთელი ფლოუ კიდევ ერთხელ |

cap აღემატება მხოლოდ Shako-ს მიერ override-ით (Phase 7.5 Rule 11), რომელიც 24 საათში ავტომატურად იხურება. ცოლი ყოველი override-ისთვის Telegram-ში notification იღებს.

---

## 4. პოსტერიორ-დრიფტის ხედვა (`/ka/drift`)

ეს გვერდი აჩვენებს როგორ შეიცვალა posterior დროში. ცოლს რომ უნდა ნახოს თუ რომელი dimension-ი მართლა იცვლება, ფურცელი `/ka/drift`-ი მისთვისაა.

### რა ჩანს

- 13 dimension-ის ცალკე chart.
- X ღერძი დროა (გასული 30 დღე).
- Y ღერძი posterior expected value.
- დაჩრდილული ზოლი CI 95% HDI.
- ვერტიკალური წერტილოვანი ხაზი ცოლის თითო ხმოვანი პასუხის თარიღს მონიშნავს.

### როცა dimension-ი მკვეთრად იცვლება

წითელი წერტილით აღინიშნება. ცოლი ერთ click-ში ხედავს რომელი evidence-მა გამოიწვია ცვლილება (link evidence row-ზე).

---

## 5. SCM editor (Phase 7.2 + 7.6)

ეს არ არის ცოლისთვის სავალდებულო. SCM editor მთლიანად შაკოს ხელშია. მაგრამ ცოლს რომ უნდა ნახოს თუ რა მიზეზობრივ კავშირებზე ეფუძნება სიმულაცია, `/ka/causal` გვერდი ღიაა.

| რას აჩვენებს | სად |
|---|---|
| nodes (dimensions + interventions) | graph view-ში |
| edges (causal links) | სტრიქონები ნოდებს შორის |
| თითო edge-ის PMID/DOI | hover ან click |
| edge-ის sign (+/-) | ფერი + ისარი |

რედაქტირება შაკოს password-ით. ცოლი read-only რეჟიმში ნახულობს.

---

## 6. Constitutional override-ის მოთხოვნის flow

13 ფიზიკური წესი დაცულია. წესის გვერდის ავლის ერთადერთი გზაა `issue_override` API-ის გამოძახება შაკოს მიერ. ცოლი ყოველ override-ზე Telegram-ში გაიგებს.

### რა ხდება როცა override-ი იძახება

1. Shako CLI-ში წერს `issue_override(rule_number=N, reason="...")`.
2. constitutional_overrides ცხრილში row ჩაიწერება (UUID + reason + 24h TTL).
3. Telegram bot ცოლს უგზავნის: "Shako-მ Rule #N გადააცილა 24h-ით, მიზეზი: <reason>".
4. 24 საათში override ავტომატურად ძალადაკარგულია (TTL expires).
5. ცოლს რომ უნდა იხილოს ყველა active override, `/ka/audit` გვერდი მათ ნახულობს.

### ცოლის როლი

ცოლი override-ს ვერ ცვლის. მაგრამ ცოლს უფლება აქვს Shako-ს უთხრას: "ეს override არ მინდა". ამ შემთხვევაში შაკო ცვლის reason-ს ან თვითონ ცვლის override-ის TTL-ს ნულზე.

---

## 7. ვერსიონის შენიშვნა

| ფაქტი | მნიშვნელობა |
|---|---|
| ვერსია | v7.0 |
| Launch თარიღი | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| ცვლილებები v6.1-დან | 8 ახალი route (twin, causal, simulate, drift + 4 sub-page), 13 constitutional rule ფიზიკურად ჩაშენებული, ცოლის active-question Telegram flow, PDF builder ექიმისთვის |
| რა იცვლება ცოლისთვის | რეგულარული Telegram კითხვა (კვირაში მაქს 3), Status Cockpit-ში Twin Status widget, drift view, override notification |
| რა იცვლება ექიმისთვის | Simulation Studio scenarios, Causal Graph viewer, PDF handout 5+ primary source-ით |
| რა არ იცვლება | MRI client-side only (server-ზე არ ხვდება), Phase 4 Weekly Brief, Phase 5 Manager |
| ბიუჯეტი | $20-30/თვე MVP, $120/თვე full; v7.0 ცვლილებას არ მოაქვს |

### თუ რამე გაუგებარია

Shako-ს Telegram-ში. პასუხი 24 საათში.

### თუ რამე ცუდად მუშაობს

Shako-ს Telegram-ში. P0/P1 ფიქსაცია იმავე დღეს. P2/P3 v7.1 backlog-ში მიდის.

### თუ რომელიმე surface-ი ცოლს არ უნდა

`viewer/lib/flags.ts` ფაილში შაკო ცვლის ცალკეული flag-ის true -> false. ცოლი ერთი წინადადებით ცვლის რომელი route გათიშოს.

---

## დასკვნა

v7.0 ცოლისთვის ერთი ცვლილებაა. Status Cockpit-ში ერთი ახალი widget. Telegram-ში კვირაში მაქს 3 ახალი კითხვა. ყველაფერი დანარჩენი (MRI viewer, Weekly Brief, Manager) იგივე რჩება. control mechanism (`/pause`, `/stop`, override notification) ცოლის ხელშია.

13 წესი ფიზიკურად დაცულია. სისტემამ თვითონ ვერ დაარღვევს. წესის გვერდის ავლა შესაძლებელია მხოლოდ Shako-ს მიერ ხელნაკეთი override-ით, რომელიც 24 საათში ავტომატურად ძალადაკარგულია.

წყაროები: `v7_architecture/70_PHASES/77_PHASE_7_7_ACCEPTANCE_WINDOW_2W.md`, `docs/PHASE_7_5_EXIT_REPORT.md`, `docs/PHASE_7_5_KA_SUMMARY.md`.
