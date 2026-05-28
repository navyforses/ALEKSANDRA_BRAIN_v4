"use client";

import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Brain,
  CheckCircle2,
  Database,
  FileText,
  FlaskConical,
  Layers3,
  Library,
  LifeBuoy,
  MessageSquareText,
  Network,
  Scale,
  Search,
  ShieldCheck,
  Stethoscope,
  UsersRound,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import type { Locale } from "@/lib/seo";

type PageKey =
  | "today"
  | "dashboard"
  | "brain"
  | "hypotheses"
  | "therapies"
  | "timeline"
  | "evidence-map"
  | "cohorts"
  | "data-integrations"
  | "papers"
  | "alerts"
  | "resources"
  | "how-it-works"
  | "support"
  | "settings"
  | "audit"
  | "knowledge";

type Grade = "research" | "promising" | "established";
type Tone = "sky" | "emerald" | "amber" | "violet" | "slate";

type Metric = { label: string; value: string; detail: string };
type TopicModel = {
  eyebrow: string;
  title: string;
  summary: string;
  shortAnswer: string;
  icon: LucideIcon;
  grade: Grade;
  gradeLabel: string;
  confidenceLabel: string;
  metrics: Metric[];
  evidence: string[];
  uncertainty: string[];
  risks: string[];
  doctorQuestions: string[];
  briefItems: string[];
  related: string[];
};

const gradeStyles: Record<Grade, string> = {
  research: "border-amber-200/20 bg-amber-200/[0.055] text-amber-50",
  promising: "border-sky-300/20 bg-sky-300/[0.065] text-sky-50",
  established: "border-emerald-300/20 bg-emerald-300/[0.065] text-emerald-50",
};

const toneStyles: Record<Tone, { border: string; bg: string; text: string; icon: string }> = {
  sky: { border: "border-sky-300/18", bg: "bg-sky-300/[0.055]", text: "text-sky-100", icon: "text-sky-200" },
  emerald: { border: "border-emerald-300/18", bg: "bg-emerald-300/[0.055]", text: "text-emerald-100", icon: "text-emerald-200" },
  amber: { border: "border-amber-200/18", bg: "bg-amber-200/[0.055]", text: "text-amber-100", icon: "text-amber-100" },
  violet: { border: "border-violet-300/18", bg: "bg-violet-300/[0.055]", text: "text-violet-100", icon: "text-violet-200" },
  slate: { border: "border-white/10", bg: "bg-white/[0.035]", text: "text-slate-200", icon: "text-slate-300" },
};

