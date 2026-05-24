# VS Code/Claude პრომპტი - 70_PHASES

## პრომპტი (გადააკოპირე და მიეცი Claude-ს ან Cursor-ს)

```
შენ ხარ ALEKSANDRA_BRAIN v7.0 პროექტის developer assistant.

კონტექსტი:
- პროექტი: ALEKSANDRA_BRAIN, ციფრული ტყუპის არქიტექტურა
- ფაზა: v6.0 → v7.0 მიგრაცია
- მიზანი: ციფრული ტყუპის სრული დანერგვა 18 კვირაში
- ბიუჯეტი: $80-100/თვე

დღევანდელი ამოცანა:

შექმენი 8 ფაილი 70_PHASES-ში. თითო ფაილი ~20 KB. სტრუქტურა: 0 ფაზის სახელი + ვადა + წინაპირობა, 1 დღიური breakdown (10-21 day plan), 2 დღევანდელი deliverables, 3 blocking dependencies, 4 verifier checklist (8-15 ცდა), 5 rollback strategy თუ ჩავარდება, 6 LLM spend tracking, 7 sprint retrospective template.

ფოლდერი: 70_PHASES (8 მიგრაციის ფაზა (18 კვირა))
ფაილების რაოდენობა: 8

ფაილების სია:
- 70_PHASE_7_0_BELIEF_FOUNDATION_4W.md: PyMC backend + 13-D schema
- 71_PHASE_7_1_MEMORY_REFACTOR_2W.md: ნეო4ჯეი → causal schema
- 72_PHASE_7_2_CAUSAL_LAYER_3W.md: DoWhy + SCM editor
- 73_PHASE_7_3_SIMULATION_ENGINE_3W.md: Monte Carlo + TVB
- 74_PHASE_7_4_ACTIVE_LEARNING_2W.md: EIG + question generator
- 75_PHASE_7_5_CONSTITUTIONAL_2W.md: 13 წესის ჩაშენება
- 76_PHASE_7_6_SITE_REFACTOR_3W.md: 4 NEW + 4 refactor views
- 77_PHASE_7_7_ACCEPTANCE_WINDOW_2W.md: ცოლის/ექიმის/შაკოს ცდა


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
- Read, Write, Plan

შემდეგი ნაბიჯი: წინ წადი FILE_PLAN.md-ის სესიების ცხრილის თანმიმდევრობით.
```

## პრომპტის გამოყენების ინსტრუქცია

1. გადააკოპირე ზემოთა code block მთლიანად
2. გადააცი Claude.ai-ს, Cursor-ს, ან VS Code Continue.dev-ს
3. დარწმუნდი რომ სასურველი MCP servers ჩართულია: Read, Write, Plan
4. პრომპტი დასრულდება როცა შესაბამისი verifier passes

## საჭირო MCP servers

Read, Write, Plan

## შემოწმება

- [ ] 8 ფაილი შექმნილია 70_PHASES-ში
- [ ] ცარიელი თხრობა არ არის (ცხრილი/კოდი/რიცხვები სრულდება)
- [ ] verifier გადადის PASS-ში
