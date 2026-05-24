# VS Code/Claude პრომპტი - A0_OPERATIONS

## პრომპტი (გადააკოპირე და მიეცი Claude-ს ან Cursor-ს)

```
შენ ხარ ALEKSANDRA_BRAIN v7.0 პროექტის developer assistant.

კონტექსტი:
- პროექტი: ALEKSANDRA_BRAIN, ციფრული ტყუპის არქიტექტურა
- ფაზა: v6.0 → v7.0 მიგრაცია
- მიზანი: ციფრული ტყუპის სრული დანერგვა 18 კვირაში
- ბიუჯეტი: $80-100/თვე

დღევანდელი ამოცანა:

შექმენი 4 ფაილი A0_OPERATIONS-ში. A0_BUDGET: line-by-line $80-100/თვე breakdown per component (Vercel, Anthropic, OpenAI, Railway, R2, etc). A1_RISKS: 15-20 რისკი table-ით (რისკი | ალბათობა | გავლენა | mitigation | owner). A2_DECISIONS: 7 გადასაწყვეტი საკითხი (PyMC vs NumPyro, TVB Docker placement, etc.) context-ით + recommendation. A3_OPEN: არგადაწყვეტილი კითხვები მომავალი სესიისთვის.

ფოლდერი: A0_OPERATIONS (ბიუჯეტი, რისკები, გადაწყვეტილებები)
ფაილების რაოდენობა: 4

ფაილების სია:
- A0_BUDGET_DETAILED.md: $80-100/თვე breakdown
- A1_RISKS_REGISTER.md: 15-20 რისკი + mitigation
- A2_DECISIONS_PENDING.md: 7 გადასაწყვეტი საკითხი
- A3_OPEN_QUESTIONS.md: რა ვერ გადავწყვიტეთ


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
- Read, Write

შემდეგი ნაბიჯი: წინ წადი FILE_PLAN.md-ის სესიების ცხრილის თანმიმდევრობით.
```

## პრომპტის გამოყენების ინსტრუქცია

1. გადააკოპირე ზემოთა code block მთლიანად
2. გადააცი Claude.ai-ს, Cursor-ს, ან VS Code Continue.dev-ს
3. დარწმუნდი რომ სასურველი MCP servers ჩართულია: Read, Write
4. პრომპტი დასრულდება როცა შესაბამისი verifier passes

## საჭირო MCP servers

Read, Write

## შემოწმება

- [ ] 4 ფაილი შექმნილია A0_OPERATIONS-ში
- [ ] ცარიელი თხრობა არ არის (ცხრილი/კოდი/რიცხვები სრულდება)
- [ ] verifier გადადის PASS-ში