const kaTopics: Record<PageKey, TopicModel> = {
  today: {
    eyebrow: "დღის მოკლე სურათი",
    title: "რა ვიცით, რა არის გაურკვეველი და რა ვკითხოთ ექიმს.",
    summary: "დღევანდელი ხედვა აერთიანებს ახალ წყაროებს, უსაფრთხოების საზღვრებს და ვიზიტისთვის გამოსაყენებელ კითხვებს.",
    shortAnswer: "ამ ეტაპზე ყველაზე სასარგებლოა არა ერთი პასუხის ძებნა, არამედ მტკიცებულების ხარისხის, გაურკვევლობისა და კლინიკური კონტექსტის ერთად დანახვა.",
    icon: Activity,
    grade: "promising",
    gradeLabel: "პერსპექტიული კვლევა",
    confidenceLabel: "საჭიროა ექიმთან გადამოწმება",
    metrics: [
      { label: "ახალი წყარო", value: "6", detail: "ბოლო განახლებაში" },
      { label: "კითხვა", value: "9", detail: "ვიზიტისთვის მზად" },
      { label: "რისკის ჩანაწერი", value: "4", detail: "საჭიროებს ყურადღებას" },
      { label: "ბრიფი", value: "1", detail: "შემაჯამებელი ვერსია" },
    ],
    evidence: ["წყაროები დაჯგუფებულია თემებად: მტკიცებულება, ჰიპოთეზა და პრაქტიკული კითხვა.", "თითოეულ ჩანაწერს ახლავს მოკლე ხარისხის ნიშანი და კვლევითი საზღვარი.", "ოჯახისთვის ხილული ტექსტი გამარტივებულია, მაგრამ წყაროს კონტექსტი არ იკარგება."],
    uncertainty: ["კვლევების ნაწილი მცირე ჯგუფებზეა დაფუძნებული.", "ყველა მიგნება არ ეხება პირდაპირ ახალშობილთა HIE-ს.", "ერთიანი კლინიკური რეკომენდაცია მხოლოდ ამ მონაცემებით არ დგება."],
    risks: ["კვლევითი იდეა არ უნდა გადაიქცეს თვითნებურ ჩარევად.", "ნებისმიერი თერაპიული ცვლილება უნდა შეფასდეს მკურნალ გუნდთან."],
    doctorQuestions: ["ამ მიგნებიდან რომელი ნაწილი ეხება ჩვენს კონკრეტულ შემთხვევას?", "რა მონაცემი გვაკლია უსაფრთხო დასკვნისთვის?", "რა უნდა დავაკვირდეთ მომდევნო ვიზიტამდე?"],
    briefItems: ["მოკლე პასუხი", "ძირითადი გაურკვევლობა", "სამი კითხვა ექიმთან"],
    related: ["მტკიცებულება", "რისკი", "ბრიფი"],
  },
  dashboard: {
    eyebrow: "კვლევის პანელი",
    title: "მონაცემი უნდა გადაიქცეს მშვიდ, გასაგებ სამუშაო გზად.",
    summary: "სრული პანელი აჩვენებს წყაროებს, ჰიპოთეზებს, რისკებს და ექიმთან განსახილველ კითხვებს ერთ მოდელში.",
    shortAnswer: "პანელის მთავარი ლოგიკაა: ჯერ ვნახოთ მტკიცებულება, შემდეგ მისი შეზღუდვა, ბოლოს კი უსაფრთხო კითხვა ექიმთან.",
    icon: Layers3,
    grade: "promising",
    gradeLabel: "სამუშაო მოდელი",
    confidenceLabel: "მტკიცებულება ნაწილობრივ სტრუქტურირებულია",
    metrics: [
      { label: "წყარო", value: "12.8k", detail: "კურაციის ნაკადში" },
      { label: "claim", value: "742", detail: "გამოყოფილი მტკიცება" },
      { label: "ჰიპოთეზა", value: "173", detail: "შემოწმების რიგში" },
      { label: "კითხვა", value: "96", detail: "ექიმთან განხილვისთვის" },
    ],
    evidence: ["მონაცემები იყოფა წყაროდ, claim-ად, ჰიპოთეზად და რისკის ჩანაწერად.", "ყველა card მიბმულია ერთიან flow-სთან და არა მხოლოდ ვიზუალურ სტატისტიკასთან.", "ბრიფის ელემენტები მზადდება იმავე მოდელიდან, რომლითაც გვერდები იქმნება."],
    uncertainty: ["ჯერ არ არსებობს სრულად ავტომატური grading pipeline.", "ზოგი წყარო საჭიროებს ხელით გადამოწმებას.", "კლინიკური შესაბამისობა ყოველთვის დამოკიდებულია პაციენტის კონტექსტზე."],
    risks: ["მაღალი რიცხვები არ ნიშნავს მაღალ სანდოობას.", "dashboard არ უნდა გამოიყურებოდეს როგორც დიაგნოსტიკური ინსტრუმენტი."],
    doctorQuestions: ["რომელი მტკიცებულება არის ნამდვილად შესაბამისი ასაკისთვის და დიაგნოზისთვის?", "რომელი ჰიპოთეზა ღირს განხილვად და რომელი მხოლოდ კვლევითია?", "რა უნდა შევიტანოთ ექიმთან წასაღებ მოკლე ბრიფში?"],
    briefItems: ["წყაროების ხარისხი", "მთავარი რისკები", "საუბრის მიზანი"],
    related: ["წყარო", "claim", "ჰიპოთეზა", "კითხვა"],
  },
  brain: {
    eyebrow: "ტვინის რუკა",
    title: "ტვინის ხედვა არის საუბრის რუკა და არა დიაგნოზი.",
    summary: "რუკა აჩვენებს კავშირებს კვლევით თემებს, ფუნქციურ დაკვირვებებსა და სპეციალისტთან დასასმელ კითხვებს შორის.",
    shortAnswer: "ტვინის მოდელი ეხმარება თემების ორგანიზებას, მაგრამ MRI-ს, ნევროლოგის შეფასებას ან მკურნალობის გეგმას არ ცვლის.",
    icon: Brain,
    grade: "research",
    gradeLabel: "კვლევითი ხედვა",
    confidenceLabel: "ვიზუალური კონტექსტი, არა კლინიკური პასუხი",
    metrics: [
      { label: "ფენა", value: "7", detail: "სტრუქტურა და ფუნქცია" },
      { label: "კავშირი", value: "48", detail: "კვლევითი ბმა" },
      { label: "შენიშვნა", value: "16", detail: "კლინიკური საზღვარი" },
      { label: "კითხვა", value: "12", detail: "სპეციალისტისთვის" },
    ],
    evidence: ["სხვადასხვა წყარო აღწერს HIE-ის შემდგომ სტრუქტურულ და ფუნქციურ ცვლილებებს.", "დროითი დაკვირვება ხშირად მნიშვნელოვანია ერთჯერად მონაცემზე მეტად.", "რუკა აერთიანებს MRI, განვითარებისა და კვლევითი თემების ენას."],
    uncertainty: ["ერთი ვიზუალური ფენა ვერ ხსნის ბავშვის მთლიან მდგომარეობას.", "კვლევითი კავშირი არ ნიშნავს მიზეზობრივ კავშირს.", "ფუნქციური პროგნოზი საჭიროებს სპეციალისტის შეფასებას."],
    risks: ["რუკის ზედმეტად პირდაპირი ინტერპრეტაცია შეიძლება შეცდომაში შემყვანი იყოს.", "არ უნდა გაკეთდეს დასკვნა მხოლოდ ვიზუალური მსგავსების საფუძველზე."],
    doctorQuestions: ["რომელი ფენა არის მნიშვნელოვანი ჩვენი შემთხვევისთვის?", "რა ტიპის დაკვირვება ან შეფასება არის შემდეგი ლოგიკური ნაბიჯი?", "რომელი ცვლილება შეიძლება იყოს დროითი და არა მუდმივი?"],
    briefItems: ["კონტექსტის რუკა", "გაურკვეველი კავშირები", "სპეციალისტის კითხვები"],
    related: ["MRI", "განვითარება", "კავშირები"],
  },
  hypotheses: {
    eyebrow: "ჰიპოთეზები",
    title: "ჰიპოთეზა არის შესამოწმებელი იდეა და არა დასკვნა.",
    summary: "გვერდი ალაგებს იდეებს მტკიცებულების ხარისხით, გაურკვევლობით და ექიმთან გადასამოწმებელი კითხვებით.",
    shortAnswer: "ჰიპოთეზა სასარგებლოა მაშინ, როცა ჩანს მისი წყარო, საწინააღმდეგო სიგნალი, რისკი და კლინიკური საზღვარი.",
    icon: FlaskConical,
    grade: "promising",
    gradeLabel: "პერსპექტიული, მაგრამ არა საბოლოო",
    confidenceLabel: "საჭიროა დამატებითი validation",
    metrics: [
      { label: "ძლიერი", value: "28%", detail: "უკეთესი მხარდაჭერა" },
      { label: "საშუალო", value: "41%", detail: "დამატებით შესამოწმებელი" },
      { label: "შეზღუდული", value: "18%", detail: "კვლევის დონე" },
      { label: "კითხვა", value: "34", detail: "ვიზიტისთვის" },
    ],
    evidence: ["ჰიპოთეზები ეყრდნობა ცალკე claim-ებს და არა მხოლოდ სტატიის სათაურს.", "ხარისხის ნიშანი აერთიანებს წყაროს ტიპს, პოპულაციის შესაბამისობას და თანმიმდევრულობას.", "სისტემა აჩვენებს როგორც მხარდაჭერას, ისე შეზღუდვას."],
    uncertainty: ["ზოგი მექანიზმი ნაჩვენებია მხოლოდ preclinical დონეზე.", "პოპულაციის შესაბამისობა ხშირად არასრულია.", "ჰიპოთეზებს შორის კონკურენტული ახსნებიც არსებობს."],
    risks: ["პერსპექტიული მექანიზმი არ ნიშნავს უსაფრთხო ჩარევას.", "ჰიპოთეზის language არ უნდა გახდეს მკურნალობის რეკომენდაცია."],
    doctorQuestions: ["ეს ჰიპოთეზა ეხება ბავშვის კონკრეტულ კლინიკურ სურათს?", "რომელი მტკიცებულება არის ყველაზე ძლიერი და რომელი ყველაზე სუსტი?", "რა ნიშნულით გავიგებთ, რომ იდეა აღარ არის შესაბამისი?"],
    briefItems: ["ჰიპოთეზის მოკლე ახსნა", "მხარდამჭერი claim-ები", "საწინააღმდეგო ან გაურკვეველი მხარე"],
    related: ["claim", "validation", "საწინააღმდეგო სიგნალი"],
  },
  therapies: {
    eyebrow: "თერაპიის კანდიდატები",
    title: "თერაპია ჩანს მხოლოდ კვლევითი საზღვრით და ექიმთან განხილვის ენით.",
    summary: "გვერდი არ იძლევა მკურნალობის ინსტრუქციას; ის აჩვენებს, რა არის კვლევის დონეზე საინტერესო და რა რისკი ახლავს ინტერპრეტაციას.",
    shortAnswer: "თერაპიის კანდიდატი უნდა შეფასდეს მტკიცებულებით, უსაფრთხოებით, ასაკობრივი შესაბამისობით და მკურნალ გუნდთან განხილვით.",
    icon: Stethoscope,
    grade: "research",
    gradeLabel: "მხოლოდ კვლევითი განხილვა",
    confidenceLabel: "არ არის დანიშნულება",
    metrics: [
      { label: "კანდიდატი", value: "28", detail: "საზღვრით აღწერილი" },
      { label: "trial", value: "14", detail: "აქტიური/დაკვირვების" },
      { label: "რისკი", value: "22", detail: "განსაზღვრული ჩანაწერი" },
      { label: "კითხვა", value: "31", detail: "ექიმთან" },
    ],
    evidence: ["თერაპიის კანდიდატები უკავშირდება ჰიპოთეზებს და კონკრეტულ მექანიზმებს.", "კლინიკური სტატუსი ცალკე ჩანს: research-only, trial-stage ან established care.", "უსაფრთხოების ჩანაწერი ყოველთვის თან ახლავს თერაპიის აღწერას."],
    uncertainty: ["ზოგი იდეა არ არის შესწავლილი HIE-ის პედიატრიულ კონტექსტში.", "დოზა, დრო და safety ხშირად გაურკვეველია.", "გამოქვეყნებული შედეგები შეიძლება არ იყოს საკმარისი პრაქტიკული ცვლილებისთვის."],
    risks: ["თერაპიის სახელის ნახვა არ ნიშნავს, რომ ის უნდა გამოიყენოს ოჯახმა დამოუკიდებლად.", "off-label ან experimental იდეა ექიმის გარეშე არ განიხილება."],
    doctorQuestions: ["ეს ჩარევა საერთოდ არის განხილვადი ჩვენს კონტექსტში?", "რა არის ცნობილი უსაფრთხოებაზე და რა არის უცნობი?", "არსებობს guideline ან trial, რომელიც უფრო სანდო მიმართულებას აძლევს?"],
    briefItems: ["თერაპიის სტატუსი", "უსაფრთხოების საზღვარი", "ექიმთან დასასმელი კითხვა"],
    related: ["უსაფრთხოება", "trial", "clinical boundary"],
  },
  timeline: {
    eyebrow: "დროითი ხაზი",
    title: "დრო ეხმარება კვლევისა და დაკვირვების ერთმანეთთან დაკავშირებას.",
    summary: "ქრონოლოგია აჩვენებს, როდის გაჩნდა მიგნება, როდის შეიცვალა გაგება და რა კითხვაა შემდეგი.",
    shortAnswer: "HIE-ის კვლევაში დროითი ფანჯარა მნიშვნელოვანია, მაგრამ კონკრეტული ბავშვის შეფასება ყოველთვის ინდივიდუალურია.",
    icon: Activity,
    grade: "research",
    gradeLabel: "კონტექსტური მტკიცებულება",
    confidenceLabel: "დროითი ინტერპრეტაცია სიფრთხილეს მოითხოვს",
    metrics: [
      { label: "ეტაპი", value: "7", detail: "კვლევის ქრონოლოგია" },
      { label: "განახლება", value: "2025+", detail: "მიმდინარე სწავლა" },
      { label: "კითხვა", value: "8", detail: "დროის ფანჯარაზე" },
      { label: "შეზღუდვა", value: "5", detail: "ინტერპრეტაციის" },
    ],
    evidence: ["დროითი მონაცემი ხშირად ცვლის კვლევის წაკითხვას.", "ქრონოლოგია ეხმარება ძველი და ახალი წყაროების გამიჯვნას.", "დაკვირვების პერიოდი შეიძლება იყოს ისეთივე მნიშვნელოვანი, როგორც ერთი მიგნება."],
    uncertainty: ["ყველა კვლევა ერთნაირად არ აღწერს ასაკსა და დროით ფანჯარას.", "შედარება რთულია სხვადასხვა outcome-ს შორის.", "დროითი კავშირი ყოველთვის მიზეზობრივ კავშირს არ ნიშნავს."],
    risks: ["ძველი წყაროს პირდაპირი გამოყენება ახალი კონტექსტის გარეშე სახიფათოა.", "დროის ფანჯარა არ უნდა გახდეს თვითნებური გადაწყვეტილების საფუძველი."],
    doctorQuestions: ["რომელი დროითი ფანჯარაა მნიშვნელოვანი ჩვენს შემთხვევაში?", "რა უნდა შევადაროთ წინა ვიზიტის მონაცემებს?", "რომელი ცვლილება ითვლება პროგრესად ან სიგნალად?"],
    briefItems: ["დროითი ნიშნული", "რა შეიცვალა", "შემდეგი დაკვირვება"],
    related: ["ქრონოლოგია", "განახლება", "დაკვირვება"],
  },
  "evidence-map": {
    eyebrow: "მტკიცებულების რუკა",
    title: "ყველა წყარო უნდა პასუხობდეს კითხვას: რას ამტკიცებს და რამდენად გვადგება?",
    summary: "რუკა ყოფს წყაროებს claims-ად, ხარისხის ნიშნად, პოპულაციის შესაბამისობად და კლინიკურ საზღვრად.",
    shortAnswer: "მტკიცებულება ღირებულია მაშინ, როცა ჩანს წყარო, study type, ვის ეხება და რა შეზღუდვა აქვს.",
    icon: Network,
    grade: "established",
    gradeLabel: "სტრუქტურული საფუძველი",
    confidenceLabel: "წყაროების მოდელი მკაფიოა",
    metrics: [
      { label: "წყარო", value: "12.8k", detail: "დამუშავებული ჩანაწერი" },
      { label: "claim", value: "742", detail: "გამოყოფილი მტკიცება" },
      { label: "grade", value: "5", detail: "ხარისხის განზომილება" },
      { label: "რისკი", value: "88", detail: "შეზღუდვის ჩანაწერი" },
    ],
    evidence: ["წყარო და claim ერთმანეთისგან გაყოფილია.", "ხარისხის შეფასება აჩვენებს study type-ს, შესაბამისობას და თანმიმდევრულობას.", "მომხმარებელი ხედავს არა მხოლოდ დასკვნას, არამედ მის საზღვარსაც."],
    uncertainty: ["ავტომატურად ამოღებული claim შეიძლება საჭიროებდეს human review-ს.", "ყველა წყარო ერთნაირი ხარისხის metadata-ს არ იძლევა.", "ზოგი დასკვნა დამოკიდებულია კონტექსტზე."],
    risks: ["ცალკეული სტატია არ უნდა წარმოვადგინოთ როგორც საბოლოო consensus.", "მტკიცებულების რაოდენობა არ უდრის მტკიცებულების ხარისხს."],
    doctorQuestions: ["რომელი წყარო არის ყველაზე ახლოს ჩვენს კლინიკურ კითხვასთან?", "ეს კვლევა ბავშვებზეა, ახალშობილებზეა თუ სხვა პოპულაციაზე?", "რა შეზღუდვა აქვს ამ მტკიცებას?"],
    briefItems: ["წყაროს ტიპი", "claim", "შეზღუდვა"],
    related: ["source", "claim", "grade", "risk"],
  },
  cohorts: {
    eyebrow: "კოჰორტები",
    title: "პოპულაცია განსაზღვრავს, რამდენად გვადგება კვლევა.",
    summary: "კოჰორტების გვერდი ეხმარება მომხმარებელს დაინახოს, ვისზეა კვლევა ჩატარებული და რამდენად ახლოსაა HIE-ის პედიატრიულ კონტექსტთან.",
    shortAnswer: "კვლევა შეიძლება ძლიერი იყოს, მაგრამ არ იყოს შესაბამისი კონკრეტული ასაკის, დიაგნოზის ან დროითი ფანჯრისთვის.",
    icon: UsersRound,
    grade: "research",
    gradeLabel: "შესაბამისობის შეფასება",
    confidenceLabel: "კონტექსტი გადამწყვეტია",
    metrics: [
      { label: "კოჰორტა", value: "14", detail: "კვლევითი ჯგუფი" },
      { label: "ასაკი", value: "4", detail: "ძირითადი ფენა" },
      { label: "outcome", value: "19", detail: "შედარების ველი" },
      { label: "gap", value: "7", detail: "მონაცემის დანაკლისი" },
    ],
    evidence: ["პოპულაციის metadata ეხმარება კვლევის პრაქტიკული მნიშვნელობის შეფასებას.", "ასაკი, HIE severity და follow-up პერიოდი ცალკე უნდა ჩანდეს.", "შედარება მხოლოდ მსგავს კონტექსტებს შორის არის გონივრული."],
    uncertainty: ["სხვადასხვა კვლევა განსხვავებულ inclusion criteria-ს იყენებს.", "ზოგი cohort მცირეა ან ერთცენტრიანია.", "outcome measures ხშირად არ ემთხვევა ერთმანეთს."],
    risks: ["არასწორი population match შეიძლება გადაჭარბებულ იმედს ან შიშს ქმნიდეს.", "სხვა ასაკობრივი ჯგუფის მიგნება პირდაპირ არ გადმოდის ბავშვზე."],
    doctorQuestions: ["ეს კვლევის ჯგუფი რამდენად ჰგავს ჩვენს კლინიკურ კონტექსტს?", "რომელი outcome არის რეალურად მნიშვნელოვანი ბავშვისთვის?", "არის მონაცემის ისეთი დანაკლისი, რაც დასკვნას ზღუდავს?"],
    briefItems: ["პოპულაციის მსგავსება", "ასაკი და დიაგნოზი", "შეზღუდვა"],
    related: ["population", "outcome", "match"],
  },
  "data-integrations": {
    eyebrow: "მონაცემები",
    title: "ინტეგრაცია სანდოა მაშინ, როცა provenance და საზღვარი ჩანს.",
    summary: "მონაცემთა გვერდი აღწერს, საიდან მოდის ინფორმაცია, რა სტატუსი აქვს და რა ეტაპზე სჭირდება გადამოწმება.",
    shortAnswer: "საიტმა არ უნდა დამალოს წყარო, დრო, დამუშავების გზა და human review-ის სტატუსი.",
    icon: Database,
    grade: "promising",
    gradeLabel: "ტექნიკური მოდელი",
    confidenceLabel: "საჭიროა governance",
    metrics: [
      { label: "არხი", value: "36", detail: "მონაცემის წყარო" },
      { label: "review", value: "3", detail: "შემოწმების დონე" },
      { label: "audit", value: "219", detail: "კვალი" },
      { label: "alert", value: "9", detail: "ცვლილების სიგნალი" },
    ],
    evidence: ["მონაცემს უნდა ახლდეს provenance: წყარო, დრო, დამუშავება.", "review სტატუსი ცალკე ჩანს და არ ერევა კლინიკურ დასკვნაში.", "audit trail ამცირებს არასწორი ინტერპრეტაციის რისკს."],
    uncertainty: ["ზოგი ინტეგრაცია შეიძლება არასრული metadata-თი მოდიოდეს.", "სინქრონიზაციის შეცდომა უნდა გამოჩნდეს მომხმარებლისთვის გასაგებად.", "ავტომატური parsing-ს სჭირდება კონტროლი."],
    risks: ["ტექნიკური availability არ ნიშნავს კლინიკურ სანდოობას.", "არასრული მონაცემი არ უნდა გამოჩნდეს როგორც დამტკიცებული მტკიცებულება."],
    doctorQuestions: ["ეს მონაცემი საიდან მოდის და როდის განახლდა?", "გადამოწმებულია თუ მხოლოდ ავტომატურად არის ამოღებული?", "რომელი ნაწილი უნდა განვიხილოთ სპეციალისტთან?"],
    briefItems: ["წყაროს provenance", "review სტატუსი", "სანდოობის საზღვარი"],
    related: ["provenance", "review", "audit"],
  },
  papers: {
    eyebrow: "პუბლიკაციები",
    title: "სტატია მნიშვნელოვანია მხოლოდ მაშინ, როცა მისი claim გასაგებია.",
    summary: "პუბლიკაციები წარმოდგენილია არა როგორც გრძელი სია, არამედ როგორც მოკლე მტკიცებები, grading და შეზღუდვები.",
    shortAnswer: "კარგი literature view გვაჩვენებს: რა თქვა წყარომ, ვისზე თქვა, რამდენად ძლიერია და რა არ ვიცით.",
    icon: BookOpen,
    grade: "established",
    gradeLabel: "წყაროზე დაფუძნებული",
    confidenceLabel: "საჭიროა claim-level კითხვა",
    metrics: [
      { label: "სტატია", value: "8.1k", detail: "ბიბლიოგრაფია" },
      { label: "review", value: "312", detail: "შეჯამებული წყარო" },
      { label: "guideline", value: "18", detail: "კლინიკური კონტექსტი" },
      { label: "claim", value: "742", detail: "გამოყოფილი" },
    ],
    evidence: ["ბიბლიოგრაფიული ჩანაწერი განცალკევებულია შინაარსობრივი claim-ისგან.", "guideline და randomized მონაცემი უფრო მკაფიოდ გამოიყოფა.", "სუსტი და ძლიერი წყაროები არ ჩანს ერთნაირი წონით."],
    uncertainty: ["abstract ყოველთვის საკმარისი არ არის დასკვნისთვის.", "publication bias შეიძლება გავლენას ახდენდეს ხედვაზე.", "ძველი წყაროები საჭიროებს თანამედროვე კონტექსტთან შედარებას."],
    risks: ["სტატიის სათაურის საფუძველზე დასკვნა სახიფათოა.", "ერთი წყაროს language არ უნდა გახდეს ოჯახის გადაწყვეტილების საფუძველი."],
    doctorQuestions: ["ეს წყარო guideline-ის დონეზეა თუ მხოლოდ კვლევითი observation?", "რა population აქვს კვლევას?", "ამ სტატიიდან რომელი claim არის პრაქტიკულად მნიშვნელოვანი?"],
    briefItems: ["სტატიის ტიპი", "მთავარი claim", "შეზღუდვა"],
    related: ["bibliography", "claim", "guideline"],
  },
  alerts: {
    eyebrow: "სიგნალები",
    title: "სიგნალი არის მიზეზი შესამოწმებლად და არა მიზეზი შესაშფოთებლად.",
    summary: "alert-ები აჩვენებს, რა შეიცვალა წყაროებში, ჰიპოთეზებში ან რისკის ჩანაწერებში.",
    shortAnswer: "კარგი სიგნალი არის მოკლე, წყაროზე მიბმული და ახსნილი: რა შეიცვალა და რა უნდა ვკითხოთ შემდეგ.",
    icon: AlertTriangle,
    grade: "research",
    gradeLabel: "საწყისი სიგნალი",
    confidenceLabel: "საჭიროა გადამოწმება",
    metrics: [
      { label: "სიგნალი", value: "9", detail: "ბოლო ცვლილება" },
      { label: "წყარო", value: "6", detail: "ახალი ჩანაწერი" },
      { label: "რისკი", value: "3", detail: "შეცვლილი საზღვარი" },
      { label: "კითხვა", value: "5", detail: "შესამოწმებელი" },
    ],
    evidence: ["სიგნალები იქმნება წყაროს, claim-ის ან risk note-ის ცვლილებაზე.", "თითოეული alert აღწერს, რა არის ახალი და რა არ შეცვლილა.", "მომხმარებელი ხედავს action-ს: წაკითხვა, გადამოწმება ან ბრიფში დამატება."],
    uncertainty: ["ახალი მონაცემი შეიძლება იყოს წინასწარი ან არასრული.", "ცვლილება შეიძლება ტექნიკური metadata-ს განახლება იყოს და არა კლინიკური სიახლე.", "ზოგი alert საჭიროებს human review-ს."],
    risks: ["სიგნალის language არ უნდა იყოს საგანგაშო.", "ახალი კვლევა არ ნიშნავს მკურნალობის ცვლილებას."],
    doctorQuestions: ["ეს ახალი წყარო ცვლის ჩვენს არსებულ კითხვებს?", "არის ეს კლინიკურად მნიშვნელოვანი თუ მხოლოდ კვლევითი?", "უნდა დავამატოთ ეს ბრიფში მომდევნო ვიზიტისთვის?"],
    briefItems: ["რა შეიცვალა", "რატომ არის მნიშვნელოვანი", "შემდეგი კითხვა"],
    related: ["change", "review", "brief"],
  },
  resources: {
    eyebrow: "ექიმთან წასაღები ბრიფი",
    title: "ბრიფი უნდა იყოს მოკლე, უსაფრთხო და გამოყენებადი ვიზიტზე.",
    summary: "რესურსების გვერდი აგროვებს მთავარ მტკიცებულებას, გაურკვევლობას და ექიმთან დასასმელ კითხვებს ერთ გვერდზე.",
    shortAnswer: "კარგი ბრიფი არ ითხოვს მკურნალობას; ის ეხმარება ოჯახს უკეთ დასვას კითხვა და ექიმს სწრაფად დაინახოს კონტექსტი.",
    icon: FileText,
    grade: "established",
    gradeLabel: "უსაფრთხო კომუნიკაცია",
    confidenceLabel: "არა სამედიცინო ინსტრუქცია",
    metrics: [
      { label: "სექცია", value: "3", detail: "მტკიცებულება, რისკი, კითხვა" },
      { label: "კითხვა", value: "12", detail: "მზად ვიზიტისთვის" },
      { label: "სიგრძე", value: "2 წთ", detail: "წასაკითხად" },
      { label: "საზღვარი", value: "1", detail: "research-only" },
    ],
    evidence: ["ბრიფი აგებულია იმავე სტრუქტურით, როგორც topic pages.", "ყოველ claim-ს ახლავს გაურკვევლობა და clinical boundary.", "ტექსტი მოკლეა, რათა ვიზიტზე რეალურად წაიკითხონ."],
    uncertainty: ["ბრიფი არ მოიცავს ყველა სამედიცინო დეტალს.", "ექიმმა შეიძლება სხვა პრიორიტეტი ჩათვალოს მნიშვნელოვანი.", "ოჯახის კონტექსტი უნდა დაემატოს სიფრთხილით."],
    risks: ["ბრიფი არ უნდა გახდეს ექიმზე ზეწოლის ინსტრუმენტი.", "არ უნდა შეიცავდეს დოზას, დანიშნულებას ან თვითნებურ რეკომენდაციას."],
    doctorQuestions: ["ამ სამი კითხვიდან რომელი არის ყველაზე მნიშვნელოვანი დღეს?", "რა ინფორმაცია უნდა მოგაწოდოთ, რომ უკეთ შეაფასოთ სიტუაცია?", "რომელი მიგნება არ არის შესაბამისი ჩვენს შემთხვევაში?"],
    briefItems: ["ერთი აბზაცის summary", "ძირითადი risk note", "მოკლე კითხვები"],
    related: ["summary", "risk", "doctor question"],
  },
  "how-it-works": {
    eyebrow: "როგორ წავიკითხოთ",
    title: "საიტის ლოგიკა მარტივია: მტკიცებულება, რისკი, კითხვა.",
    summary: "ეს გვერდი ხსნის, როგორ უნდა გამოიყენოს მომხმარებელმა კვლევითი ინფორმაცია ისე, რომ ის არ აერიოს სამედიცინო რჩევაში.",
    shortAnswer: "წაიკითხე claim, ნახე grading, გაიგე შეზღუდვა და მხოლოდ ამის შემდეგ ჩამოაყალიბე კითხვა ექიმთან.",
    icon: ShieldCheck,
    grade: "established",
    gradeLabel: "სარგებლობის წესი",
    confidenceLabel: "უსაფრთხო გამოყენების ჩარჩო",
    metrics: [
      { label: "ნაბიჯი", value: "3", detail: "evidence-risk-question" },
      { label: "საზღვარი", value: "1", detail: "არა სამედიცინო რჩევა" },
      { label: "როლი", value: "2", detail: "ოჯახი და ექიმი" },
      { label: "ბრიფი", value: "1", detail: "საუბრისთვის" },
    ],
    evidence: ["ერთიანი pattern ამცირებს ინფორმაციულ ქაოსს.", "clinical boundary ჩანს ყველა მნიშვნელოვან გვერდზე.", "assistant მოქმედებები იწყება preset არჩევანით და არა ცარიელი input-ით."],
    uncertainty: ["საიტი ვერ იცნობს სრულ სამედიცინო ისტორიას.", "ზოგი თემის grading მომავალში უნდა დაიხვეწოს.", "მომხმარებელი მაინც საჭიროებს ექიმის განმარტებას."],
    risks: ["კვლევითი ინფორმაცია შეიძლება ზედმეტად დარწმუნებულად ჟღერდეს, თუ საზღვარი არ ჩანს.", "მომხმარებელმა არ უნდა მიიღოს გადაწყვეტილება მხოლოდ პორტალის მიხედვით."],
    doctorQuestions: ["როგორ წავიკითხოთ ეს მტკიცებულება ჩვენს კონტექსტში?", "რა არის ყველაზე მნიშვნელოვანი რისკი ამ თემაში?", "რა მონაცემი სჭირდება ექიმს უკეთესი პასუხისთვის?"],
    briefItems: ["გამოყენების წესი", "საზღვარი", "კითხვის ფორმა"],
    related: ["how to read", "boundary", "assistant"],
  },
  support: {
    eyebrow: "მხარდაჭერა",
    title: "დახმარება უნდა იყოს მშვიდი, კონკრეტული და არა გადატვირთული.",
    summary: "მხარდაჭერის ხედვა ეხმარება მომხმარებელს გაიგოს, სად მოძებნოს განმარტება, როგორ მოამზადოს კითხვა და რას არ ნიშნავს პლატფორმა.",
    shortAnswer: "თუ მომხმარებელი იბნევა, საუკეთესო next step არის მოკლე ბრიფი და ექიმთან ერთ-ორი მკაფიო კითხვა.",
    icon: LifeBuoy,
    grade: "established",
    gradeLabel: "გამოყენების მხარდაჭერა",
    confidenceLabel: "კომუნიკაციის დახმარება",
    metrics: [
      { label: "გზა", value: "3", detail: "წაკითხვა, შერჩევა, კითხვა" },
      { label: "FAQ", value: "8", detail: "მოკლე პასუხი" },
      { label: "საზღვარი", value: "1", detail: "research-only" },
      { label: "ბრიფი", value: "2 წთ", detail: "მომზადება" },
    ],
    evidence: ["მხარდაჭერა ეფუძნება ერთიან ტერმინებს და მოკლე გზებს.", "მომხმარებელს ეძლევა მოქმედება და არა მხოლოდ ტექსტი.", "ყველა დახმარება ინარჩუნებს ექიმის როლს."],
    uncertainty: ["პერსონალური სამედიცინო კითხვა ვერ გადაწყდება საიტზე.", "ზოგი რესურსი საჭიროებს ინდივიდუალურ განმარტებას.", "საჭიროა მომავალი accessibility ტესტირება."],
    risks: ["support ტექსტი არ უნდა ჟღერდეს როგორც triage ან რეკომენდაცია.", "მომხმარებელი უნდა გადამისამართდეს ექიმთან, როცა კითხვა კლინიკურია."],
    doctorQuestions: ["რომელი კითხვა უნდა დავუსვა პირველ რიგში ექიმს?", "როგორ ავუხსნა ჩემი მთავარი concern მოკლედ?", "რა ინფორმაცია უნდა მოვამზადო ვიზიტამდე?"],
    briefItems: ["მთავარი concern", "ერთი მტკიცებულება", "ერთი კითხვა"],
    related: ["help", "brief", "visit"],
  },
  settings: {
    eyebrow: "პარამეტრები",
    title: "პარამეტრები უნდა მართავდეს სირთულეს და არა სამედიცინო გადაწყვეტილებას.",
    summary: "მომხმარებელს უნდა შეეძლოს ენის, სირთულის და ბრიფის ფორმატის არჩევა, მაგრამ არა treatment recommendation-ის მიღება.",
    shortAnswer: "პარამეტრების მიზანია ინფორმაციის კითხვა გახდეს კომფორტული და უსაფრთხო, არა clinical decision support.",
    icon: Scale,
    grade: "research",
    gradeLabel: "პროდუქტის პარამეტრი",
    confidenceLabel: "უსაფრთხო შეზღუდვებით",
    metrics: [
      { label: "ენა", value: "2", detail: "ქართული და English" },
      { label: "რეჟიმი", value: "2", detail: "მარტივი და კვლევითი" },
      { label: "ბრიფი", value: "3", detail: "სიგრძის ვარიანტი" },
      { label: "საზღვარი", value: "1", detail: "უცვლელი" },
    ],
    evidence: ["სირთულის რეჟიმი ეხმარება სხვადასხვა მომხმარებელს.", "research-only disclaimer არ უნდა ითიშებოდეს.", "ქართული-first ტექსტი ინარჩუნებს მოკლე label-ებს."],
    uncertainty: ["პერსონალიზაცია ჯერ არ უნდა გახდეს რეკომენდაციის სისტემა.", "ზედმეტი პარამეტრი UX-ს გაართულებს.", "საჭიროა მომავალში usability testing."],
    risks: ["პარამეტრი არ უნდა ქმნიდეს შთაბეჭდილებას, რომ საიტი კონკრეტულ მკურნალობას არჩევს.", "მომხმარებლის კონტექსტი არ უნდა ინტერპრეტირდეს როგორც დიაგნოზი."],
    doctorQuestions: ["რა ფორმატით ჯობს წავიღო ინფორმაცია ექიმთან?", "რა დეტალი შეიძლება იყოს ზედმეტი ან არასწორად ინტერპრეტირებული?", "რა უნდა დარჩეს მხოლოდ ექიმის შეფასებისთვის?"],
    briefItems: ["ენის არჩევა", "სირთულის დონე", "უსაფრთხო საზღვარი"],
    related: ["preferences", "mode", "safety"],
  },
  audit: {
    eyebrow: "აუდიტის კვალი",
    title: "სანდო სისტემა აჩვენებს, როგორ მივიდა მონაცემი ეკრანამდე.",
    summary: "აუდიტი აღწერს წყაროს, ცვლილებას, review სტატუსს და იმას, სად გამოიყენება claim ან risk note.",
    shortAnswer: "თუ მონაცემის გზა ჩანს, მომხმარებელი უკეთ არჩევს, რა არის სანდო, რა არის ახალი და რა საჭიროებს გადამოწმებას.",
    icon: FileText,
    grade: "established",
    gradeLabel: "გამჭვირვალობის ფენა",
    confidenceLabel: "provenance ჩანს",
    metrics: [
      { label: "ჩანაწერი", value: "219", detail: "audit event" },
      { label: "review", value: "3", detail: "დონე" },
      { label: "change", value: "27", detail: "ბოლო თვეში" },
      { label: "risk", value: "88", detail: "დაკავშირებული" },
    ],
    evidence: ["audit trail ინახავს ცვლილების დროს, მიზეზს და გამოყენების ადგილს.", "review დონე ეხმარება ავტომატური და შემოწმებული მონაცემის გამიჯვნას.", "claim-to-risk კავშირი ამცირებს ზედმეტად დარწმუნებულ wording-ს."],
    uncertainty: ["ყველა historical source სრულად სტრუქტურირებული არ არის.", "audit event-ის ენა უნდა იყოს ადამიანისთვის გასაგები.", "მომავალში საჭიროა უფრო მკაცრი governance."],
    risks: ["გამჭვირვალობის გარეშე AI-generated ან ავტომატური ტექსტი შეიძლება ზედმეტად სანდოდ ჩანდეს.", "review სტატუსის დამალვა ზრდის არასწორი გამოყენების რისკს."],
    doctorQuestions: ["ეს მიგნება როდის და რატომ განახლდა?", "ვინ ან რა პროცესმა შეამოწმა claim?", "რომელ რისკთან არის ეს წყარო დაკავშირებული?"],
    briefItems: ["provenance", "review", "change reason"],
    related: ["audit", "review", "trace"],
  },
  knowledge: {
    eyebrow: "ცოდნის ბაზა",
    title: "ცოდნა უკეთ მუშაობს, როცა ტერმინი, წყარო და კითხვა ერთად ჩანს.",
    summary: "ცოდნის ბაზა ხსნის ტერმინებს მოკლედ და აკავშირებს მათ მტკიცებულებასთან, რისკთან და ექიმთან კითხვასთან.",
    shortAnswer: "ტერმინის გაგება პირველი ნაბიჯია; შემდეგ უნდა ვნახოთ, რა წყარო უჭერს მხარს და რა ზღვარი აქვს გამოყენებას.",
    icon: Library,
    grade: "established",
    gradeLabel: "საგანმანათლებლო ფენა",
    confidenceLabel: "ტერმინები გამარტივებულია",
    metrics: [
      { label: "ტერმინი", value: "64", detail: "მარტივი ახსნა" },
      { label: "წყარო", value: "128", detail: "დაკავშირებული" },
      { label: "კითხვა", value: "42", detail: "ექიმთან" },
      { label: "რისკი", value: "18", detail: "warning note" },
    ],
    evidence: ["ტერმინები წარმოდგენილია family-safe ენით.", "თითოეულ განმარტებას ახლავს შესაბამისი წყარო ან თემა.", "გაურკვევლობა ცალკე ჩანს და არ იმალება განმარტებაში."],
    uncertainty: ["ზოგი ტერმინი სხვადასხვა სპეციალისტთან განსხვავებულად გამოიყენება.", "მარტივი ახსნა შეიძლება საჭიროებდეს დამატებით დეტალს.", "ტერმინის ცოდნა არ ნიშნავს დიაგნოსტიკურ შეფასებას."],
    risks: ["ტერმინის ზედმეტად პირდაპირი გაგება შეიძლება შეცდომაში შემყვანი იყოს.", "განმარტება არ უნდა იქცეს თვითდიაგნოზად."],
    doctorQuestions: ["ეს ტერმინი რას ნიშნავს ჩვენს შემთხვევაში?", "რომელი ნაწილი არის მნიშვნელოვანი და რომელი ზოგადი ახსნაა?", "არსებობს სხვა ტერმინი, რომელიც უკეთ აღწერს მდგომარეობას?"],
    briefItems: ["ტერმინის ახსნა", "წყარო", "ექიმთან კითხვა"],
    related: ["terms", "source", "question"],
  },
};

