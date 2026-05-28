"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  ArrowRight,
  Bell,
  BookOpen,
  Brain,
  BarChart3,
  CalendarClock,
  CheckCircle2,
  Database,
  FileText,
  FlaskConical,
  Heart,
  Library,
  Gauge,
  LifeBuoy,
  Network,
  Settings,
  TrendingUp,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  UsersRound,
  type LucideIcon,
} from "lucide-react";
import type { Locale } from "@/lib/seo";

type Tone = "blue" | "cyan" | "emerald" | "violet" | "amber" | "rose" | "slate";
type DetailCard = { label: string; title: string; body: string; tone?: Tone };
type WorkItem = { label: string; value: string; status: string };
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

type PageContent = {
  eyebrow: string;
  title: string;
  subtitle: string;
  icon: LucideIcon;
  metrics: Array<{ label: string; value: string; detail: string; tone: Tone }>;
  cards: DetailCard[];
  worklist: WorkItem[];
  asideTitle: string;
  asideItems: string[];
};

const InfoIcon = ShieldCheck;

const toneClasses: Record<Tone, { chip: string; card: string; ring: string; icon: string; glow: string; text: string }> = {
  blue: { chip: "bg-blue-500/12 text-blue-100 ring-blue-400/30", card: "from-blue-500/12 via-slate-950/80 to-slate-900/70", ring: "ring-blue-400/20", icon: "bg-blue-500/18 text-blue-200 ring-blue-300/25", glow: "shadow-blue-500/20", text: "text-blue-200" },
  cyan: { chip: "bg-cyan-400/12 text-cyan-100 ring-cyan-300/30", card: "from-cyan-400/14 via-slate-950/80 to-slate-900/70", ring: "ring-cyan-300/22", icon: "bg-cyan-400/18 text-cyan-100 ring-cyan-300/25", glow: "shadow-cyan-400/20", text: "text-cyan-200" },
  emerald: { chip: "bg-emerald-400/12 text-emerald-100 ring-emerald-300/30", card: "from-emerald-400/14 via-slate-950/80 to-slate-900/70", ring: "ring-emerald-300/22", icon: "bg-emerald-400/18 text-emerald-100 ring-emerald-300/25", glow: "shadow-emerald-400/20", text: "text-emerald-200" },
  violet: { chip: "bg-violet-400/12 text-violet-100 ring-violet-300/30", card: "from-violet-500/14 via-slate-950/80 to-slate-900/70", ring: "ring-violet-300/22", icon: "bg-violet-400/18 text-violet-100 ring-violet-300/25", glow: "shadow-violet-400/20", text: "text-violet-200" },
  amber: { chip: "bg-amber-300/12 text-amber-100 ring-amber-300/30", card: "from-amber-300/12 via-slate-950/80 to-slate-900/70", ring: "ring-amber-300/22", icon: "bg-amber-300/18 text-amber-100 ring-amber-300/25", glow: "shadow-amber-300/15", text: "text-amber-100" },
  rose: { chip: "bg-rose-400/12 text-rose-100 ring-rose-300/30", card: "from-rose-400/14 via-slate-950/80 to-slate-900/70", ring: "ring-rose-300/22", icon: "bg-rose-400/18 text-rose-100 ring-rose-300/25", glow: "shadow-rose-400/20", text: "text-rose-100" },
  slate: { chip: "bg-slate-700/60 text-slate-200 ring-white/10", card: "from-white/[0.06] via-slate-950/80 to-slate-900/70", ring: "ring-white/10", icon: "bg-white/8 text-slate-200 ring-white/10", glow: "shadow-slate-950/20", text: "text-slate-200" },
};

