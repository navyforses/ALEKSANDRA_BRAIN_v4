# ALEKSANDRA_BRAIN_v4 — სრული frontend prototype-ის კომპონენტური გეგმა

## მიზანი

Prototype-ის მიზანია, არსებული კვლევითი მონაცემები და ALEKSANDRA_BRAIN-ის შესაძლებლობები გამოჩნდეს არა როგორც მშრალი ცხრილები, არამედ როგორც **ცოცხალი კვლევითი ოპერაციული სისტემა**. მთავარი ნარატივი უნდა იყოს: ოჯახისთვის გასაგები გზა, კლინიკური გუნდისთვის სანდო evidence intelligence და მკვლევრისთვის hypotheses → therapies → brain/timeline კავშირის ხილული რუკა.

## დიზაინის პრინციპი

საიტი უნდა დარჩეს პროფესიონალური და სამედიცინო-უსაფრთხო, მაგრამ უნდა მიიღოს უფრო ძლიერი hierarchy, მკაფიო demo-state და reusable UI კომპონენტები. ქართული ტექსტი უნდა იყოს პირველადი, გასაგები და არა ზედმეტად ტექნიკური; ინგლისური ვერსია უნდა დარჩეს მხარდაჭერილი.

| სფერო | არსებული პრობლემა | Prototype გადაწყვეტა |
|---|---|---|
| შინაარსი | გვერდები აღწერს მონაცემებს, მაგრამ არ აჩვენებს სისტემის ღირებულებას | თითოეულ გვერდს ექნება hero, capability summary, workflow cards და safety boundary |
| ვიზუალური ენა | ბევრი ერთნაირი თეთრი ბარათი და სუსტი hierarchy | gradient shell, glass cards, status pills, metric tiles, evidence pipeline |
| მონაცემების აღქმა | Supabase ცარიელ ან შეცდომის მდგომარეობაში გვერდი სუსტი ჩანს | ყველა მთავარ გვერდზე დაემატება sample/demo state, რომელიც განმარტავს სისტემის პოტენციალს |
| კომპონენტობა | UI ლოგიკა განმეორებადია გვერდებში | შეიქმნება reusable prototype components: hero, metric, status, workflow, safety, brain preview, therapy card |

## Prototype კომპონენტები

| კომპონენტი | დანიშნულება | სად გამოიყენება |
|---|---|---|
| `PrototypeShell` | საერთო ფონური სისტემა, max-width, ზედა summary rail | ყველა prototype გვერდი |
| `PrototypeHero` | გვერდის ძლიერი შესავალი, CTA/quick stats და trust labels | Home, Dashboard, Hypotheses, Therapies, Brain, Timeline |
| `MetricTile` | მოკლე KPI/სიგნალის ჩვენება | Dashboard, Therapies, Home |
| `StatusPill` | evidence/status/confidence ტონების ვიზუალური კოდი | ყველა მონაცემიან გვერდზე |
| `CapabilityCard` | შესაძლებლობების card-based ახსნა | Home |
| `EvidencePipeline` | research ingestion → hypothesis → therapy → monitoring workflow | Home, Dashboard |
| `SafetyBoundary` | medical safety და human-in-the-loop განმარტება | Home, Therapies, Hypotheses |
| `BrainSignalPanel` | brain/digital twin განცდის UI preview | Home, Brain |
| `TimelineRail` | timeline events და next actions | Timeline, Dashboard |
| `TherapyPrototypeCard` | therapy catalog-ის უკეთესი reading experience | Therapies |
| `HypothesisPrototypeCard` | hypothesis queue-ის priority/safety/evidence structure | Hypotheses |

## განხორციელების ფარგლები ამ sprint-ში

ამ sprint-ში აშენდება reusable კომპონენტების ფენა და გადაკეთდება ძირითადი ზედაპირები: homepage, dashboard, hypotheses, therapies, brain და timeline. Papers/Today/Knowledge გვერდები შეიძლება დარჩეს შემდეგ sprint-ში სრული content deep-dive-ისთვის, მაგრამ navigation და საერთო shell უკვე მოემზადება მათთვისაც.

## Quality gate

ცვლილებების შემდეგ უნდა გაეშვას `npm run check`, რაც მოიცავს lint, TypeScript typecheck და production build-ს. ასევე უნდა გაიხსნას ძირითადი ქართული გვერდები ბრაუზერში და შეინახოს ვიზუალური შემოწმების შენიშვნები.