const enTopics: Record<PageKey, TopicModel> = Object.fromEntries(
  Object.entries(kaTopics).map(([key, topic]) => [
    key,
    {
      ...topic,
      eyebrow: "Research view",
      title: topic.title,
      summary: "This page keeps the same evidence, uncertainty, risk, and doctor-question structure used in the Georgian-first interface.",
      shortAnswer: "Read the claim, check the evidence grade, review uncertainty, and turn the result into a safe question for the clinician.",
      gradeLabel: topic.grade === "established" ? "Structured evidence" : topic.grade === "promising" ? "Promising research" : "Research only",
      confidenceLabel: "Not medical advice",
      evidence: ["Evidence is separated from interpretation.", "Each topic keeps a visible research boundary.", "The next step is phrased as a doctor question."],
      uncertainty: ["Clinical relevance depends on individual context.", "Some sources may be preliminary or indirect.", "A clinician should interpret applicability."],
      risks: ["Research information must not become self-directed treatment.", "The portal does not diagnose or prescribe."],
      doctorQuestions: ["Which part of this evidence applies to our context?", "What remains uncertain or unsafe to infer?", "What should we monitor or discuss next?"],
      briefItems: ["Short answer", "Main uncertainty", "Doctor question"],
      related: ["evidence", "risk", "doctor question"],
    },
  ])
) as Record<PageKey, TopicModel>;

