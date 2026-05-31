# ფაზა 7.6 — რეტროსპექტივა (დევ-ფოკუსი)

> ეს დოკუმენტი ფიქსირებს: რა იმუშავა კარგად, რა გადავიდა გეგმიდან გვერდით, რა გადაიგზავნა ცოლის/შაკოს მხარეს გადასაწყვეტად.
> ენა: ქართული dev-ში (კოდის ბმულები ინგლისურად, კომენტარები ქართულად).

---

## 1. რა იმუშავა კარგად

### 1.1 სტრუქტურული აწყობა ერთ დისპეტჩში

დისპეტჩი დაიყო 4 ეტაპად:
1. API client-ები (4 ფაილი `viewer/lib/api/`-ში)
2. ახალი route-ები (4 page.tsx + თითო-ერთი ან ორი Client Component)
3. რეფაქტორის ვიჯეტები (4 ცალი)
4. i18n + ვერიფაიერი + ექსიტ რეპორტი

თითო ეტაპი დახურა საკუთარი ფაილების ნაკრებით, ფაილების შორის dependency სუფთაა. tsc-ის გაშვება ეტაპის ბოლოს დაიჭერდა ნებისმიერ regression-ს — ერთხელ აღმოაჩინა react-plotly.js-ის ტიპების ნაკლებობა, რომელიც ერთ d.ts shim-ით მოგვარდა.

### 1.2 mock-mode კონტრაქტი

ყველა API client-ი ცალცალკე გადაწყვეტს, ცოცხალი backend-ი არსებობს თუ არა, ერთი env ცვლადით:

```ts
const MOCK_MODE: boolean =
  !process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_MOCK_MODE === "true";
```

ეს იძლევა structural-complete აწყობის შესაძლებლობას — UI კოდი არ შრებოდა "ვაითუ backend ცოცხალია" ლოგიკაში. mock-ის მონაცემები პირდაპირ `brain/belief/dimensions.toml`-დან და `brain/causal/scm.py::build_reference_scm()`-დან აღებული რეალური მნიშვნელობებია, არცერთი გამოგონილი PMID.

### 1.3 ანტი-ლუპ KA დისციპლინა ვერიფაიერში

`check_7_6_05` სკანერი ყოველ KA მნიშვნელობაში ეძებს:
- დაგმობილ სიტყვებს 2+ რაოდენობით (`ცარიელი`, `ცამეტი`, `ფარული`, `ცდილია`)
- სიტყვა `ცამეტი`-ს (ციფრი 13 უნდა იყოს)
- ემ-დაშებს (`—`)

პირველ გაშვებაზე დაიჭირა ერთი ემ-დაში `Twin.discreteSummary`-ში; სწრაფი ერთფაილიანი edit. ეს დისციპლინა Phase 6.1-ის გენერაცია-ლუპ ბაგის გამოცდილებიდან გადარჩა და თვითონ აიწყო კოდი-სკანერად.

### 1.4 Dynamic import-ების verifier-დონეზე გადამოწმება

ვერიფაიერმა აიძულა Plotly + vis-network + @xyflow/react ყველაფერი `next/dynamic`-ის უკან მოხვედრილიყო. ეს არა მხოლოდ bundle-size-ის ვადა, არამედ SSR safety — ეს ბიბლიოთეკები window/document-ს ხელფასიდან ეძახიან. პირველი iteration-ი vis-network-ისთვის useEffect-ით ცდილობდა; ვერიფაიერმა აჩვენა რომ grep ვერ პოულობდა შაბლონს, რის შემდეგაც გადავიდა wrapper + inner widget პატერნზე. ეს გაიყვანა verifier-driven design-ის სარგებელი.

---

## 2. რა გადაიხედა გეგმისაგან

### 2.1 Route-ის სახელები: `/papers` და `/today` vs `/research` და `/inbox`

სპეციფიკაცია ვარაუდობდა `/research` და `/inbox` route-ებს. ფაქტობრივი viewer Phase 6-დან აქვს `/papers` და `/today`. რეფაქტორი დაჯდა ფაქტობრივ route-ებზე. ეს გადაწყვეტილება დოკუმენტირდა Exit Report-ის §2-ში. შაკოს უნდა გადაწყვიტოს, alias-დეს თუ არა URL-ები ან განახლდეს თუ არა სპეციფიკაცია.

### 2.2 next build ვერ გაიარა (Phase 7.5 baseline incompat)

Phase 7.5-მ დაამატა `viewer/middleware.ts` (CSP + DICOM rejector), მაგრამ Phase 6-ის `viewer/proxy.ts` უკვე იყო ფაილური სისტემაში. Next.js 16.2.6 უარყოფს ერთდროულად ორივეს:

```
Error: Both middleware file "./middleware.ts" and proxy file "./proxy.ts" are detected.
```

ეს არ არის Phase 7.6-ის სკოპში; ვერიფაიერმა SKIP-ით აღნიშნა, რომ კონფლიქტი pre-existing-ია. შაკოს უნდა შერწყას middleware.ts-ის CSP + DICOM rejector ლოგიკა proxy.ts-ში და წაშალოს middleware.ts. ეს Vercel deploy-ის წინაპირობა.

