# VS Code/Claude პრომპტი - 60_SITE_VIEWS

## პრომპტი (გადააკოპირე და მიეცი Claude-ს ან Cursor-ს)

```
შენ ხარ ALEKSANDRA_BRAIN v7.0 პროექტის developer assistant.

კონტექსტი:
- პროექტი: ALEKSANDRA_BRAIN, ციფრული ტყუპის არქიტექტურა
- ფაზა: v6.0 → v7.0 მიგრაცია
- მიზანი: ციფრული ტყუპის სრული დანერგვა 18 კვირაში
- ბიუჯეტი: $80-100/თვე

დღევანდელი ამოცანა:

შექმენი 8 ფაილი 60_SITE_VIEWS-ში. თითო ფაილი ~15 KB. სტრუქტურა: 0 ხედის სახელი + URL path, 1 ვინ ხედავს (ცოლი, ექიმი, შაკო), 2 wireframe (ASCII art ან Mermaid diagram), 3 UI components (shadcn/ui), 4 data fetching (SWR, Supabase), 5 i18n keys (en + ka), 6 accessibility (ARIA, keyboard nav), 7 mobile responsiveness.

ფოლდერი: 60_SITE_VIEWS (8 ხედი Next.js საიტზე)
ფაილების რაოდენობა: 8

ფაილების სია:
- 60_VIEW_TWIN_STATUS_NEW.md: 13 განზომილების snapshot ხედი (NEW)
- 61_VIEW_CAUSAL_GRAPH_NEW.md: DAG, vis.js (NEW)
- 62_VIEW_SIMULATION_STUDIO_NEW.md: ექიმის scenario builder (NEW)
- 63_VIEW_BELIEF_DRIFT_NEW.md: რწმენის ცვლილების ისტორია (NEW)
- 64_VIEW_STATUS_COCKPIT_REFACTOR.md: + twin snapshot
- 65_VIEW_HYPOTHESES_REFACTOR.md: + სიმულაცია
- 66_VIEW_RESEARCH_PULSE_REFACTOR.md: + twin filter
- 67_VIEW_FAMILY_INBOX_REFACTOR.md: + აქტიური შეკითხვები


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
- Read, Write, Plan, code-review-graph

შემდეგი ნაბიჯი: წინ წადი FILE_PLAN.md-ის სესიების ცხრილის თანმიმდევრობით.
```

## პრომპტის გამოყენების ინსტრუქცია

1. გადააკოპირე ზემოთა code block მთლიანად
2. გადააცი Claude.ai-ს, Cursor-ს, ან VS Code Continue.dev-ს
3. დარწმუნდი რომ სასურველი MCP servers ჩართულია: Read, Write, Plan, code-review-graph
4. პრომპტი დასრულდება როცა შესაბამისი verifier passes

## საჭირო MCP servers

Read, Write, Plan, code-review-graph

## შემოწმება

- [ ] 8 ფაილი შექმნილია 60_SITE_VIEWS-ში
- [ ] ცარიელი თხრობა არ არის (ცხრილი/კოდი/რიცხვები სრულდება)
- [ ] verifier გადადის PASS-ში
