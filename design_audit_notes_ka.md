# დიზაინისა და შიგთავსის აუდიტის სამუშაო ჩანაწერები

## საწყისი გვერდი `/ka`

საწყისი გვერდი ამჟამად ხაზს უსვამს ტექნიკურ ფაზებს, workflow visibility-ს და privacy-ს, მაგრამ ნაკლებად აჩვენებს სისტემის სრულ შესაძლებლობებს. ვიზუალურად ძალიან თეთრი, მინიმალისტური და სტატიკურია; არ ჩანს „ცოცხალი research brain“-ის შეგრძნება, მონაცემთა ქსელი, ჰიპოთეზების pipeline, AI-თან ურთიერთობა ან ოჯახის/ექიმის/მკვლევრის განსხვავებული სცენარები. მარჯვენა BRAIN პანელი დიდ ადგილს იკავებს, თუმცა HTTP 503 შეცდომა პირველივე ეკრანზე ნეგატიურ შთაბეჭდილებას ქმნის.

## Dashboard გვერდი `/ka/dashboard`

Dashboard-ს აქვს სწორი მიზანი — ოჯახისთვის ხილული workflow-ის სტატუსი — მაგრამ ცარიელი Supabase მდგომარეობა ვიზუალურად დომინირებს. მთავარი მესიჯი უფრო ტექნიკურია: RLS smoke, Supabase env, SERVICE_ROLE_KEY. ოჯახისთვის ან გუნდისთვის უფრო სასარგებლო იქნებოდა capability-first presentation: რა იცის სისტემამ, რა შემოდის, როგორ ფასდება მტკიცებულებები, რა ელოდება გადამოწმებას, რა არის უსაფრთხოების საზღვარი. ვიზუალური KPI ბარათები ცარიელია და არ აჩვენებს პოტენციურ მონაცემებით მდიდარ მდგომარეობას.

## Hypotheses გვერდი `/ka/hypotheses`

Hypotheses გვერდი ყველაზე ძლიერი ფუნქციის — evidence-linked hypothesis validation — საწყისად სწორად ასახელებს, მაგრამ ცარიელი მონაცემების დროს შესაძლებლობა არ ჩანს. მომხმარებელი ხედავს ორ KPI-ს და configuration warning-ს, თუმცა ვერ ხედავს როგორი შეიძლება იყოს რეალური workflow: AI reasoning, მტკიცებულების ხარისხი, urgency, feasibility, next action, curator decision და linked papers. საჭირო არის demo/illustrative state ან capability preview, რათა გვერდმა მონაცემების არქონის დროსაც ახსნას სისტემის ღირებულება.

## Therapies გვერდი `/ka/therapies`

Therapies გვერდი მუშაობს tracker-ის იდეაზე, მაგრამ ვიზუალურად ისევ ნულები და გარემოს შეცდომა დომინირებს. განსაკუთრებით თვალში ხვდება ინგლისურად დარჩენილი technical error: `SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is not configured`. გვერდს აკლია თერაპიის კანდიდატის rich card, სადაც ერთად გამოჩნდება evidence strength, time window, eligibility, location, cost, clinical status და disclaimer. ასეთით უკეთ გამოჩნდებოდა, რომ ეს არის ოპერაციული decision-support კონტექსტი და არა მკურნალობის რეკომენდაცია.

## Brain გვერდი `/ka/brain`

Brain გვერდი ყველაზე დიდ პოტენციალს ატარებს, რადგან აქ ჩანს ციფრული ტყუპი / 3D მოდელი, ექიმის/მშობლის/მკვლევრის ხედები და MRI upload-ის იდეა. თუმცა ამჟამად ძირითადი არე ცარიელი placeholder-ია და შესაძლებლობა მხოლოდ ტექსტითაა ახსნილი. კარგი დიზაინი აქ უნდა იყოს hero-grade: მუქი/მედიკური visualization canvas, layer controls, role-based tabs, lesion/preserved legend, safety copy და clear upload/preview workflow. ეს გვერდი უნდა გახდეს პროექტის ემოციური და ტექნოლოგიური ცენტრი.

## Timeline გვერდი `/ka/timeline`

Timeline გვერდი ამჟამად ქრონოლოგიის მარტივი ცარიელი ბარათია. იდეა სწორია, მაგრამ ვერ აჩვენებს, რომ სისტემა შეიძლება გახდეს ბავშვის ისტორიის, კვლევითი გადაწყვეტილებების და თერაპიული window-ების ერთიანი რუკა. საჭიროა ვიზუალური timeline, event categories, evidence attachments, clinical/research distinction და „what changed since last visit“ ტიპის summary.

## გენერირებული mockup-ების სწრაფი შემოწმება

Concept A — Clinical Intelligence Command Center წარმატებით აჩვენებს სისტემას, როგორც მაღალი ინფორმაციულობის მქონე სამედიცინო research dashboard-ს. ძლიერი მხარეებია Evidence Map → Hypothesis Validation → Therapy Candidates pipeline, მარჯვენა BRAIN assistant და safety boundary. ეს მიმართულება ყველაზე ეფექტურია მკვლევრისა და ექიმისთვის, თუმცა რეალურ UI-ში ტექსტის სიმჭიდროვე უნდა დავარეგულიროთ, რომ dashboard არ გადაიტვირთოს.

Concept B — Family-Safe Research Journey ყველაზე გასაგებია მშობლისა და ოჯახის ხედისთვის. ის კარგად ცვლის ტექნიკურ სტატუსებს ადამიანის ენაზე: „what changed today“, „questions for doctor“, „evidence being reviewed“ და safety boundary. ეს მიმართულება განსაკუთრებით გამოსადეგია public/parent-facing homepage-ისთვის ან family mode-ისთვის, რადგან საიტის შესაძლებლობას ემოციურად და პრაქტიკულად ხსნის.

