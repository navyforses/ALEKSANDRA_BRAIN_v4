# ALEKSANDRA_BRAIN — მუდმივი ვებსაიტის გაშვების გზამკვლევი

ეს დოკუმენტი აღწერს, როგორ გადაიქცეს მიმდინარე mockup-driven frontend მუდმივ საჯარო ვებსაიტად. პროექტი არის **Next.js** აპლიკაცია `viewer/` საქაღალდეში, ამიტომ რეკომენდებული ჰოსტინგი არის **Vercel** ან სხვა Node.js/Next.js თავსებადი პლატფორმა.

## რა არის უკვე მზად

| ნაწილი | სტატუსი | შენიშვნა |
|---|---:|---|
| Generated mockup დიზაინზე გადატანილი Home გვერდი | მზად | Concept B family-safe portal გადაიტანა რეალურ frontend-ში. |
| Dashboard | მზად | Concept A dark clinical command center. |
| Brain Lab | მზად | Concept C digital twin lab. |
| Hypotheses, Therapies, Timeline | მზად | გადაყვანილია იგივე generated visual system-ზე. |
| Build validation | მზად | `npm run lint` და `npm run build` წარმატებით სრულდება. |
| Vercel config | მზად | დამატებულია `viewer/vercel.json`. |
| Environment example | მზად | დამატებულია `viewer/.env.example`. |

## Vercel-ზე გაშვება

Vercel საუკეთესო გზაა, რადგან აპლიკაციაში არსებობს server-rendered გვერდები და API routes. GitHub Pages მხოლოდ სტატიკურ HTML-ს ემსახურება და ამ პროექტისთვის სრულად საკმარისი არ არის.

1. შედით [Vercel](https://vercel.com)-ში და აირჩიეთ **Add New Project**.
2. დააკავშირეთ GitHub repository: `navyforses/ALEKSANDRA_BRAIN_v4`.
3. Project settings-ში მიუთითეთ **Root Directory**: `viewer`.
4. Build command დარჩეს `npm run build`.
5. Install command დარჩეს `npm install`.
6. Environment Variables-ში დაამატეთ:

| Variable | მნიშვნელობა | აუცილებელია? |
|---|---|---:|
| `SUPABASE_URL` | თქვენი Supabase project URL | დიახ, live მონაცემებისთვის |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase server-side service role key | დიახ, live მონაცემებისთვის |

თუ environment variables დროებით არ დაემატა, frontend მაინც ჩაიტვირთება fallback/empty state-ებით, მაგრამ live Supabase მონაცემები არ გამოჩნდება.

## Render/Railway ალტერნატივა

თუ Vercel არ გამოიყენება, აპლიკაცია შეიძლება გაიშვას ნებისმიერი Node.js runtime-ზე შემდეგი ბრძანებებით:

```bash
cd viewer
npm install
npm run build
npm run start
```

ჰოსტინგმა უნდა გამოიყენოს Node.js `>=22.0.0` და უნდა ჰქონდეს იგივე environment variables: `SUPABASE_URL` და `SUPABASE_SERVICE_ROLE_KEY`.

## უსაფრთხოების შენიშვნა

`SUPABASE_SERVICE_ROLE_KEY` არასდროს უნდა ჩაიწეროს კოდში ან GitHub-ში. ის უნდა დაემატოს მხოლოდ hosting provider-ის protected environment variables-ში. `.env.example` მხოლოდ სახელების ნიმუშია და რეალურ საიდუმლოებებს არ შეიცავს.

## შემოწმება deployment-ის შემდეგ

გაშვების შემდეგ გადაამოწმეთ შემდეგი route-ები:

| ენა | Route |
|---|---|
| ქართული | `/ka` |
| ქართული Dashboard | `/ka/dashboard` |
| ქართული Brain Lab | `/ka/brain` |
| ინგლისური | `/en` |

თუ `/ka/dashboard`, `/ka/hypotheses`, `/ka/therapies` ან `/ka/timeline` ცარიელ data state-ს აჩვენებს, ეს თითქმის ყოველთვის ნიშნავს, რომ Supabase environment variables ჯერ არ არის დამატებული production ჰოსტინგში.
