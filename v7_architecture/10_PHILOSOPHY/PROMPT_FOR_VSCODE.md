# VS Code/Claude პრომპტი - 10_PHILOSOPHY

## პრომპტი (გადააკოპირე და მიეცი Claude-ს ან Cursor-ს)

```
შენ ხარ ALEKSANDRA_BRAIN v7.0 პროექტის developer assistant.

კონტექსტი:
- პროექტი: ALEKSANDRA_BRAIN, ციფრული ტყუპის არქიტექტურა
- ფაზა: v6.0 → v7.0 მიგრაცია
- მიზანი: ციფრული ტყუპის სრული დანერგვა 18 კვირაში
- ბიუჯეტი: $80-100/თვე

დღევანდელი ამოცანა:

შექმენი 4 ფაილი 10_PHILOSOPHY-ში ფილოსოფიური ფუნდამენტისთვის. 10_DIGITAL_TWIN_METAPHOR.md (25 KB): Apollo-13-ის გადარჩენიდან ალექსანდრამდე, ჰიუსტონის ციფრული ტყუპის გადატანა AKB-ში, რა ნიშნავს ფაქტობრივად. 11_FIVE_STRUCTURAL_GAPS.md (20 KB): აღწერითობა vs წინასწარმეტყველება, კორელაცია vs მიზეზშედეგობრიობა, პასიურობა vs აქტიურობა, სტატიკურობა vs ცოცხალი რწმენა, წერილობითი vs ფიზიკური წესები. 12_BAYESIAN_FOUNDATIONS.md (20 KB): რა არის prior/likelihood/posterior, MCMC vs variational inference, PyMC-ის შესავალი. 13_CAUSAL_FOUNDATIONS.md (15 KB): do-operator, კონფაუნდერების მართვა, კონტრფაქტური მსჯელობა.

ფოლდერი: 10_PHILOSOPHY (ფილოსოფიური ფუნდამენტი)
ფაილების რაოდენობა: 4

ფაილების სია:
- 10_DIGITAL_TWIN_METAPHOR.md: Apollo-13 → ALEKSANDRA_BRAIN ფილოსოფიური ფუნდამენტი
- 11_FIVE_STRUCTURAL_GAPS.md: v6.0-ის 5 სტრუქტურული ხარვეზის სრული ანალიზი
- 12_BAYESIAN_FOUNDATIONS.md: PyMC-ის შესავალი, ცოცხალი რწმენის მათემატიკა
- 13_CAUSAL_FOUNDATIONS.md: პერლის do-calculus, კონტრფაქტური მსჯელობა


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
- Read, Write, WebSearch (Pearl-ის ფაქტებისთვის)

შემდეგი ნაბიჯი: წინ წადი FILE_PLAN.md-ის სესიების ცხრილის თანმიმდევრობით.
```

## პრომპტის გამოყენების ინსტრუქცია

1. გადააკოპირე ზემოთა code block მთლიანად
2. გადააცი Claude.ai-ს, Cursor-ს, ან VS Code Continue.dev-ს
3. დარწმუნდი რომ სასურველი MCP servers ჩართულია: Read, Write, WebSearch
4. პრომპტი დასრულდება როცა შესაბამისი verifier passes

## საჭირო MCP servers

Read, Write, WebSearch (Pearl-ის ფაქტებისთვის)

## შემოწმება

- [ ] 4 ფაილი შექმნილია 10_PHILOSOPHY-ში
- [ ] ცარიელი თხრობა არ არის (ცხრილი/კოდი/რიცხვები სრულდება)
- [ ] verifier გადადის PASS-ში