const georgianPages: Record<PageKey, PageContent> = {
  today: {
    eyebrow: "დღევანდელი ფოკუსი",
    title: "დღეს რა არის მნიშვნელოვანი — მოკლე, გასაგები და ექიმთან გადასამოწმებელი.",
    subtitle: "ეს გვერდი აერთიანებს ახალ evidence-ს, მიმდინარე კითხვებს და იმ ნაბიჯებს, რომლებიც კლინიკურ გუნდთან უნდა განიხილოთ.",
    icon: Activity,
    metrics: [
      { label: "ახალი ცვლილება", value: "6", detail: "ბოლო 24 საათში", tone: "cyan" },
      { label: "ექიმთან კითხვა", value: "9", detail: "მომზადებულია", tone: "blue" },
      { label: "დაკვირვების სია", value: "4", detail: "საყურადღებო თემა", tone: "violet" },
    ],
    cards: [
      { label: "რა შეიცვალა", title: "კვლევების მოკლე განახლება", body: "ახალი წყაროები დაჯგუფებულია: რა არის პრაქტიკული, რა რჩება ჰიპოთეზად და რა საჭიროებს ექიმის შეფასებას.", tone: "cyan" },
      { label: "შემდეგი ნაბიჯი", title: "კითხვები ვიზიტისთვის", body: "სისტემა აქცევს რთულ ტერმინებს ოჯახისთვის გასაგებ კითხვებად, რათა ვიზიტი იყოს კონკრეტული და მშვიდი.", tone: "amber" },
      { label: "უსაფრთხოება", title: "არავითარი თვითნებური ცვლილება", body: "თერაპია, დოზა ან ჩარევა არ იცვლება მხოლოდ პლატფორმის მიხედვით; ყველაფერი გადის კლინიკურ შემოწმებას.", tone: "emerald" },
    ],
    worklist: [
      { label: "ტვინის კავშირების კვლევა", value: "ოჯახისთვის გასაგები შეჯამება", status: "მზადდება" },
      { label: "მოტორული მხარდაჭერა", value: "ექიმთან განსახილველი კითხვა", status: "მომდევნო" },
      { label: "კვლევის დროითი ფანჯარა", value: "საკითხი ასაკობრივ ფანჯარაზე", status: "შემოწმება" },
    ],
    asideTitle: "დღის მოკლე წესი",
    asideItems: ["დაიწყე იმით, რაც შეიცვალა", "გაარჩიე evidence და ჰიპოთეზა", "ექიმთან წაიღე მხოლოდ შემოწმებული კითხვები"],
  },
  dashboard: {
    eyebrow: "მართვის ცენტრი",
    title: "კვლევის მართვის პანელი, სადაც მტკიცებულება ჰიპოთეზად და შემდეგ განხილვად იქცევა.",
    subtitle: "მონიტორინგის სივრცე აჩვენებს წყაროებს, შემოწმებას, თერაპიის კანდიდატებს, აქტიურ კვლევებს და პარტნიორ მონაცემებს ერთ ფრთხილ არქიტექტურაში.",
    icon: Activity,
    metrics: [
      { label: "მტკიცებულების ჩანაწერები", value: "12,842", detail: "რეცენზირებული და რეალური მონაცემები", tone: "blue" },
      { label: "შემოწმებული ჰიპოთეზები", value: "173", detail: "შემოწმების რიგში", tone: "violet" },
      { label: "თერაპიის კანდიდატები", value: "28", detail: "კლინიკური საზღვრით", tone: "emerald" },
      { label: "აქტიური კვლევები", value: "14", detail: "მრავალცენტრიანი კვლევები", tone: "cyan" },
    ],
    cards: [
      { label: "მტკიცებულების რუკა", title: "წყაროების შეგროვება და კურაცია", body: "ყველა წყარო გადის relevance, maturity და safety ნიშნულებს, სანამ ოჯახის ხედვაში გამოჩნდება.", tone: "blue" },
      { label: "ჰიპოთეზების გენერაცია", title: "შაბლონების პოვნა", body: "იდეები ინახება როგორც ჰიპოთეზა, არა როგორც რეკომენდაცია; მათ სჭირდება validation და ექიმის კონტექსტი.", tone: "violet" },
      { label: "კლინიკური მნიშვნელობა", title: "გადათარგმნა უსაფრთხო განხილვად", body: "საბოლოო ფენა ამზადებს მოკლე კლინიკურ brief-ს და ოჯახის კითხვებს, არა მკურნალობის ინსტრუქციას.", tone: "emerald" },
    ],
    worklist: [
      { label: "მტკიცებულების რუკა", value: "12,842 ჩანაწერი დამუშავებულია", status: "აქტიური" },
      { label: "შემოწმება", value: "173 მხარდაჭერილი ჰიპოთეზა", status: "გადახედვა" },
      { label: "პროცესი", value: "28 თერაპიის კანდიდატი", status: "დაცული" },
    ],
    asideTitle: "პროცესის კონტროლი",
    asideItems: ["შეგროვება და კურაცია", "შაბლონების პოვნა", "შემოწმება და დახვეწა", "პრიორიტეტი და შეფასება", "გადათარგმნა და სწავლა"],
  },
  brain: {
    eyebrow: "ცოცხალი კვლევითი ტვინი",
    title: "ციფრული ტვინი აჩვენებს კავშირს მონაცემებს, დაკვირვებასა და კვლევით კითხვებს შორის.",
    subtitle: "ვიზუალიზაცია განკუთვნილია ორიენტირებისთვის. იგი არ ადგენს დიაგნოზს და არ ცვლის MRI-ს ან ნევროლოგის შეფასებას.",
    icon: Brain,
    metrics: [
      { label: "ფენები", value: "7", detail: "MRI, მოტორული, კოგნიტური", tone: "cyan" },
      { label: "კავშირები", value: "48", detail: "კვლევითი კავშირები", tone: "blue" },
      { label: "შემოწმების ჩანაწერები", value: "16", detail: "კლინიკურ კონტექსტში", tone: "emerald" },
    ],
    cards: [
      { label: "MRI კონტექსტი", title: "სურათი როგორც რუკა, არა პასუხი", body: "ტვინის ფენები ეხმარება საუბარს, მაგრამ ნებისმიერი ინტერპრეტაცია რჩება სპეციალისტთან.", tone: "cyan" },
      { label: "განვითარება", title: "დროითი ცვლილებების დაკვირვება", body: "სისტემა აერთიანებს ფუნქციურ პროგრესს, ვიზიტებს და კვლევით მიგნებებს ერთ ქრონოლოგიასთან.", tone: "amber" },
      { label: "კითხვები", title: "რა უნდა დაისვას ექიმთან", body: "ყველა მიგნება გადაიქცევა შეკითხვად, არა ინსტრუქციად: რა ვნახოთ, რა გავზომოთ, რა არის საზღვარი.", tone: "emerald" },
    ],
    worklist: [
      { label: "კავშირები", value: "კვლევითი ახსნა", status: "მარტივი ენით" },
      { label: "მოტორული ფენა", value: "მხარდამჭერი თერაპიის კონტექსტი", status: "დაკვირვება" },
      { label: "კოგნიტური ფენა", value: "შემდგომი კითხვები", status: "შემდეგი" },
    ],
    asideTitle: "ტვინის ხედვის ფენები",
    asideItems: ["სტრუქტურული კონტექსტი", "ფუნქციური პროგრესი", "კვლევითი წყაროები", "ექიმთან კითხვები"],
  },
  hypotheses: {
    eyebrow: "ჰიპოთეზების შემოწმება",
    title: "ჰიპოთეზები ინახება მკაფიო სტატუსით: რას ვამოწმებთ, რატომ და ვისთან.",
    subtitle: "აქ იდეა ჯერ მხოლოდ სამუშაო ვერსიაა. იგი უნდა იყოს დაკავშირებული წყაროსთან, რისკთან და კლინიკურ შემოწმებასთან.",
    icon: FlaskConical,
    metrics: [
      { label: "ძლიერი მხარდაჭერა", value: "28%", detail: "მაღალი სანდოობა", tone: "emerald" },
      { label: "საშუალო", value: "41%", detail: "საჭიროებს შემოწმებას", tone: "blue" },
      { label: "შეზღუდული", value: "18%", detail: "ჰიპოთეზის დონე", tone: "amber" },
    ],
    cards: [
      { label: "მტკიცებულება", title: "წყაროების ხარისხი ჩანს თავიდანვე", body: "ჰიპოთეზას თან ახლავს წყაროს სიმწიფე, პოპულაციის შესაბამისობა და უსაფრთხოების შენიშვნა.", tone: "blue" },
      { label: "შემოწმება", title: "შემოწმება ხდება ნაბიჯ-ნაბიჯ", body: "იდეა გადადის რიგში მხოლოდ მაშინ, როცა ოჯახის კითხვა და ექიმის კონტექსტი განსაზღვრულია.", tone: "violet" },
      { label: "გადაწყვეტილების საზღვარი", title: "შემოწმებული არ ნიშნავს დანიშნულს", body: "დადასტურებული ჰიპოთეზაც კი რჩება განხილვის მასალად და არა მკურნალობის ბრძანებად.", tone: "emerald" },
    ],
    worklist: [
      { label: "ნეიროანთება", value: "წყაროთა ჯგუფი შემოწმებულია", status: "საშუალო" },
      { label: "მიტოქონდრიული მხარდაჭერა", value: "მექანიზმის რუკა", status: "ჰიპოთეზა" },
      { label: "ძილი და აღდგენა", value: "ოჯახის დაკვირვებასთან კავშირი", status: "თვალყურის დევნება" },
    ],
    asideTitle: "შემოწმების კითხვები",
    asideItems: ["რომელ წყაროზე დგას იდეა?", "შეესაბამება თუ არა ასაკს და კონტექსტს?", "რა უნდა ჰკითხოს ოჯახმა ექიმს?"],
  },
  therapies: {
    eyebrow: "თერაპიის კანდიდატები",
    title: "თერაპიების დაკვირვების სია აჩვენებს შესაძლებლობებს, მტკიცებულების სიმწიფეს და კლინიკურ საზღვარს.",
    subtitle: "თერაპიული იდეა არ არის რეკომენდაცია. გვერდი ეხმარება ოჯახს მოამზადოს სანდო, მოკლე და ფრთხილი საუბარი სპეციალისტთან.",
    icon: Stethoscope,
    metrics: [
      { label: "დაკვირვების სია", value: "28", detail: "საკანდიდატო იდეები", tone: "violet" },
      { label: "ადრეული მტკიცებულება", value: "11", detail: "მხოლოდ განხილვა", tone: "amber" },
      { label: "ექიმის შემოწმება", value: "100%", detail: "აუცილებელი", tone: "emerald" },
    ],
    cards: [
      { label: "მიზნობრივი მხარდაჭერა", title: "მიზნობრივი მხარდაჭერები", body: "სისტემა აჩვენებს რა არის supportive და რა ითხოვს მკაცრ კლინიკურ შეფასებას.", tone: "emerald" },
      { label: "მოტორული განვითარება", title: "განვითარების მიდგომები", body: "family-safe summary ხაზს უსვამს მიზანს, შესაძლო დაკვირვებას და სპეციალისტის როლს.", tone: "cyan" },
      { label: "ნეირომოდულაცია", title: "მაღალი სიფრთხილის თემები", body: "preclinical ან early-stage მიმართულებები ცალკე ინიშნება, რათა არ აირიოს პრაქტიკულ რჩევაში.", tone: "rose" },
    ],
    worklist: [
      { label: "Cognitive supports", value: "early evidence", status: "watch" },
      { label: "Motor skill development", value: "therapy discussion", status: "doctor" },
      { label: "Non-invasive research", value: "preclinical boundary", status: "guarded" },
    ],
    asideTitle: "განხილვამდე",
    asideItems: ["რა არის მიზანი?", "რა არის რისკი?", "რას ვაკვირდებით?", "ვინ იღებს საბოლოო გადაწყვეტილებას?"],
  },
  timeline: {
    eyebrow: "კვლევისა და ზრუნვის ქრონოლოგია",
    title: "ქრონოლოგია აერთიანებს ვიზიტებს, წყაროებს, ჰიპოთეზებსა და ოჯახის ჩანაწერებს ერთ ხაზზე.",
    subtitle: "დროითი ხაზი ეხმარება გუნდს დაინახოს რა შეიცვალა, რა დაიხურა და რა დარჩა შემდეგ ვიზიტამდე.",
    icon: CalendarClock,
    metrics: [
      { label: "მნიშვნელოვანი ეტაპები", value: "18", detail: "დოკუმენტირებული", tone: "blue" },
      { label: "ღია follow-up", value: "7", detail: "შემდეგი ვიზიტი", tone: "amber" },
      { label: "დახურული საკითხები", value: "42", detail: "განხილულია", tone: "emerald" },
    ],
    cards: [
      { label: "დაკვირვება", title: "ოჯახის დაკვირვებები არ იკარგება", body: "ყოველ ჩანაწერს აქვს თარიღი, კონტექსტი და მომდევნო მოქმედება.", tone: "cyan" },
      { label: "კვლევა", title: "წყაროები უკავშირდება მოვლენებს", body: "კვლევის განახლება ჩანს იმ დღეს, როცა იგი ოჯახის კითხვას ან ჰიპოთეზის შემოწმებას შეეხო.", tone: "blue" },
      { label: "კლინიკური შემოწმება", title: "რა განიხილა გუნდმა", body: "ქრონოლოგია ინახავს რა გადაიხედა, რა დაიხურა და რა გადავიდა დაკვირვების სიაში.", tone: "emerald" },
    ],
    worklist: [
      { label: "2018", value: "პლატფორმა დაიწყო", status: "ეტაპი" },
      { label: "2023", value: "შემოწმებული ჰიპოთეზების ფენა", status: "აგებულია" },
      { label: "2025+", value: "კლინიკური მნიშვნელობის სწავლა", status: "მიმდინარე" },
    ],
    asideTitle: "ქრონოლოგიის გამოყენება",
    asideItems: ["შეადარე ცვლილებები დროში", "დააკავშირე კითხვა ვიზიტთან", "დახურე განხილული საკითხი"],
  },
  "evidence-map": {
    eyebrow: "მტკიცებულების რუკა",
    title: "მტკიცებულების რუკა აჩვენებს, როგორ უკავშირდება წყარო ჰიპოთეზას, კითხვას და უსაფრთხო მომდევნო ნაბიჯს.",
    subtitle: "ეს რუკა არ არის მხოლოდ ბიბლიოთეკა; ის არის კავშირის სისტემა, სადაც წყაროს ტიპი, სანდოობა და ოჯახის კითხვა ერთად ჩანს.",
    icon: Network,
    metrics: [
      { label: "რეცენზირებული", value: "44%", detail: "წყაროების ნარევი", tone: "blue" },
      { label: "კლინიკური რეესტრები", value: "24%", detail: "დაკვირვებითი", tone: "cyan" },
      { label: "პრეკლინიკური", value: "10%", detail: "ფრთხილი", tone: "amber" },
    ],
    cards: [
      { label: "წყარო", title: "წყაროები იკითხება მარტივად", body: "ყოველ წყაროს აქვს მოკლე ოჯახური შეჯამება და ტექნიკური შენიშვნა ექიმისთვის.", tone: "blue" },
      { label: "კავშირი", title: "კავშირები ჩანს ვიზუალურად", body: "პუბლიკაცია შეიძლება დაუკავშირდეს ჰიპოთეზას, თერაპიის დაკვირვების სიას ან ქრონოლოგიის მოვლენას.", tone: "cyan" },
      { label: "სანდოობა", title: "სანდოობა ცალკე ჩანს", body: "წყაროს ტიპი არ ერევა კლინიკურ რეკომენდაციაში; სანდოობის ნიშანი მხოლოდ განხილვის ხარისხს აჩვენებს.", tone: "emerald" },
    ],
    worklist: [
      { label: "ტვინის კავშირები", value: "ახალი წყაროთა ჯგუფი", status: "დარუკებულია" },
      { label: "ნეიროპროტექცია", value: "კლინიკური კვლევის ბმული", status: "შემოწმება" },
      { label: "მხარდამჭერი თერაპიები", value: "ოჯახის კითხვები", status: "მზადაა" },
    ],
    asideTitle: "რუკის ლეგენდა",
    asideItems: ["წყარო", "მექანიზმი", "ჰიპოთეზა", "კითხვა", "კლინიკური საზღვარი"],
  },
  cohorts: {
    eyebrow: "კვლევითი ჯგუფები",
    title: "კვლევითი ჯგუფები აჩვენებს გაერთიანებულ კვლევით კონტექსტს პირადი მონაცემების გარეშე.",
    subtitle: "გვერდი ეხმარება კონტექსტის გაგებას: რა ასაკი, რა შედეგი, რა ტიპის კვლევა და რამდენად ახლოსაა ეს კონკრეტულ კითხვასთან.",
    icon: UsersRound,
    metrics: [
      { label: "ჯგუფები", value: "9", detail: "გაერთიანებული", tone: "blue" },
      { label: "შედეგები", value: "32", detail: "დაკვირვების დომენები", tone: "cyan" },
      { label: "კონფიდენციალურობა", value: "დაცული", detail: "პირადი სამედიცინო ინფორმაცია არ ჩანს", tone: "emerald" },
    ],
    cards: [
      { label: "პოპულაციის შესაბამისობა", title: "ვინ ჰგავს ვის — მხოლოდ კვლევით დონეზე", body: "ჯგუფის აღწერა არ არის ინდივიდუალური პროგნოზი; იგი ეხმარება წყაროს შესაბამისობის გაგებას.", tone: "blue" },
      { label: "შედეგების დაკვირვება", title: "რას აკვირდებოდნენ კვლევებში", body: "მოტორული, კოგნიტური, გულყრის, ძილის და ოჯახის ფუნქციური შედეგები გამოყოფილია ცალკე.", tone: "cyan" },
      { label: "კონფიდენციალურობა", title: "პირადი მონაცემი არ ჩანს", body: "გვერდი მუშაობს გაერთიანებული აღწერებით და მკაფიოდ იცავს უსაფრთხოების საზღვარს.", tone: "emerald" },
    ],
    worklist: [
      { label: "ბავშვთა HIE რეესტრი", value: "შედეგების დომენები", status: "შეჯამება" },
      { label: "მოტორული განვითარების ჯგუფი", value: "თერაპიის კონტექსტი", status: "შედარება" },
      { label: "გრძელვადიანი დაკვირვება", value: "ქრონოლოგიასთან დაკავშირებული", status: "აქტიური" },
    ],
    asideTitle: "ჯგუფების კითხვები",
    asideItems: ["რა ასაკობრივი ჯგუფია?", "რა შედეგი იზომებოდა?", "რამდენად გადასატანია დასკვნა კონკრეტულ კონტექსტში?"],
  },
  "data-integrations": {
    eyebrow: "მონაცემები და ინტეგრაციები",
    title: "მონაცემები და ინტეგრაციები აჩვენებს საიდან მოდის ინფორმაცია და როგორ გადის შემოწმებას.",
    subtitle: "ყოველი წყარო მონიშნულია წარმომავლობით, განახლების სიხშირით და კლინიკური უსაფრთხოების შენიშვნით, რათა გუნდი ენდოს პროცესს და არა ბრმა ავტომაციას.",
    icon: Database,
    metrics: [
      { label: "წყაროები", value: "36", detail: "დაკავშირებულია", tone: "blue" },
      { label: "განახლება", value: "ყოველდღე", detail: "განახლების რიტმი", tone: "cyan" },
      { label: "აუდიტი", value: "ჩართული", detail: "მიკვლევადი", tone: "emerald" },
    ],
    cards: [
      { label: "რეესტრი", title: "სტრუქტურირებული წყაროები", body: "რეესტრი და პუბლიკაციების არხები გამოყოფილია კლინიკური ჩანაწერებისგან და ცალკე აფასებს შესაბამისობას.", tone: "blue" },
      { label: "ადამიანური შემოწმება", title: "ავტომაცია მარტო არ წყვეტს", body: "კრიტიკული შეჯამებები გადის ადამიანურ შემოწმებას, სანამ ოჯახის სივრცეში გამოჩნდება.", tone: "emerald" },
      { label: "მიკვლევადობა", title: "ყველა განახლება იძებნება", body: "აუდიტის ბილიკი აჩვენებს რა შეიცვალა, როდის და რომელ გვერდს შეეხო.", tone: "amber" },
    ],
    worklist: [
      { label: "პუბლიკაციების არხი", value: "ყოველდღიური სკანირება", status: "დაკავშირებულია" },
      { label: "კლინიკური ჩანაწერის იმპორტი", value: "ხელით შემოწმება", status: "დაცული" },
      { label: "ოჯახის დაკვირვებები", value: "სტრუქტურირებული ჩანაწერები", status: "მზადაა" },
    ],
    asideTitle: "ინტეგრაციის წესები",
    asideItems: ["წყაროს წარმომავლობა", "განახლების ფანჯარა", "შემოწმების პასუხისმგებელი", "აუდიტის ჩანაწერი"],
  },
  papers: {
    eyebrow: "პუბლიკაციები",
    title: "პუბლიკაციების ბიბლიოთეკა რთულ კვლევას აქცევს მოკლე, შემოწმებად ოჯახურ ბრიფად.",
    subtitle: "კვლევები წარმოდგენილია შესაბამისობით, მტკიცებულების სიმწიფით და იმ კითხვით, რომელიც ექიმთან საუბრისთვის შეიძლება გამოდგეს.",
    icon: BookOpen,
    metrics: [
      { label: "სტატიები", value: "184", detail: "შერჩეული ნაკრები", tone: "blue" },
      { label: "ბრიფები", value: "62", detail: "მარტივი ენა", tone: "cyan" },
      { label: "ექიმის კითხვები", value: "118", detail: "მომზადებულია", tone: "emerald" },
    ],
    cards: [
      { label: "მარტივი ენა", title: "ყველა კვლევას აქვს მოკლე ახსნა", body: "ოჯახი კითხულობს რას ეხება კვლევა, ვისზეა, რა შეზღუდვა აქვს და რა კითხვა დარჩა.", tone: "cyan" },
      { label: "ტექნიკური შენიშვნა", title: "ექიმისთვის რჩება დეტალი", body: "მეთოდი, პოპულაცია, შედეგი და შეზღუდვები არ იკარგება ოჯახური შეჯამების უკან.", tone: "blue" },
      { label: "შესაბამისობა", title: "კავშირი კონკრეტულ თემასთან", body: "პუბლიკაცია უკავშირდება ჰიპოთეზას, თერაპიის კანდიდატს ან ქრონოლოგიის მოვლენას.", tone: "emerald" },
    ],
    worklist: [
      { label: "ნეიროგანვითარების მიმოხილვა", value: "ოჯახური ბრიფი", status: "მზადაა" },
      { label: "ჰიპოთერმიის შედეგები", value: "შეზღუდვები მონიშნულია", status: "შემოწმებულია" },
      { label: "კავშირების კვლევები", value: "კითხვები ამოღებულია", status: "ახალი" },
    ],
    asideTitle: "კითხვის თანმიმდევრობა",
    asideItems: ["ერთი წინადადების takeaway", "ვის ეხება კვლევა", "რა არის შეზღუდვა", "რა ვკითხოთ ექიმს"],
  },
  alerts: {
    eyebrow: "შეტყობინებები და განახლებები",
    title: "განახლებები გეუბნება რა შეიცვალა და რატომ არის ეს მნიშვნელოვანი ოჯახის შეხვედრისთვის.",
    subtitle: "შეტყობინებები არ ქმნის პანიკას; ისინი ალაგებს სიახლეებს პრიორიტეტის, სანდოობის და მოქმედების კონტექსტის მიხედვით.",
    icon: Bell,
    metrics: [
      { label: "ახალი კვლევები", value: "3", detail: "დღეს დაემთხვა", tone: "cyan" },
      { label: "კომენტარი", value: "1", detail: "ექსპერტის შენიშვნა", tone: "blue" },
      { label: "მიმდინარე განახლებები", value: "2", detail: "დაკვირვებაშია", tone: "amber" },
    ],
    cards: [
      { label: "პრიორიტეტი", title: "ყველა განახლება ერთნაირი არ არის", body: "სისტემა გამოყოფს ინფორმაციულ განახლებას გადაუდებელი კლინიკური კითხვისგან.", tone: "blue" },
      { label: "შეჯამება", title: "ოჯახისთვის მოკლე ახსნა", body: "განახლება იწერება ადამიანურად: რა მოხდა, რას ნიშნავს და რა არ უნდა შეიცვალოს თვითნებურად.", tone: "cyan" },
      { label: "მოქმედება", title: "შემდეგი კითხვა ან დაკვირვების სია", body: "თუ საჭირო გახდა, განახლება იქცევა ექიმთან კითხვად, არა დამოუკიდებელ ნაბიჯად.", tone: "emerald" },
    ],
    worklist: [
      { label: "ახალი კვლევის რეესტრი", value: "ასაკობრივი ფანჯარა მონიშნულია", status: "დაკვირვება" },
      { label: "ექსპერტის კომენტარი", value: "მხარდამჭერი თერაპია", status: "დაემატა" },
      { label: "პუბლიკაციის განახლება", value: "მტკიცებულების რუკას დაუკავშირდა", status: "ახალი" },
    ],
    asideTitle: "შეტყობინების დონეები",
    asideItems: ["ინფორმაციული", "review საჭირო", "ექიმთან კითხვა", "დახურული"],
  },
  resources: {
    eyebrow: "ოჯახის რესურსები",
    title: "ოჯახის რესურსები ამზადებს ვიზიტისთვის, საუბრისთვის და მშვიდი გადაწყვეტილებისთვის.",
    subtitle: "აქ თავმოყრილია მარტივი განმარტებები, კითხვების სიები და უსაფრთხოების საზღვრები, რომ კვლევა არ გადაიქცეს ზედმეტ შფოთვად.",
    icon: Library,
    metrics: [
      { label: "გზამკვლევები", value: "12", detail: "ოჯახისთვის უსაფრთხო", tone: "blue" },
      { label: "სიები", value: "7", detail: "ვიზიტისთვის მომზადება", tone: "emerald" },
      { label: "განმარტებები", value: "24", detail: "მარტივი ენა", tone: "cyan" },
    ],
    cards: [
      { label: "ვიზიტამდე", title: "ვიზიტამდე მოსამზადებელი კითხვები", body: "მოკლე ფორმატი: რა ვიცით, რა არ ვიცით, რას ვაკვირდებით და რას ვკითხავთ ექიმს.", tone: "emerald" },
      { label: "ვიზიტის შემდეგ", title: "რა დავაფიქსიროთ შეხვედრის შემდეგ", body: "შენიშვნები ინახება ქრონოლოგიაში და უკავშირდება შესაბამის ჰიპოთეზას ან თერაპიის დაკვირვების სიას.", tone: "blue" },
      { label: "მარტივი სიტყვები", title: "ტერმინების მარტივი ახსნა", body: "რთული სამედიცინო ტერმინი ითარგმნება ყოველდღიურ ენაზე, მაგრამ ტექნიკური მნიშვნელობა არ იკარგება.", tone: "cyan" },
    ],
    worklist: [
      { label: "ექიმთან ვიზიტის სია", value: "დასაბეჭდად მზად", status: "მზადაა" },
      { label: "მტკიცებულების სანდოობის გზამკვლევი", value: "ოჯახური განმარტება", status: "მზადაა" },
      { label: "თერაპიის საზღვრის შენიშვნა", value: "უსაფრთხოების ბარათი", status: "მნიშვნელოვანი" },
    ],
    asideTitle: "რესურსის წესი",
    asideItems: ["მოკლე", "გასაგები", "ექიმთან მიმართული", "არადიაგნოსტიკური"],
  },
  "how-it-works": {
    eyebrow: "როგორ მუშაობს",
    title: "სისტემა აგროვებს კვლევას, ალაგებს მტკიცებულებას და ამზადებს კითხვებს — გადაწყვეტილებას იღებს ექიმი.",
    subtitle: "ALEKSANDRA_BRAIN არის კვლევის მხარდამჭერი სივრცე. მისი როლია სურათის დალაგება, არა დიაგნოზის დასმა ან მკურნალობის შეცვლა.",
    icon: InfoIcon,
    metrics: [
      { label: "ნაბიჯი 1", value: "შეგროვება", detail: "წყაროები", tone: "blue" },
      { label: "ნაბიჯი 2", value: "შემოწმება", detail: "ჰიპოთეზა", tone: "violet" },
      { label: "ნაბიჯი 3", value: "კითხვა", detail: "ექიმთან კითხვა", tone: "emerald" },
    ],
    cards: [
      { label: "შეგროვება", title: "მონაცემი ერთდება მრავალი ადგილიდან", body: "პუბლიკაცია, რეესტრი, ოჯახის ჩანაწერი და ქრონოლოგიის მოვლენა სხვადასხვა ფენად ინახება.", tone: "blue" },
      { label: "დაკავშირება", title: "კავშირები აჩვენებს მნიშვნელობას", body: "წყარო უკავშირდება ჰიპოთეზას, თერაპიის დაკვირვების სიას ან ექიმთან დასასმელ კითხვას.", tone: "cyan" },
      { label: "განხილვა", title: "ფინალი არის საუბარი სპეციალისტთან", body: "ყველა პრაქტიკული მიგნება გადადის კლინიკურ განხილვაში და არა თვითნებურ მოქმედებაში.", tone: "emerald" },
    ],
    worklist: [
      { label: "კვლევის მიღება", value: "წყარო კლასიფიცირებულია", status: "ავტომატური + შემოწმება" },
      { label: "ოჯახური შეჯამება", value: "მარტივი ენა", status: "შექმნილია" },
      { label: "კლინიკური საზღვარი", value: "ექიმი წყვეტს", status: "ყოველთვის" },
    ],
    asideTitle: "სისტემის საზღვრები",
    asideItems: ["არ სვამს დიაგნოზს", "არ ნიშნავს დოზას", "არ ცვლის ექიმს", "ამზადებს კითხვებს"],
  },
  support: {
    eyebrow: "დახმარება და მხარდაჭერა",
    title: "დახმარების გვერდი აჩვენებს როგორ გამოიყენოს ოჯახმა და გუნდმა პლატფორმა მშვიდად.",
    subtitle: "აქ არის გამოყენების სცენარები: ახალი კვლევის ახსნა, ვიზიტისთვის მომზადება, ქრონოლოგიის შევსება და უსაფრთხოების საზღვრის გაგება.",
    icon: LifeBuoy,
    metrics: [
      { label: "სცენარები", value: "8", detail: "ხშირი პროცესები", tone: "blue" },
      { label: "გზამკვლევები", value: "5", detail: "ნაბიჯ-ნაბიჯ", tone: "cyan" },
      { label: "მხარდაჭერა", value: "ოჯახი", detail: "მარტივი ენა", tone: "emerald" },
    ],
    cards: [
      { label: "დაწყება", title: "დაიწყე მთავარი პანელიდან", body: "ნახე რა შეიცვალა დღეს, შემდეგ გადადი შესაბამის ჰიპოთეზაზე ან რესურსზე.", tone: "blue" },
      { label: "კითხვა", title: "გამოიყენე ასისტენტი როგორც განმმარტებელი", body: "ჰკითხე მარტივი ენით ახსნა, მაგრამ მკურნალობის გადაწყვეტილებისთვის მიმართე ექიმს.", tone: "cyan" },
      { label: "მომზადება", title: "შეხვედრისთვის შეკრიბე სამი კითხვა", body: "ყველაზე ეფექტურია მოკლე, კონკრეტული და წყაროსთან დაკავშირებული კითხვები.", tone: "emerald" },
    ],
    worklist: [
      { label: "ახალი მომხმარებლის გზა", value: "მთავარი პანელი", status: "ხელმისაწვდომია" },
      { label: "ექიმთან ვიზიტის მომზადება", value: "კითხვების შემქმნელი", status: "ხელმისაწვდომია" },
      { label: "კვლევის განმარტება", value: "სტატიის შეჯამება", status: "ხელმისაწვდომია" },
    ],
    asideTitle: "სწრაფი დახმარება",
    asideItems: ["ვერ იგებ ტერმინს? გახსენი პუბლიკაციები", "გინდა შემდეგი ნაბიჯი? ნახე დღეს", "გინდა საზღვარი? ნახე როგორ მუშაობს"],
  },
  settings: {
    eyebrow: "პარამეტრები",
    title: "პარამეტრები აკონტროლებს ხედვის რეჟიმს, ენას, შეხსენებებს და უსაფრთხოების ტექსტებს.",
    subtitle: "ეს გვერდი ამზადებს სისტემის ქცევის გამჭვირვალე კონტროლს, რათა ოჯახმა და კლინიკურმა გუნდმა ერთნაირად გაიგონ მოქმედების საზღვარი.",
    icon: Settings,
    metrics: [
      { label: "ენა", value: "KA / EN", detail: "გადართვა მზადაა", tone: "blue" },
      { label: "ხედვის რეჟიმი", value: "ოჯახი", detail: "ექიმის რეჟიმი ჩანს", tone: "cyan" },
      { label: "საზღვარი", value: "ჩართული", detail: "ყოველთვის ჩანს", tone: "emerald" },
    ],
    cards: [
      { label: "ენა", title: "ქართული და ინგლისური ხედვა", body: "ენის გადართვა ინარჩუნებს იგივე გვერდს და კონტექსტს.", tone: "blue" },
      { label: "რეჟიმი", title: "ოჯახის ხედვა და ექიმის რეჟიმი", body: "ოჯახის ტექსტი რჩება მარტივი; ექიმის ხედვა ინარჩუნებს ტექნიკურ დეტალს.", tone: "cyan" },
      { label: "უსაფრთხოება", title: "უსაფრთხოების შეხსენება მუდმივია", body: "სამედიცინო გადაწყვეტილების საზღვარი ჩანს გვერდით მენიუში და ასისტენტის პანელში.", tone: "emerald" },
    ],
    worklist: [
      { label: "ენის გადართვა", value: "ზედა კონტროლი", status: "აქტიურია" },
      { label: "უსაფრთხოების ბანერი", value: "მუდმივი", status: "აქტიურია" },
      { label: "აუდიტის პარამეტრი", value: "მიკვლევადი განახლებები", status: "აქტიურია" },
    ],
    asideTitle: "პარამეტრების მოდელი",
    asideItems: ["ქართული აღწერები", "ოჯახისთვის უსაფრთხო ფორმულირება", "ექიმის შემოწმების შეხსენება", "მიკვლევადი განახლებები"],
  },
  audit: {
    eyebrow: "აუდიტის ბილიკი",
    title: "აუდიტი აჩვენებს რა შეიცვალა, საიდან მოვიდა განახლება და რომელ გვერდს შეეხო.",
    subtitle: "გამჭვირვალობა მნიშვნელოვანია: ოჯახის ხედვა ხედავს არა მხოლოდ პასუხს, არამედ იმასაც, როგორ იქნა იგი მიღებული და გადამოწმებული.",
    icon: FileText,
    metrics: [
      { label: "მოვლენები", value: "219", detail: "მიკვლევადი", tone: "blue" },
      { label: "შემოწმებულია", value: "87%", detail: "ადამიანმა შეამოწმა", tone: "emerald" },
      { label: "ღია", value: "12", detail: "შემოწმებას ელოდება", tone: "amber" },
    ],
    cards: [
      { label: "მიკვლევა", title: "ყველა ცვლილებას აქვს ბილიკი", body: "ჩანაწერი აჩვენებს დროს, წყაროს, დაზარალებულ გვერდს და შემოწმების სტატუსს.", tone: "blue" },
      { label: "შემოწმება", title: "ადამიანური შემოწმება ცალკე ჩანს", body: "სისტემა განასხვავებს ავტომატურ მიღებას და ადამიანის მიერ დამტკიცებულ შეჯამებას.", tone: "emerald" },
      { label: "ნდობა", title: "ნდობა იქმნება პროცესით", body: "აუდიტის ბილიკი ეხმარება გუნდს დაინახოს რატომ გამოჩნდა კონკრეტული მიგნება.", tone: "cyan" },
    ],
    worklist: [
      { label: "წყარო დაემატა", value: "კავშირების სტატია", status: "შემოწმებულია" },
      { label: "ჰიპოთეზა განახლდა", value: "მიტოქონდრიული მხარდაჭერა", status: "მოლოდინშია" },
      { label: "კითხვა მომზადდა", value: "ექიმთან ვიზიტი", status: "დამტკიცებულია" },
    ],
    asideTitle: "აუდიტის ველები",
    asideItems: ["დრო", "წყარო", "გვერდი", "შემოწმების პასუხისმგებელი", "სტატუსი"],
  },
  knowledge: {
    eyebrow: "ცოდნის ბაზა",
    title: "ცოდნის ბაზა აერთიანებს მტკიცებულების რუკას, პუბლიკაციებს და ჰიპოთეზების კავშირებს.",
    subtitle: "ეს გვერდი შენარჩუნებულია არსებული არქიტექტურისთვის და ახლა მიჰყვება იგივე პორტალის დიზაინს, რაც მტკიცებულების რუკას.",
    icon: Network,
    metrics: [
      { label: "კვანძები", value: "318", detail: "ცოდნის გრაფი", tone: "blue" },
      { label: "კავშირები", value: "742", detail: "წყაროს ურთიერთობები", tone: "cyan" },
      { label: "ბრიფები", value: "64", detail: "ოჯახური შეჯამებები", tone: "emerald" },
    ],
    cards: [
      { label: "გრაფი", title: "კავშირები ერთ რუკაზე", body: "წყარო, ჰიპოთეზა, თერაპია და ქრონოლოგიის მოვლენა ერთმანეთთან ჩანს, რათა კონტექსტი არ დაიკარგოს.", tone: "blue" },
      { label: "ძიება", title: "კითხვის მიხედვით მოძებნა", body: "ოჯახი იწყებს შეკითხვით და ხედავს დაკავშირებულ წყაროებსა და შემდეგ ნაბიჯს.", tone: "cyan" },
      { label: "საზღვარი", title: "ცოდნა არ უდრის ინსტრუქციას", body: "ყველა დასკვნა რჩება განხილვის მასალად და არა სამედიცინო გადაწყვეტილებად.", tone: "emerald" },
    ],
    worklist: [
      { label: "გრაფის განახლება", value: "ყოველდღე", status: "აქტიურია" },
      { label: "წყაროების დაჯგუფება", value: "მტკიცებულების რუკა", status: "აქტიურია" },
      { label: "ოჯახური შეჯამებები", value: "მარტივი ენა", status: "აქტიურია" },
    ],
    asideTitle: "ცოდნის ფენები",
    asideItems: ["წყარო", "კავშირი", "ჰიპოთეზა", "კითხვა", "შემოწმება"],
  },
};

