# Real-data UI inventory

ამ ეტაპის მიზანია პორტალში არსებული hardcoded/illustrative კონტენტის გამოვლენა, რათა საიტზე აღარ გამოჩნდეს ისეთი ინფორმაცია, რომელიც რეალურ წყაროს ან მონაცემთა ცხრილს არ უკავშირდება.

## ძირითადი მიგნებები

| ადგილი | მიგნება | მოქმედება |
|---|---|---|
| `viewer/components/portal/PortalContent.tsx` | მთავარ topic model-ში მრავალი რაოდენობა და ტექსტი არის hardcoded, მაგალითად `12.8k`, `742`, `173`, `96`, `219`, ასევე narrative claims წყაროების/claim-ების/კითხვების შესახებ. | ეს მონაცემები არ უნდა გამოჩნდეს როგორც ფაქტი, თუ არ მოდის რეალური data source-დან. საჭიროებს no-data/fallback მოდელს. |
| `viewer/app/[locale]/hypotheses/[id]/page.tsx` | დეტალური ჰიპოთეზის გვერდი უკვე იყენებს `getRows`-ს Supabase-დან და ცარიელ შედეგზე `notFound`/empty states-ს. | ეს pattern უნდა დარჩეს: რეალური row არსებობს → ჩანს; არ არსებობს → არ ხდება შევსება გამოგონილი მონაცემით. |
| `viewer/lib/supabase.ts` | არსებობს server-side `getRows` და `getCount`, რომლებიც config-ის არქონისას აბრუნებს `configured: false`, ცარიელ rows-ს და error-ს. | no-data UI უნდა დაეყრდნოს სწორედ ამ სემანტიკას: არაკონფიგურირებული/ცარიელი/შეცდომა → „მონაცემი არ არის“. |
| `viewer/components/DashboardCharts.tsx` | კომპონენტი იღებს chart data-ს props-ით, მაგრამ ტექსტი ითვლის summary-ს გადაცემული arrays-დან. | თუ arrays ცარიელია, უნდა გამოჩნდეს no-data state, არა ნულზე აგებული „დამუშავებული ნაშრომების“ ტექსტი. |

## სამუშაო წესი

საიტის UI-ში აღარ უნდა გამოჩნდეს illustrative numbers, sample claims ან generic factual-sounding statements. თუ შესაბამისი Supabase row/count/source არ არსებობს, ტექსტი უნდა იყოს მკაფიო: **„მონაცემი არ არის“**. ეს ეხება metric cards-ს, evidence lists-ს, risk notes-ს, doctor questions-ს და brief output-ს.