function contentFor(locale: Locale, pageKey: PageKey) {
  return locale === "ka" ? kaTopics[pageKey] : enTopics[pageKey];
}

function Surface({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-3xl border border-white/10 bg-white/[0.035] ${className}`}>{children}</section>;
}

function Pill({ children, tone = "slate" }: { children: ReactNode; tone?: Tone }) {
  const style = toneStyles[tone];
  return <span className={`inline-flex items-center rounded-full border px-3 py-1 text-[0.72rem] font-semibold ${style.border} ${style.bg} ${style.text}`}>{children}</span>;
}

function GradeBadge({ topic }: { topic: TopicModel }) {
  return <span className={`inline-flex items-center rounded-full border px-3 py-1 text-[0.72rem] font-semibold ${gradeStyles[topic.grade]}`}>{topic.gradeLabel}</span>;
}

function MetricGrid({ metrics }: { metrics: Metric[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric) => (
        <Surface key={metric.label} className="p-4">
          <p className="text-[0.72rem] font-medium leading-5 text-slate-500">{metric.label}</p>
          <p className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-white">{metric.value}</p>
          <p className="mt-1 text-xs leading-5 text-slate-400">{metric.detail}</p>
        </Surface>
      ))}
    </div>
  );
}

function FlowCard({ icon: Icon, label, title, body, tone }: { icon: LucideIcon; label: string; title: string; body: string; tone: Tone }) {
  const style = toneStyles[tone];
  return (
    <Surface className={`p-5 ${style.bg} ${style.border}`}>
      <div className="flex items-center justify-between gap-3">
        <span className={`grid h-10 w-10 place-items-center rounded-xl border border-white/10 bg-black/10 ${style.icon}`}>
          <Icon className="h-5 w-5" />
        </span>
        <Pill tone={tone}>{label}</Pill>
      </div>
      <h2 className="mt-5 text-lg font-semibold leading-7 text-white">{title}</h2>
      <p className="mt-3 text-sm leading-7 text-slate-300">{body}</p>
    </Surface>
  );
}

function ListBlock({ icon: Icon, title, items, tone = "slate" }: { icon: LucideIcon; title: string; items: string[]; tone?: Tone }) {
  const style = toneStyles[tone];
  return (
    <Surface className="p-5">
      <div className="flex items-center gap-3">
        <span className={`grid h-9 w-9 place-items-center rounded-xl border ${style.border} ${style.bg} ${style.icon}`}>
          <Icon className="h-4 w-4" />
        </span>
        <h2 className="text-base font-semibold text-white">{title}</h2>
      </div>
      <div className="mt-4 space-y-3">
        {items.map((item) => (
          <div key={item} className="flex gap-3 rounded-2xl border border-white/8 bg-[#0b1424]/70 px-3 py-3 text-sm leading-6 text-slate-300">
            <CheckCircle2 className={`mt-1 h-4 w-4 shrink-0 ${style.icon}`} />
            <span>{item}</span>
          </div>
        ))}
      </div>
    </Surface>
  );
}

function BriefBuilder({ topic, locale }: { topic: TopicModel; locale: Locale }) {
  const isKa = locale === "ka";
  return (
    <Surface className="p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Pill tone="emerald">{isKa ? "ბრიფის მონახაზი" : "Brief outline"}</Pill>
          <h2 className="mt-4 text-xl font-semibold leading-7 text-white">{isKa ? "ექიმთან წასაღები მოკლე ტექსტი" : "A short note for the clinician"}</h2>
          <p className="mt-2 text-sm leading-7 text-slate-400">{isKa ? "აირჩიე მხოლოდ ის, რაც საუბარს გაამარტივებს. ეს არ არის დანიშნულების მოთხოვნა." : "Keep only what makes the conversation clearer. This is not a treatment request."}</p>
        </div>
        <button type="button" className="inline-flex items-center justify-center gap-2 rounded-2xl border border-emerald-300/20 bg-emerald-300/[0.07] px-4 py-2.5 text-sm font-semibold text-emerald-50 transition hover:bg-emerald-300/[0.11]">
          {isKa ? "ბრიფის შედგენა" : "Build brief"}
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-5 grid gap-3 md:grid-cols-3">
        {topic.briefItems.map((item, index) => (
          <div key={item} className="rounded-2xl border border-white/10 bg-[#0b1424] p-4">
            <p className="text-[0.72rem] font-semibold text-slate-500">{index + 1}</p>
            <p className="mt-2 text-sm font-semibold leading-6 text-white">{item}</p>
          </div>
        ))}
      </div>
    </Surface>
  );
}

function Hero({ topic, locale }: { topic: TopicModel; locale: Locale }) {
  const isKa = locale === "ka";
  const Icon = topic.icon;
  return (
    <Surface className="overflow-hidden p-5 sm:p-6">
      <div className="grid gap-6 lg:grid-cols-[1fr_18rem]">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Pill tone="sky">{topic.eyebrow}</Pill>
            <GradeBadge topic={topic} />
          </div>
          <h1 className="mt-5 max-w-5xl text-[clamp(1.6rem,3vw,3rem)] font-semibold leading-[1.14] tracking-[-0.025em] text-white">{topic.title}</h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-300 sm:text-base">{topic.summary}</p>
          <div className="mt-5 rounded-2xl border border-white/10 bg-[#0b1424] p-4">
            <p className="text-[0.72rem] font-semibold text-slate-500">{isKa ? "მოკლე პასუხი" : "Short answer"}</p>
            <p className="mt-2 text-sm leading-7 text-slate-200">{topic.shortAnswer}</p>
          </div>
        </div>
        <div className="rounded-3xl border border-white/10 bg-[#0b1424] p-5">
          <span className="grid h-12 w-12 place-items-center rounded-2xl border border-sky-300/20 bg-sky-300/[0.07] text-sky-100">
            <Icon className="h-6 w-6" />
          </span>
          <p className="mt-5 text-sm font-semibold text-white">{topic.confidenceLabel}</p>
          <p className="mt-3 text-xs leading-6 text-slate-400">{isKa ? "ინტერფეისი განკუთვნილია კვლევის გასაგებად და ექიმთან საუბრის მოსამზადებლად." : "The interface is for understanding research and preparing a safer clinician conversation."}</p>
          <div className="mt-5 flex flex-wrap gap-2">
            {topic.related.map((item) => <Pill key={item}>{item}</Pill>)}
          </div>
        </div>
      </div>
    </Surface>
  );
}

export function PortalHomeDashboard({ locale }: { locale: Locale }) {
  const topic = contentFor(locale, "today");
  const isKa = locale === "ka";

  return (
    <div className="space-y-4">
      <Hero topic={topic} locale={locale} />

      <section className="grid gap-4 lg:grid-cols-3">
        <FlowCard icon={BookOpen} label={isKa ? "1. მტკიცებულება" : "1. Evidence"} title={isKa ? "რა ვიცით" : "What we know"} body={isKa ? "ნახე მოკლე claim, წყაროების ხარისხი და რამდენად ახლოსაა კვლევა HIE-ის კონტექსტთან." : "Read the claim, source quality, and relevance to the HIE context."} tone="sky" />
        <FlowCard icon={AlertTriangle} label={isKa ? "2. რისკი" : "2. Risk"} title={isKa ? "რა არის გაურკვეველი" : "What is uncertain"} body={isKa ? "ყოველ თემას ახლავს შეზღუდვა: population mismatch, safety gap ან კვლევითი საზღვარი." : "Each topic includes limits such as population mismatch, safety gaps, or research boundaries."} tone="amber" />
        <FlowCard icon={Stethoscope} label={isKa ? "3. კითხვა" : "3. Question"} title={isKa ? "რა ვკითხოთ ექიმს" : "What to ask"} body={isKa ? "საბოლოო ნაბიჯი არის მოკლე, მშვიდი და ექიმთან განსახილველი კითხვა, არა თვითმკურნალობა." : "The final step is a concise clinician question, not self-directed care."} tone="emerald" />
      </section>

      <MetricGrid metrics={topic.metrics} />

      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <ListBlock icon={BookOpen} title={isKa ? "დღის მტკიცებულება" : "Today’s evidence"} items={topic.evidence} tone="sky" />
        <ListBlock icon={AlertTriangle} title={isKa ? "სიფრთხილის მიზეზი" : "Reasons for caution"} items={topic.uncertainty} tone="amber" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <ListBlock icon={Scale} title={isKa ? "რისკის ჩანაწერი" : "Risk notes"} items={topic.risks} tone="violet" />
        <ListBlock icon={MessageSquareText} title={isKa ? "ექიმთან დასასმელი კითხვები" : "Questions for the doctor"} items={topic.doctorQuestions} tone="emerald" />
      </div>

      <BriefBuilder topic={topic} locale={locale} />
    </div>
  );
}

export function PortalTopicPage({ locale, pageKey }: { locale: Locale; pageKey: PageKey }) {
  const topic = contentFor(locale, pageKey);
  const isKa = locale === "ka";

  return (
    <div className="space-y-4">
      <Hero topic={topic} locale={locale} />
      <MetricGrid metrics={topic.metrics} />

      <section className="grid gap-4 xl:grid-cols-3">
        <FlowCard icon={BookOpen} label={isKa ? "მტკიცებულება" : "Evidence"} title={isKa ? "რა ვიცით" : "What we know"} body={topic.evidence[0]} tone="sky" />
        <FlowCard icon={AlertTriangle} label={isKa ? "გაურკვევლობა" : "Uncertainty"} title={isKa ? "რა არ ვიცით" : "What is uncertain"} body={topic.uncertainty[0]} tone="amber" />
        <FlowCard icon={Stethoscope} label={isKa ? "ექიმთან კითხვა" : "Doctor question"} title={isKa ? "რა ვიკითხოთ" : "What to ask"} body={topic.doctorQuestions[0]} tone="emerald" />
      </section>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <ListBlock icon={BookOpen} title={isKa ? "მტკიცებულების დეტალი" : "Evidence detail"} items={topic.evidence} tone="sky" />
        <ListBlock icon={Search} title={isKa ? "გაურკვევლობა" : "Uncertainty"} items={topic.uncertainty} tone="amber" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <ListBlock icon={ShieldCheck} title={isKa ? "საზღვარი და რისკი" : "Boundary and risk"} items={topic.risks} tone="violet" />
        <ListBlock icon={MessageSquareText} title={isKa ? "ექიმთან კითხვები" : "Doctor questions"} items={topic.doctorQuestions} tone="emerald" />
      </div>

      <BriefBuilder topic={topic} locale={locale} />
    </div>
  );
}