function contentFor(locale: Locale, key: PageKey): PageContent {
  if (locale === "ka") return georgianPages[key];
  const fallback = georgianPages[key];
  return {
    ...fallback,
    eyebrow: fallback.eyebrow,
    title: fallback.title,
    subtitle: fallback.subtitle,
  };
}

export function StatusChip({ children, tone = "blue" }: { children: ReactNode; tone?: Tone }) {
  return <span className={`inline-flex rounded-full px-3 py-1 text-[0.68rem] font-bold uppercase tracking-[0.18em] ring-1 ${toneClasses[tone].chip}`}>{children}</span>;
}

export function PortalPanel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-[1.35rem] border border-white/10 bg-slate-950/72 shadow-2xl shadow-black/30 backdrop-blur-xl ${className}`}>{children}</section>;
}

function useLivePulse(seed = 0) {
  const [tick, setTick] = useState(seed);

  useEffect(() => {
    const interval = window.setInterval(() => setTick((value) => value + 1), 2400);
    return () => window.clearInterval(interval);
  }, []);

  return tick;
}

function formatMetric(base: number, tick: number, drift = 5) {
  const wave = Math.sin((tick + base) / 2.7) * drift;
  const value = Math.max(0, Math.round(base + wave));
  return value.toLocaleString("en-US");
}

function Sparkline({ tone = "cyan", compact = false }: { tone?: Tone; compact?: boolean }) {
  const tick = useLivePulse(1);
  const points = useMemo(() => {
    return Array.from({ length: 18 }, (_, index) => {
      const x = (index / 17) * 100;
      const y = 58 - Math.sin((index + tick) / 2.1) * 18 - Math.cos(index / 2.8) * 9;
      return `${x},${Math.max(12, Math.min(86, y))}`;
    }).join(" ");
  }, [tick]);

  return (
    <svg viewBox="0 0 100 72" className={compact ? "h-10 w-24" : "h-16 w-full"} aria-hidden="true">
      <defs>
        <linearGradient id={`spark-${tone}`} x1="0" x2="1">
          <stop offset="0%" stopColor={tone === "violet" ? "#a78bfa" : tone === "emerald" ? "#34d399" : "#22d3ee"} stopOpacity="0.15" />
          <stop offset="100%" stopColor={tone === "blue" ? "#60a5fa" : "#22d3ee"} stopOpacity="0.85" />
        </linearGradient>
      </defs>
      <polyline fill="none" stroke={`url(#spark-${tone})`} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" points={points} />
      <polyline fill="none" stroke="rgba(255,255,255,0.16)" strokeWidth="1" points="0,58 100,58" />
    </svg>
  );
}

