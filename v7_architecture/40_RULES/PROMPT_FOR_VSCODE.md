# VS Code/Claude პრომპტი - 40_RULES

## პრომპტი (გადააკოპირე და მიეცი Claude-ს ან Cursor-ს)

```
შენ ხარ ALEKSANDRA_BRAIN v7.0 პროექტის developer assistant.

კონტექსტი:
- პროექტი: ALEKSANDRA_BRAIN, ციფრული ტყუპის არქიტექტურა
- ფაზა: v6.0 → v7.0 მიგრაცია
- მიზანი: ციფრული ტყუპის სრული დანერგვა 18 კვირაში
- ბიუჯეტი: $80-100/თვე

დღევანდელი ამოცანა:

შექმენი 13 ფაილი 40_RULES-ში, თითო ფაილი ~10 KB. სტრუქტურა: 0 წესის ერთი წინადადებიანი ფორმულირება, 1 რატომ არის წესი მნიშვნელოვანი (Aleksandra-ის კონტექსტი), 2 ფიზიკური ფენა (CSP middleware, DB trigger, Pydantic schema, etc), 3 კოდის სკეტჩი (Python ან TypeScript), 4 false-positive escape hatch (როდის აქვს შაკოს უფლება გვერდის ავლა), 5 ცდის სტრატეგია, 6 audit log requirements.

ფოლდერი: 40_RULES (13 კონსტიტუციური წესის detail)
ფაილების რაოდენობა: 13

ფაილების სია:
- 40_RULE_01_MRI_CLIENT_ONLY.md: წესი 1
- 41_RULE_02_VOICE_REVIEW_REQUIRED.md: წესი 2
- 42_RULE_03_CITATION_MANDATORY.md: წესი 3
- 43_RULE_04_CONFIDENCE_INTERVALS.md: წესი 4
- 44_RULE_05_BILINGUAL_PARITY.md: წესი 5
- 45_RULE_06_PHI_FILTER.md: წესი 6
- 46_RULE_07_BUDGET_HARD_STOP.md: წესი 7
- 47_RULE_08_BELIEF_REQUIRES_EVIDENCE.md: წესი 8
- 48_RULE_09_HYPOTHESIS_MIN_SOURCES.md: წესი 9
- 49_RULE_10_SIMULATION_UNCERTAINTY.md: წესი 10
- 4A_RULE_11_QUESTION_RATE_LIMIT.md: წესი 11
- 4B_RULE_12_PDF_MIN_SOURCES.md: წესი 12
- 4C_RULE_13_VERIFIER_DEPLOYMENT_GATE.md: წესი 13


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
- Read, Write, code-review-graph (კოდის სკეტჩისთვის)

შემდეგი ნაბიჯი: წინ წადი FILE_PLAN.md-ის სესიების ცხრილის თანმიმდევრობით.
```

## პრომპტის გამოყენების ინსტრუქცია

1. გადააკოპირე ზემოთა code block მთლიანად
2. გადააცი Claude.ai-ს, Cursor-ს, ან VS Code Continue.dev-ს
3. დარწმუნდი რომ სასურველი MCP servers ჩართულია: Read, Write, code-review-graph
4. პრომპტი დასრულდება როცა შესაბამისი verifier passes

## საჭირო MCP servers

Read, Write, code-review-graph (კოდის სკეტჩისთვის)

## შემოწმება

- [ ] 13 ფაილი შექმნილია 40_RULES-ში
- [ ] ცარიელი თხრობა არ არის (ცხრილი/კოდი/რიცხვები სრულდება)
- [ ] verifier გადადის PASS-ში
