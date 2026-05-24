# VS Code/Claude პრომპტი - 50_TECH

## პრომპტი (გადააკოპირე და მიეცი Claude-ს ან Cursor-ს)

```
შენ ხარ ALEKSANDRA_BRAIN v7.0 პროექტის developer assistant.

კონტექსტი:
- პროექტი: ALEKSANDRA_BRAIN, ციფრული ტყუპის არქიტექტურა
- ფაზა: v6.0 → v7.0 მიგრაცია
- მიზანი: ციფრული ტყუპის სრული დანერგვა 18 კვირაში
- ბიუჯეტი: $80-100/თვე

დღევანდელი ამოცანა:

შექმენი 11 ფაილი 50_TECH-ში. თითო ფაილი ~20 KB. სტრუქტურა: 0 ტექნოლოგიის სახელი + ვერსია + ლიცენზია, 1 რას აკეთებს ფაქტობრივად, 2 რატომ აირჩა v7.0-ში (alternatives რეჯექტი), 3 ინსტალაცია (pip install, docker run, npm install), 4 მინიმალური მუშა მაგალითი (Hello World style), 5 AKB-ში ინტეგრაცია, 6 cost projection, 7 წყაროები + ოფიციალური docs.

ფოლდერი: 50_TECH (11 ახალი ტექნოლოგიის სიღრმე)
ფაილების რაოდენობა: 11

ფაილების სია:
- 50_TECH_PYMC_NUMPYRO.md: ბაიესისეული backend (Apache 2.0)
- 51_TECH_DOWHY_CAUSALNEX.md: მიზეზშედეგობრიობა
- 52_TECH_TVB_DOCKER.md: ნეირონული მასების სიმულაცია
- 53_TECH_PLOTLY_REACT_FLOW_VIS.md: Frontend visualization stack
- 54_TECH_PYDANTIC_CSP_MIDDLEWARE.md: ფიზიკური წესების ჩაშენება
- 55_TECH_EVENT_SOURCING_POSTGRES.md: Time-travel debugging
- 56_TECH_LITELLM_MULTIMODEL_ROUTING.md: Multi-vendor routing
- 57_TECH_GEMINI_DEEP_RESEARCH.md: TxGemma parallel
- 58_TECH_CLAUDE_EXTENDED_THINKING.md: Causal validation
- 59_TECH_VERCEL_AI_SDK_ORCHESTRATION.md: Frontend streaming
- 5A_TECH_FLOWER_PYSYFT_FEDERATED.md: v8.0 ფედერირებული საფუძველი


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
- Read, Write, WebSearch (latest versions, pricing)

შემდეგი ნაბიჯი: წინ წადი FILE_PLAN.md-ის სესიების ცხრილის თანმიმდევრობით.
```

## პრომპტის გამოყენების ინსტრუქცია

1. გადააკოპირე ზემოთა code block მთლიანად
2. გადააცი Claude.ai-ს, Cursor-ს, ან VS Code Continue.dev-ს
3. დარწმუნდი რომ სასურველი MCP servers ჩართულია: Read, Write, WebSearch
4. პრომპტი დასრულდება როცა შესაბამისი verifier passes

## საჭირო MCP servers

Read, Write, WebSearch (latest versions, pricing)

## შემოწმება

- [ ] 11 ფაილი შექმნილია 50_TECH-ში
- [ ] ცარიელი თხრობა არ არის (ცხრილი/კოდი/რიცხვები სრულდება)
- [ ] verifier გადადის PASS-ში