function MetricTile({ label, base, suffix = "", detail, tone, icon: Icon, drift = 4, liveLabel = "live" }: { label: string; base: number; suffix?: string; detail: string; tone: Tone; icon: LucideIcon; drift?: number; liveLabel?: string }) {
  const tick = useLivePulse(base);
  return (
    <PortalPanel className={`group overflow-hidden bg-gradient-to-br ${toneClasses[tone].card} p-4 ring-1 ${toneClasses[tone].ring} transition duration-500 hover:-translate-y-1 hover:border-white/20 hover:shadow-2xl ${toneClasses[tone].glow}`}>
      <div className="flex items-start justify-between gap-3">
        <div className={`grid h-10 w-10 place-items-center rounded-2xl ring-1 ${toneClasses[tone].icon}`}><Icon className="h-5 w-5" /></div>
        <Sparkline tone={tone} compact />
      </div>
      <p className="mt-4 text-[0.67rem] font-bold uppercase tracking-[0.2em] text-slate-400">{label}</p>
      <div className="mt-2 flex items-end gap-2">
        <p className="text-3xl font-semibold tracking-[-0.05em] text-white">{formatMetric(base, tick, drift)}{suffix}</p>
        <span className={`pb-1 text-xs font-semibold ${toneClasses[tone].text}`}>{liveLabel}</span>
      </div>
      <p className="mt-1 text-xs leading-5 text-slate-400">{detail}</p>
    </PortalPanel>
  );
}

