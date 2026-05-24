# VS Code/Claude პრომპტი - 30_DIMENSIONS

## პრომპტი (გადააკოპირე და მიეცი Claude-ს ან Cursor-ს)

```
შენ ხარ ALEKSANDRA_BRAIN v7.0 პროექტის developer assistant.

კონტექსტი:
- პროექტი: ALEKSANDRA_BRAIN, ციფრული ტყუპის არქიტექტურა
- ფაზა: v6.0 → v7.0 მიგრაცია
- მიზანი: ციფრული ტყუპის სრული დანერგვა 18 კვირაში
- ბიუჯეტი: $80-100/თვე

დღევანდელი ამოცანა:

შექმენი 13 ფაილი 30_DIMENSIONS-ში, თითო ფაილი ~10 KB. სტრუქტურა: 0 განზომილების სახელი + სტატისტიკური ფორმა, 1 რას აღწერს განზომილება (კლინიკური დანიშნულება), 2 საწყისი prior-ის წყაროები (PubMed, BMC reports, BONBID-HIE dataset), 3 განახლების ფორმულა (likelihood function), 4 დაკავშირებული განზომილებები SCM-ში, 5 ცდის სტრატეგია, 6 წყაროები.

ფოლდერი: 30_DIMENSIONS (13 განზომილების detail)
ფაილების რაოდენობა: 13

ფაილების სია:
- 30_DIM_01_CYST_VOLUME.md: განზომილება 1
- 31_DIM_02_BRAINSTEM_FUNCTION.md: განზომილება 2
- 32_DIM_03_SEIZURE_FREQUENCY.md: განზომილება 3
- 33_DIM_04_MUSCLE_TONE.md: განზომილება 4
- 34_DIM_05_EYE_TRACKING.md: განზომილება 5
- 35_DIM_06_HEAD_CONTROL.md: განზომილება 6
- 36_DIM_07_GMFCS_LEVEL.md: განზომილება 7
- 37_DIM_08_BAYLEY_COGNITION.md: განზომილება 8
- 38_DIM_09_FEEDING.md: განზომილება 9
- 39_DIM_10_RESPIRATORY.md: განზომილება 10
- 3A_DIM_11_CSF_BIOMARKERS.md: განზომილება 11
- 3B_DIM_12_NEUROPLASTICITY_WINDOW.md: განზომილება 12
- 3C_DIM_13_FAMILY_READINESS.md: განზომილება 13


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
- Read, Write, healthcare MCP (PubMed search)

შემდეგი ნაბიჯი: წინ წადი FILE_PLAN.md-ის სესიების ცხრილის თანმიმდევრობით.
```

## პრომპტის გამოყენების ინსტრუქცია

1. გადააკოპირე ზემოთა code block მთლიანად
2. გადააცი Claude.ai-ს, Cursor-ს, ან VS Code Continue.dev-ს
3. დარწმუნდი რომ სასურველი MCP servers ჩართულია: Read, Write, healthcare
4. პრომპტი დასრულდება როცა შესაბამისი verifier passes

## საჭირო MCP servers

Read, Write, healthcare MCP (PubMed search)

## შემოწმება

- [ ] 13 ფაილი შექმნილია 30_DIMENSIONS-ში
- [ ] ცარიელი თხრობა არ არის (ცხრილი/კოდი/რიცხვები სრულდება)
- [ ] verifier გადადის PASS-ში
