# SESSION_NOTES_WIFE.md - ცოლის Acceptance Window ჩანაწერები (KA)

> **სტატუსი:** Phase 7.7 acceptance-window template. შაკო ავსებს რეალური სესიის დროს.
> ვერიფაიერი (`scripts/verify_phase_7_7.py` check_7_7_08) ფლაგს ცვლის SKIP -> PASS როცა
> `<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>` მარკერი წაშლილია და 5 Grade ჩანაწერია
> ფორმატით `Grade: N/5` (N >= 4).

**Phase ID:** 7.7
**Persona:** ცოლი
**ვადა:** 2026-12-27 → 2027-01-09 (Day 1, Day 2, Day 7)
**ფაიფურადი ფიქსაცია (Phase 6.1 anti-loop):** არცერთი სიტყვა 100-სიტყვიან ფანჯარაში 2-ზე მეტჯერ.

---

## Day 1 - Onboarding (~30 წუთი)

**თარიღი:** <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
**ადგილი:** <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
**მონაწილეები:** ცოლი, შაკო.

### დემო-ფლოუ

| ნაბიჯი | აქტივობა | ცოლის რეაქცია |
|---|---|---|
| 1 | `/ka` Status Cockpit გახსნა, Twin Status widget-ის ჩვენება | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| 2 | "რა არის ციფრული ტყუპი?" 2-წინადადებიანი ახსნა | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| 3 | active-question კონცეფციის ახსნა (კვირაში 3-ის cap, opt-in) | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| 4 | პირველი Telegram კითხვის გაგზავნა | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |
| 5 | opt-in დადასტურება (yes/no/maybe) | <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> |

### ცოლის კითხვები + წუხილი

<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

### Day 1 დასკვნა

- opt-in მიღებული: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- პირველი კითხვა გაგზავნილი: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- ცოლის ემოციური სტატუსი (1-5): <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

---

## Day 2 - პირველი ხმოვანი პასუხის ციკლი

**თარიღი:** <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

### ფლოუ

1. ცოლი Telegram-ში ხმოვან პასუხს გზავნის.
2. Whisper STT-ი მესიჯს ტექსტში გადააქცევს.
3. პასუხის parser-ი intake_drops-ში ჩაწერს row-ს (`requires_review=true` Rule #2-ით).
4. PyMC posterior-ი განახლდება ერთ ან მეტ ციფრულ-ტყუპის dimension-ში.
5. `/ka/drift` page-ი ცვლილებას ვიზუალურად აჩვენებს.

### დაფიქსირდა

- ხმოვანი მესიჯი მოვიდა: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- STT-ი ცოლის ქართულს სწორად დაამუშავა: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- posterior-ი მართლა განახლდა: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW> (link to drift screenshot)
- ცოლის ღია კომენტარები: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

---

## Day 7 - Satisfaction Interview (15-20 წუთი)

**თარიღი:** <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

> ცოლი თვითონ აფასებს. ფასებს შაკო არ ცვლის ინტერპრეტაციით.

### 5 კრიტერიუმი (spec §2.4)

#### 1. ციფრული ტყუპის გაგება საკუთარი სიტყვებით

ცოლის ფორმულირება (2 წინადადება):
<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

**Grade: <N>/5** (5 = ნათლად აღწერა საკუთარი სიტყვებით; 1 = ვერ აიხსნა)
<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

#### 2. Status Cockpit widget-ის სარგებლიანობა

ცოლი იყენებდა ყოველდღე 7 დღის განმავლობაში?
<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

რა იპოვა ყველაზე ღირებული?
<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

**Grade: <N>/5**
<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

#### 3. active-question-მა მისი დრო პატივი სცა?

opt-in-ი მეტი კითხვისთვის ერჩია?
<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

თუ არა, რა შეცვალოს?
<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

**Grade: <N>/5**
<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

#### 4. CI ფრჩხილებში ნდობა (არ ერთობოდა?)

ცოლი ითხოვდა "მკაფიო პასუხს" (rejecting uncertainty)?
<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

თუ არა, [low, high] ფრჩხილებში ხედავდა ნდობას?
<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

**Grade: <N>/5** (5 = ფრჩხილებში ნდობდა; 1 = ფრჩხილები მისთვის ბუნდოვანი იყო)
<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

#### 5. ქართული ტექსტი ბუნებრივი იყო?

რომელიმე ფრაზა საფიქრალი ან გაუგებარი იყო?
<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

რომელ namespace-ში (Manager / Twin / Drift / Status)?
<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

**Grade: <N>/5**
<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

### Day 7 ჯამური სტატუსი

- კვირაში 2 round-trip-ი მიღწეული: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- ცოლი v7.0-ის გაგრძელებას ეთანხმება: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>
- ცოლი რომელიმე ფიჩერის გათიშვას ითხოვს: <TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

---

## შაკოს დასკვნა

<TO BE FILLED IN BY SHAKO DURING ACCEPTANCE WINDOW>

### პასუხი check_7_7_08-ისთვის

| კრიტერიუმი | Grade |
|---|---|
| 1. ციფრული ტყუპის გაგება | `Grade: <N>/5` |
| 2. Status Cockpit widget | `Grade: <N>/5` |
| 3. active-question time-respect | `Grade: <N>/5` |
| 4. CI ნდობა | `Grade: <N>/5` |
| 5. ქართული ბუნებრიობა | `Grade: <N>/5` |

ვერიფაიერი ფლაგს ცვლის PASS-ად როცა 5-ვე grade >= 4.