function NeuralField() {
  const nodes = [
    [20, 38, "cyan"], [34, 20, "blue"], [48, 44, "violet"], [62, 26, "cyan"], [78, 42, "emerald"], [58, 62, "blue"], [30, 64, "violet"], [82, 18, "cyan"],
  ] as const;
  return (
    <div className="relative min-h-[15rem] overflow-hidden rounded-[1.35rem] border border-cyan-300/10 bg-[radial-gradient(circle_at_65%_32%,rgba(34,211,238,0.22),transparent_30%),radial-gradient(circle_at_78%_42%,rgba(168,85,247,0.22),transparent_28%),linear-gradient(135deg,rgba(15,23,42,0.96),rgba(2,6,23,0.92))] p-5">
      <div className="absolute inset-x-0 top-1/2 h-px bg-gradient-to-r from-transparent via-cyan-300/60 to-transparent shadow-[0_0_28px_rgba(34,211,238,0.7)]" />
      <div className="absolute left-[24%] top-[42%] h-20 w-44 rounded-full bg-cyan-400/15 blur-2xl" />
      <div className="absolute right-[12%] top-[18%] h-28 w-56 rounded-full bg-violet-500/15 blur-2xl" />
      <svg viewBox="0 0 100 78" className="absolute inset-0 h-full w-full opacity-85" aria-hidden="true">
        {nodes.slice(0, -1).map(([x, y], index) => {
          const [nextX, nextY] = nodes[index + 1];
          return <line key={`${x}-${y}`} x1={x} y1={y} x2={nextX} y2={nextY} stroke="rgba(125,211,252,0.28)" strokeWidth="0.45" />;
        })}
        {nodes.map(([x, y, tone], index) => (
          <g key={`${x}-${y}-${tone}`} className="animate-pulse" style={{ animationDelay: `${index * 180}ms` }}>
            <circle cx={x} cy={y} r="2.9" fill={tone === "violet" ? "#a78bfa" : tone === "emerald" ? "#34d399" : "#38bdf8"} opacity="0.9" />
            <circle cx={x} cy={y} r="7" fill="none" stroke="rgba(255,255,255,0.12)" />
          </g>
        ))}
      </svg>
      <div className="relative z-10 flex h-full flex-col justify-between gap-12">
        <div>
          <StatusChip tone="cyan">ცოცხალი კვლევის ტვინი</StatusChip>
          <h2 className="mt-4 max-w-2xl text-3xl font-semibold tracking-[0.22em] text-white md:text-4xl">ALEKSANDRA_BRAIN</h2>
          <p className="mt-3 max-w-xl text-sm leading-6 text-slate-300">ცოცხალი კვლევითი სისტემა, სადაც წყაროები, ჰიპოთეზები და თერაპიის კანდიდატები რეალურ დროში ერთიანდება.</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          {["მტკიცებულების გრაფი", "ჰიპოთეზების ძრავი", "კლინიკური საზღვარი"].map((label) => (
            <div key={label} className="rounded-2xl border border-white/10 bg-black/20 px-3 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-cyan-100 backdrop-blur">{label}</div>
          ))}
        </div>
      </div>
    </div>
  );
}

