# VS Code/Claude პრომპტი - 80_VERIFIERS

## პრომპტი (გადააკოპირე და მიეცი Claude-ს ან Cursor-ს)

```
შენ ხარ ALEKSANDRA_BRAIN v7.0 პროექტის developer assistant.

კონტექსტი:
- პროექტი: ALEKSANDRA_BRAIN, ციფრული ტყუპის არქიტექტურა
- ფაზა: v6.0 → v7.0 მიგრაცია
- მიზანი: ციფრული ტყუპის სრული დანერგვა 18 კვირაში
- ბიუჯეტი: $80-100/თვე

დღევანდელი ამოცანა:

შექმენი 9 ფაილი 80_VERIFIERS-ში. თითო ფაილი ~10 KB. სტრუქტურა: 0 verifier-ის სახელი, 1 ფაზის checklist (5-15 ცდა), 2 Python script-ის სტრუქტურა, 3 expected outputs, 4 fail criteria, 5 manual recovery steps. cumulative-ში: 78/78 (v6.1) → 87/87 (v7.0 final).

ფოლდერი: 80_VERIFIERS (9 verifier სკრიპტი)
ფაილების რაოდენობა: 9

ფაილების სია:
- 80_VERIFY_PHASE_7_0.md: Phase 7.0 verifier
- 81_VERIFY_PHASE_7_1.md: Phase 7.1 verifier
- 82_VERIFY_PHASE_7_2.md: Phase 7.2 verifier
- 83_VERIFY_PHASE_7_3.md: Phase 7.3 verifier
- 84_VERIFY_PHASE_7_4.md: Phase 7.4 verifier
- 85_VERIFY_PHASE_7_5.md: Phase 7.5 verifier
- 86_VERIFY_PHASE_7_6.md: Phase 7.6 verifier
- 87_VERIFY_PHASE_7_7.md: Phase 7.7 verifier
- 88_VERIFY_CUMULATIVE_V7.md: Cumulative v7 verifier (78/78 → 87/87)


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

- [ ] 9 ფაილი შექმნილია 80_VERIFIERS-ში
- [ ] ცარიელი თხრობა არ არის (ცხრილი/კოდი/რიცხვები სრულდება)
- [ ] verifier გადადის PASS-ში