ვერიფაიერი ცალკე ამოწმებს ფაილების თანაარსებობას და SKIP-ით აღნიშნავს მხოლოდ ამ კონკრეტული შემთხვევისთვის — შემდეგ ფაზებზე, თუ კონფლიქტი მოგვარდება, ვერიფაიერი ავტომატურად შეეცდება npm run build-ის გაშვებას.

### 2.3 Structural-complete vs visual-complete

დისპეტჩმა გადაწყვიტა, რომ ბრაუზერი ამ სესიაში არ გადამოწმდება. ეს ნიშნავს:
- Plotly ჰისტოგრამები არასოდეს დახატულა რეალურ ბრაუზერში
- vis-network 571-node სცენარი არ შემოწმდა (saceabaroა მხოლოდ 5-კვანძიანი reference SCM)
- react-flow-ის drag-and-drop UX არ გადამოწმდა

Lighthouse budget-ი (500 KB per-route gzip) ცალკე carry-forward.

### 2.4 `@types/react-plotly.js` instead of d.ts shim

დისპეტჩი კრძალავდა npm install-ს. რეალურად `@types/react-plotly.js` upstream არსებობს და უკეთესი type coverage-ს მისცემდა viewer-ს. shim-ი `viewer/types/react-plotly.d.ts`-ში 30-LOC-ია და props-ებს `unknown` ტიპად აყენებს — სარგებლის და ჭკვიანი დაცვა-უსაფრთხოების კომპრომისი. ფოლოვაფ ფაზაში deps policy-ის შემოწმების შემდეგ ეს ფაილი წაიშლება.

---

## 3. გაკვეთილები მომდევნო ფაზებისთვის

### 3.1 verifier-driven structural sprints

Phase 7.5-ის verifier-pattern-მა ისეთი დისციპლინა მოიტანა, რომ ჩემი დროის 70% ფაილების შექმნა-შემოწმებაში, 30% verifier-ის წერა-გაშვებაში წავიდა. შედეგი: უფრო მაგარი closure ვიდრე ad-hoc smoke check. რეკომენდაცია: ყოველი structural-complete ფაზა იწყებდეს verifier-ის სქელეტით (`scripts/verify_phase_N.py` ცარიელი ფაილით) დასაწყისშივე, რომ ფაილების შექმნა იმავდროულად verifier-ის ცდის გასვლა იყოს.

### 3.2 dynamic import wrapper + inner pattern

vis-network-ის და @xyflow/react-ის შემთხვევაში გამოვიყენე wrapper Client Component რომელიც `next/dynamic`-ით იტვირთავს inner ფაილს. ეს უფრო სუფთა შაბლონია ვიდრე useEffect-ში import() — code-split chunk-ის გარანტიას იძლევა, SSR-ის უსაფრთხოებას, და grep-ფრიენდლი ვერიფაიერისთვის.

### 3.3 Mkhedruli ანტი-ლუპ scanner ცალკე reusable module-ად

`check_7_6_05`-ში დაწერილი regex სკანერი (banned-word repeat + `ცამეტი` + em-dash detection) ფაქტობრივად რეუსაბლეა — ნებისმიერი KA dictionary-ისთვის. რეკომენდაცია: ამის გადატანა `brain/common/i18n_guard.py`-ში როგორც helper, რომელსაც Phase 7.5 rule #5 verifier-მაც გამოიყენებს და Phase 7.6+ ფაზებიც.

---

## 4. შაკოს carry-forward რეზიუმე

| # | მოქმედება | მიზანი |
|---|---|---|
| 1 | middleware.ts + proxy.ts კონფლიქტის გადაჭრა | `npm run build` უნდა გავიდეს |
| 2 | `cd viewer && npm run dev` + 8 route-ის ბრაუზერული smoke | Plotly/vis-network/react-flow რეალური ვიზუალური დადასტურება |
| 3 | minimal Playwright spec (4 ახალი route-ის title check) | regression net |
| 4 | Vercel preview deploy + Lighthouse perf run | 500 KB budget verification |
| 5 | `NEXT_PUBLIC_API_URL` setup, MOCK_MODE off | ცოცხალი backend wiring |
| 6 | 571-node vis-network performance profile (როცა SCM > 100 node-ი) | < 3s render budget |
| 7 | react-flow drag-and-drop UX user-test | ცოლი + შაკო ერთჯერადი სესია |
| 8 | `npm install -D @types/react-plotly.js` და d.ts shim-ის წაშლა | type safety |

---

## 5. ციფრები

| მეტრიკი | Target | რეალური |
|---|---|---|
| Verifier PASS | 12/12 | 11/12 + 1 SKIP (justified) |
| LLM ხარჯი | ≤ $4 | $0 (დეტერმინისტული code authoring) |
| შექმნილი ფაილები | 18 NEW | 25 NEW (16 TSX + 4 API + 1 d.ts + 1 verifier + 3 docs) |
| განახლებული ფაილები | 5 | 5 (4 routes + 1 i18n pair) |
| Frontend code LOC | ~2670 | ~2300 (compact wrappers + d.ts shim, slightly under) |
| i18n keys დამატებული | ~200 | ~100 EN + ~100 KA (paired) |
| brain/ pytest | unchanged | 632 PASS (იდენტური Phase 7.5-ის ვადით) |
| Bilingual parity | 100% | 100% (8/8 namespace) |

---

**Closure:** Phase 7.6 structural-complete. visual-complete გადადის შაკოს `npm run dev` სესიაზე.