function PipelineView() {
  const stages = [
    { icon: Network, label: "მტკიცებულების რუკა", value: "12,842", detail: "წყაროები", tone: "blue" as Tone },
    { icon: Brain, label: "ჰიპოთეზების ძრავი", value: "256", detail: "კანდიდატი", tone: "violet" as Tone },
    { icon: CheckCircle2, label: "ვალიდაცია", value: "173", detail: "მხარდაჭერილი", tone: "cyan" as Tone },
    { icon: FlaskConical, label: "თერაპიის კანდიდატები", value: "28", detail: "ნაკადი", tone: "emerald" as Tone },
    { icon: UsersRound, label: "კლინიკური გავლენა", value: "მიმდინარე", detail: "სწავლა", tone: "blue" as Tone },
  ];
  return (
    <PortalPanel className="overflow-hidden p-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-[-0.03em] text-white">მტკიცებულება → ჰიპოთეზა → თერაპიის ნაკადი</h2>
          <p className="text-xs text-slate-400">ავტომატურად განახლებადი ეტაპები; კლინიკური მოქმედება მხოლოდ ექიმთან.</p>
        </div>
        <StatusChip tone="cyan">ნაკადის მოდელი</StatusChip>
      </div>
      <div className="relative mt-5 grid gap-3 lg:grid-cols-5">
        <div className="pointer-events-none absolute left-4 right-4 top-12 hidden h-px bg-gradient-to-r from-cyan-400/0 via-cyan-300/70 to-violet-400/0 shadow-[0_0_18px_rgba(34,211,238,0.7)] lg:block" />
        {stages.map((stage, index) => {
          const Icon = stage.icon;
          return (
            <div key={stage.label} className="relative overflow-hidden rounded-2xl border border-white/10 bg-slate-900/60 p-4 transition duration-500 hover:-translate-y-1 hover:border-cyan-300/30">
              <div className={`grid h-14 w-14 place-items-center rounded-full ring-1 ${toneClasses[stage.tone].icon} shadow-2xl ${toneClasses[stage.tone].glow}`}>
                <Icon className="h-7 w-7" />
              </div>
              <p className="mt-4 text-[0.65rem] font-bold uppercase tracking-[0.18em] text-slate-500">{index + 1}. {stage.label}</p>
              <p className="mt-2 text-2xl font-semibold tracking-[-0.05em] text-white">{stage.value}</p>
              <p className="text-xs text-slate-400">{stage.detail}</p>
            </div>
          );
        })}
      </div>
    </PortalPanel>
  );
}

