# VS Code/Claude პრომპტი - 20_PILLARS

## პრომპტი (გადააკოპირე და მიეცი Claude-ს ან Cursor-ს)

```
შენ ხარ ALEKSANDRA_BRAIN v7.0 პროექტის developer assistant.

კონტექსტი:
- პროექტი: ALEKSANDRA_BRAIN, ციფრული ტყუპის არქიტექტურა
- ფაზა: v6.0 → v7.0 მიგრაცია
- მიზანი: ციფრული ტყუპის სრული დანერგვა 18 კვირაში
- ბიუჯეტი: $80-100/თვე

დღევანდელი ამოცანა:

შექმენი 10 ფაილი 20_PILLARS-ში თითო ბურჯისთვის. თითო ფაილი ~25 KB. სტრუქტურა თითო ფაილში: 0 რეზიუმე, 1 დანიშნულება v7.0-ში, 2 v6.0-დან ცვლილება, 3 ცენტრალური მექანიკა (კოდის სკეტჩი Python ან TypeScript), 4 ცდის სტრატეგია, 5 ღია საკითხები. პრიორიტეტი: 26, 27, 28, 29 (4 ახალი ბურჯი) უპირველესია, შემდეგ 20-25 (არსებული რეფაქტორი).

ფოლდერი: 20_PILLARS (10 ბურჯის სრული აღწერა)
ფაილების რაოდენობა: 10

ფაილების სია:
- 20_PILLAR_I_MEMORY_BELIEF_STATE.md: მეხსიერების ფენა + PyMC backend
- 21_PILLAR_II_COGNITION_NEUROSYMBOLIC.md: კოგნიცია + ნეიროსიმბოლური wiring
- 22_PILLAR_III_VISUALIZATION_UNCERTAINTY.md: NiiVue + R3F + Plotly uncertainty bands
- 23_PILLAR_IV_OBSERVABILITY_DRIFT.md: Langfuse + custom belief drift dashboards
- 24_PILLAR_V_ACTION_ACTIVE_QUESTIONS.md: Telegram, Gmail, აქტიური შეკითხვები
- 25_PILLAR_VI_VALIDATION_CALIBRATION.md: twin vs რეალობა შედარება
- 26_PILLAR_VII_CAUSALITY_NEW.md: DoWhy + CausalNex + SCM editor (NEW)
- 27_PILLAR_VIII_SIMULATION_NEW.md: TVB Docker + Monte Carlo + Simulation Studio (NEW)
- 28_PILLAR_IX_ACTIVE_LEARNING_NEW.md: EIG + question generator + rate limiter (NEW)
- 29_PILLAR_X_CONSTITUTIONAL_CODE_NEW.md: 13 წესის ფიზიკური ჩაშენება (NEW)


კრიტიკული წინაპირობა:
1. წაიკითხე ALEKSANDRA_BRAIN_v7_FILE_PLAN.md (ცენტრალური გეგმა)
2. წაიკითხე ALEKSANDRA_BRAIN_v7_DIGITAL_TWIN_ARCHITECTURE.md (არქიტექტურა)
3. წაიკითხე v7_architecture/AI_BRAIN.md (system prompt)
4. წაიკითხე ამავე ფოლდერის README.md
5. დაიწყე ფაილების შექმნა თანმიმდევრობით

ენა: ქართული default. კოდი ინგლისურად. ბმულები ინგლისურად.

ხელშეუხებელი წესები:
- არასოდეს არ შექმნა ფაილი ცარიელი თხრობით — გამოიყენე ცხრილები, კოდი, კონცრეტული რიცხვები.
- არ გაგრძელო რეპეტიციული phrasing რომელიც generation loop-ში გადადის (აიკრძალე filler-სიტყვების 2× განმეორება ერთ პარაგრაფში).
- ყოველი ფაქტი მოითხოვს ციტატას (PubMed, GitHub, ოფიციალური დოკუმენტაცია).
- ბიუჯეტი hard stop $5 ერთი ცდისთვის — ამის გადაცილებამდე საჭიროა შაკოს დადასტურება.

რეკომენდებული tools:
- Read, Write, WebSearch (DoWhy, PyMC docs)

შემდეგი ნაბიჯი: წინ წადი FILE_PLAN.md-ის სესიების ცხრილის თანმიმდევრობით.
```

## პრომპტის გამოყენების ინსტრუქცია

1. გადააკოპირე ზემოთა code block მთლიანად
2. გადააცი Claude.ai-ს, Cursor-ს, ან VS Code Continue.dev-ს
3. დარწმუნდი რომ სასურველი MCP servers ჩართულია: Read, Write, WebSearch
4. პრომპტი დასრულდება როცა შესაბამისი verifier passes

## საჭირო MCP servers

Read, Write, WebSearch (DoWhy, PyMC docs)

## შემოწმება

- [ ] 10 ფაილი შექმნილია 20_PILLARS-ში
- [ ] ცარიელი თხრობა არ არის (ცხრილი/კოდი/რიცხვები სრულდება)
- [ ] verifier გადადის PASS-ში
