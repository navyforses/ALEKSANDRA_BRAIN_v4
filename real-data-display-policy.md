# Real Data Display Policy

## ძირითადი წესი

პორტალის UI-მ უნდა აჩვენოს მხოლოდ ის მონაცემი, რომელიც მოდის არსებული ინფრასტრუქტურის რეალური წყაროდან, მაგალითად Supabase-ის ცხრილებიდან ან უკვე დამოწმებული repository data ფაილებიდან. თუ კონკრეტული რაოდენობა, claim, risk note, doctor question ან summary რეალურ წყაროში არ არსებობს, ეკრანზე უნდა გამოჩნდეს პირდაპირი no-data მდგომარეობა: **„მონაცემი არ არის“**.

## რა არ უნდა მოხდეს

UI-მ არ უნდა გამოიყენოს illustrative, mock, estimated ან marketing-style რაოდენობები. არ უნდა გამოჩნდეს `12.8k`, `742`, `173`, `96`, პროცენტები, ready questions, risk note counts ან სხვა რიცხვები, თუ ისინი runtime data source-დან არ არის მიღებული. ტექსტი, რომელიც აღწერს გვერდის მიზანს, შეიძლება დარჩეს როგორც UX განმარტება, მაგრამ ის არ უნდა ფორმულირდეს ისე, თითქოს უკვე არსებობს კონკრეტული კლინიკური ან კვლევითი ჩანაწერი.

## fallback მოდელი

| მონაცემის ტიპი | რეალური მონაცემი არსებობს | რეალური მონაცემი არ არსებობს |
|---|---|---|
| რაოდენობა/metric | გამოჩნდეს runtime count ან source-derived value | გამოჩნდეს „მონაცემი არ არის“ |
| evidence/claim | გამოჩნდეს მხოლოდ source-backed item | გამოჩნდეს „მონაცემი არ არის“ |
| uncertainty/risk | გამოჩნდეს მხოლოდ რეალური ჩანაწერი ან curated note | გამოჩნდეს „მონაცემი არ არის“ |
| doctor question | გამოჩნდეს მხოლოდ curated/generated-from-source question, თუ წყარო არსებობს | გამოჩნდეს „მონაცემი არ არის“ |
| brief item | გამოჩნდეს მხოლოდ source-backed brief section | გამოჩნდეს „მონაცემი არ არის“ |

## არსებული redesign-ის გამოყენების წესი

`PortalContent` უნდა დარჩეს როგორც layout და topic framing layer, მაგრამ hardcoded factual arrays უნდა გაუქმდეს ან გადაკეთდეს no-data fallback-ად. გვერდის სათაური, subtitle და research-only boundary შეიძლება დარჩეს, რადგან ისინი navigation/UX ტექსტებია. ყველა factual-looking card, სტატისტიკა და bullet list უნდა დაექვემდებაროს source-backed rendering-ს.

## Doctor Brief Builder-ის წესი

Doctor Brief Builder არ უნდა შეიქმნას როგორც ახალი ცალკე საიტი. ის უნდა ჩაშენდეს არსებულ `viewer` ინფრასტრუქტურაში. brief შეიძლება აიწყოს მხოლოდ რეალური source-backed მონაცემებიდან. თუ თემაზე არც evidence, არც risk note და არც doctor question არ არსებობს, brief-ში უნდა ეწეროს: **„მონაცემი არ არის“**.