function DonutChart({ value, tone = "cyan", label }: { value: number; tone?: Tone; label: string }) {
  const color = tone === "violet" ? "#a78bfa" : tone === "emerald" ? "#34d399" : tone === "amber" ? "#fbbf24" : "#22d3ee";
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.035] p-4">
      <div className="relative h-24 w-24 shrink-0 rounded-full" style={{ background: `conic-gradient(${color} ${value * 3.6}deg, rgba(255,255,255,0.08) 0deg)` }}>
        <div className="absolute inset-3 grid place-items-center rounded-full bg-slate-950 text-center shadow-inner shadow-black/50">
          <span className="text-xl font-semibold text-white">{value}%</span>
        </div>
      </div>
      <div>
        <p className="text-sm font-semibold text-white">{label}</p>
        <p className="mt-1 text-xs leading-5 text-slate-400">დღიურად ახლდება · წყაროს სანდოობით შეწონილი</p>
      </div>
    </div>
  );
}

function DomainBars() {
  const rows = [
    ["ნეიროანთება", 26, "cyan"],
    ["მიტოქონდრიული მხარდაჭერა", 21, "emerald"],
    ["ექსაიტოტოქსიკურობა", 18, "blue"],
    ["ანგიოგენეზი", 13, "violet"],
    ["ნეიროდაცვა", 12, "amber"],
  ] as const;
  return (
    <PortalPanel className="p-5">
      <h2 className="text-base font-semibold text-white">კვლევის წამყვანი დომენები</h2>
      <div className="mt-4 space-y-3">
        {rows.map(([label, value, tone]) => (
          <div key={label}>
            <div className="flex justify-between text-xs"><span className="text-slate-300">{label}</span><span className={toneClasses[tone].text}>{value}%</span></div>
            <div className="mt-1 h-2 overflow-hidden rounded-full bg-white/8">
              <div className={`h-full rounded-full bg-gradient-to-r ${tone === "violet" ? "from-violet-400 to-cyan-300" : tone === "emerald" ? "from-emerald-400 to-cyan-300" : tone === "amber" ? "from-amber-300 to-cyan-300" : "from-blue-400 to-cyan-300"}`} style={{ width: `${value * 3}%` }} />
            </div>
          </div>
        ))}
      </div>
    </PortalPanel>
  );
}

export function PortalHomeDashboard({ locale }: { locale: Locale }) {
  const isKa = locale === "ka";
  const tick = useLivePulse(12);
  const metricSeed = [12842, 173, 28, 14, 36];

  return (
    <div className="space-y-4">
      <NeuralField />

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <MetricTile label={isKa ? "მტკიცებულების ელემენტები" : "Evidence items"} base={metricSeed[0]} detail={isKa ? "რეცენზირებული + რეალური მონაცემი" : "peer-reviewed + real-world"} tone="cyan" icon={BookOpen} drift={18} liveLabel={isKa ? "ცოცხალი" : "live"} />
        <MetricTile label={isKa ? "ვალიდირებული ჰიპოთეზები" : "Validated hypotheses"} base={metricSeed[1]} detail={isKa ? "დომენთაშორისი მხარდაჭერა" : "cross-domain support"} tone="violet" icon={FlaskConical} drift={3} liveLabel={isKa ? "ცოცხალი" : "live"} />
        <MetricTile label={isKa ? "თერაპიის კანდიდატები" : "Therapy candidates"} base={metricSeed[2]} detail={isKa ? "შეფასების ნაკადი" : "evaluation pipeline"} tone="emerald" icon={Activity} drift={2} liveLabel={isKa ? "ცოცხალი" : "live"} />
        <MetricTile label={isKa ? "აქტიური კვლევები" : "Active studies"} base={metricSeed[3]} detail={isKa ? "მრავალცენტრიანი კვლევები" : "multi-center studies"} tone="blue" icon={UsersRound} drift={1} liveLabel={isKa ? "ცოცხალი" : "live"} />
        <MetricTile label={isKa ? "მონაცემთა პარტნიორები" : "Data partners"} base={metricSeed[4]} detail={isKa ? "დაკავშირებული ინსტიტუციები" : "institutions connected"} tone="cyan" icon={Database} drift={2} liveLabel={isKa ? "ცოცხალი" : "live"} />
      </section>

      <PipelineView />

      <section className="grid gap-4 xl:grid-cols-[0.95fr_0.95fr_1.1fr]">
        <PortalPanel className="p-5">
          <h2 className="text-base font-semibold text-white">მტკიცებულება წყაროს მიხედვით</h2>
          <div className="mt-4 grid gap-3">
            <DonutChart value={44} tone="blue" label="რეცენზირებული სტატიები" />
            <DonutChart value={24} tone="cyan" label="კლინიკური რეესტრები" />
          </div>
        </PortalPanel>
        <PortalPanel className="p-5">
          <h2 className="text-base font-semibold text-white">ჰიპოთეზების ვალიდაციის სტატუსი</h2>
          <div className="mt-4 grid gap-3">
            <DonutChart value={28} tone="emerald" label="ძლიერად მხარდაჭერილი" />
            <DonutChart value={41} tone="violet" label="საშუალოდ მხარდაჭერილი" />
          </div>
        </PortalPanel>
        <DomainBars />
      </section>

      <ClinicalTimeline />

      <div className="sr-only" aria-live="polite">ცოცხალი dashboard-ის პულსი {tick}</div>
    </div>
  );
}

function ClinicalTimeline() {
  const steps = [
    ["2018", "პლატფორმა დაიწყო"], ["2019–2020", "რეესტრი შეიქმნა"], ["2021", "პირველი მტკიცებულებითი ეტაპი"], ["2022", "ჰიპოთეზების ძრავი გაეშვა"], ["2023", "პირველი ვალიდირებული ჰიპოთეზები"], ["2024", "თერაპიის ნაკადი გაფართოვდა"], ["2025+", "კლინიკური გავლენის სწავლა"],
  ];
  return (
    <PortalPanel className="overflow-hidden p-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-white">კლინიკური კვლევის დროითი ხაზი</h2>
          <p className="text-xs text-slate-400">ძირითადი ეტაპები ცოცხალ კვლევით პროცესში</p>
        </div>
        <StatusChip tone="blue">ავტო-სინქრონიზებული</StatusChip>
      </div>
      <div className="relative mt-7 grid gap-4 md:grid-cols-7">
        <div className="absolute left-0 right-0 top-4 hidden h-px bg-gradient-to-r from-cyan-300 via-blue-400 to-violet-400 md:block" />
        {steps.map(([year, label], index) => (
          <div key={year} className="relative text-center">
            <div className="mx-auto grid h-8 w-8 place-items-center rounded-full border border-cyan-200/60 bg-cyan-400/20 text-cyan-100 shadow-[0_0_18px_rgba(34,211,238,0.35)]">
              <CheckCircle2 className="h-4 w-4" />
            </div>
            <p className="mt-3 text-xs font-semibold text-slate-200">{year}</p>
            <p className="mt-1 text-[0.68rem] leading-4 text-slate-500">{label}</p>
          </div>
        ))}
      </div>
    </PortalPanel>
  );
}

function MiniMatrix({ items }: { items: WorkItem[] }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-white/10">
      {items.map((item, index) => (
        <div key={`${item.label}-${index}`} className={`grid gap-2 px-4 py-3 text-sm sm:grid-cols-[1fr_1.2fr_0.55fr] ${index % 2 === 0 ? "bg-white/[0.035]" : "bg-cyan-300/[0.025]"}`}>
          <span className="font-semibold text-slate-100">{item.label}</span>
          <span className="text-slate-400">{item.value}</span>
          <span className="font-semibold text-cyan-200">{item.status}</span>
        </div>
      ))}
    </div>
  );
}

export function PortalTopicPage({ locale, pageKey }: { locale: Locale; pageKey: PageKey }) {
  const page = contentFor(locale, pageKey);
  const Icon = page.icon;
  const numeric = page.metrics.map((metric, index) => {
    const parsed = Number(metric.value.replace(/[^0-9]/g, ""));
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 10 + index * 7;
  });

  return (
    <div className="space-y-4">
      <PortalPanel className="overflow-hidden p-0">
        <div className="relative grid gap-6 p-5 lg:grid-cols-[1fr_18rem] lg:p-6">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_12%_18%,rgba(34,211,238,0.12),transparent_34%),radial-gradient(circle_at_88%_0%,rgba(139,92,246,0.14),transparent_32%)]" />
          <div className="relative z-10">
            <StatusChip tone="cyan">{page.eyebrow}</StatusChip>
            <h1 className="mt-4 max-w-5xl text-[clamp(1.85rem,3.6vw,3.6rem)] font-semibold leading-[1.02] tracking-[-0.055em] text-white">{page.title}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400">{page.subtitle}</p>
          </div>
          <div className="relative z-10 grid min-h-44 place-items-center rounded-[1.25rem] border border-white/10 bg-black/20">
            <div className="absolute h-28 w-28 rounded-full bg-cyan-400/15 blur-2xl" />
            <div className="relative grid h-24 w-24 place-items-center rounded-[2rem] border border-cyan-200/30 bg-cyan-400/10 text-cyan-100 shadow-[0_0_40px_rgba(34,211,238,0.22)]">
              <Icon className="h-11 w-11" />
            </div>
          </div>
        </div>
      </PortalPanel>

      <section className="grid gap-3 md:grid-cols-3 xl:grid-cols-4">
        {page.metrics.map((metric, index) => (
          <MetricTile key={metric.label} label={metric.label} base={numeric[index]} detail={metric.detail} tone={metric.tone} icon={index === 0 ? BarChart3 : index === 1 ? TrendingUp : Gauge} drift={index + 1} liveLabel={locale === "ka" ? "ცოცხალი" : "live"} />
        ))}
      </section>

      <div className="grid gap-4 xl:grid-cols-[1.25fr_0.9fr]">
        <PortalPanel className="p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold tracking-[-0.03em] text-white">ოპერაციული მატრიცა</h2>
              <p className="text-xs text-slate-500">კონკრეტული ელემენტები, სტატუსები და შემდეგი დამუშავების ეტაპი.</p>
            </div>
            <StatusChip tone="slate">ცოცხალი გვერდი</StatusChip>
          </div>
          <div className="mt-4"><MiniMatrix items={page.worklist} /></div>
        </PortalPanel>

        <PortalPanel className="p-5">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-cyan-200" />
            <h2 className="text-lg font-semibold tracking-[-0.03em] text-white">{page.asideTitle}</h2>
          </div>
          <div className="mt-4 space-y-2">
            {page.asideItems.map((item) => (
              <div key={item} className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.035] px-3 py-3 text-sm text-slate-300 transition hover:border-cyan-300/25 hover:bg-cyan-300/[0.05]">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-300" />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </PortalPanel>
      </div>

      <section className="grid gap-4 xl:grid-cols-3">
        {page.cards.map((card, index) => {
          const tone = card.tone || "blue";
          return (
            <PortalPanel key={card.title} className={`overflow-hidden bg-gradient-to-br ${toneClasses[tone].card} p-5 ring-1 ${toneClasses[tone].ring}`}>
              <div className="flex items-center justify-between gap-3">
                <StatusChip tone={tone}>{card.label}</StatusChip>
                <Sparkline tone={tone} compact />
              </div>
              <h2 className="mt-4 text-lg font-semibold tracking-[-0.035em] text-white">{card.title}</h2>
              <p className="mt-2 line-clamp-3 text-sm leading-6 text-slate-400">{card.body}</p>
              <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/8">
                <div className="h-full rounded-full bg-gradient-to-r from-cyan-300 to-violet-300" style={{ width: `${Math.min(92, 42 + index * 17)}%` }} />
              </div>
            </PortalPanel>
          );
        })}
      </section>
    </div>
  );
}
