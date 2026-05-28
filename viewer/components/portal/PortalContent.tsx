import type { ReactNode } from "react";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  ArrowRight,
  Bell,
  BookOpen,
  Brain,
  CalendarClock,
  CheckCircle2,
  Database,
  FileText,
  FlaskConical,
  Heart,
  Library,
  LifeBuoy,
  Network,
  Settings,
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

const toneClasses: Record<Tone, { chip: string; card: string; ring: string; icon: string }> = {
  blue: { chip: "bg-blue-50 text-blue-800 ring-blue-100", card: "from-blue-50 to-white", ring: "ring-blue-100", icon: "bg-blue-600 text-white" },
  cyan: { chip: "bg-cyan-50 text-cyan-800 ring-cyan-100", card: "from-cyan-50 to-white", ring: "ring-cyan-100", icon: "bg-cyan-600 text-white" },
  emerald: { chip: "bg-emerald-50 text-emerald-800 ring-emerald-100", card: "from-emerald-50 to-white", ring: "ring-emerald-100", icon: "bg-emerald-600 text-white" },
  violet: { chip: "bg-violet-50 text-violet-800 ring-violet-100", card: "from-violet-50 to-white", ring: "ring-violet-100", icon: "bg-violet-600 text-white" },
  amber: { chip: "bg-amber-50 text-amber-800 ring-amber-100", card: "from-amber-50 to-white", ring: "ring-amber-100", icon: "bg-amber-500 text-white" },
  rose: { chip: "bg-rose-50 text-rose-800 ring-rose-100", card: "from-rose-50 to-white", ring: "ring-rose-100", icon: "bg-rose-600 text-white" },
  slate: { chip: "bg-slate-100 text-slate-700 ring-slate-200", card: "from-slate-50 to-white", ring: "ring-slate-200", icon: "bg-slate-800 text-white" },
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
  return <span className={`inline-flex rounded-full px-3 py-1 text-xs font-bold ring-1 ${toneClasses[tone].chip}`}>{children}</span>;
}

export function PortalPanel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-[1.75rem] border border-slate-200 bg-white/90 shadow-xl shadow-slate-950/[0.045] backdrop-blur ${className}`}>{children}</section>;
}

export function PortalHomeDashboard({ locale }: { locale: Locale }) {
  const isKa = locale === "ka";
  const cards = [
    { icon: Bell, title: "რა შეიცვალა დღეს", body: "ახალი კვლევები, ექსპერტის კომენტარი და მიმდინარე დაკვირვებები ერთ მშვიდ შეჯამებაში.", tone: "blue" as Tone, rows: ["3 ახალი კვლევა დაემთხვა", "1 ექსპერტის კომენტარი დაემატა", "2 მიმდინარე განახლება"] },
    { icon: BookOpen, title: "მტკიცებულება განხილვაშია", body: "წყაროები, რომლებსაც გუნდი ახლა უფრო ახლოს უყურებს.", tone: "emerald" as Tone, rows: ["ტვინის კავშირები", "ჩარევის დრო", "მხარდამჭერი თერაპიები"] },
    { icon: Heart, title: "ჰკითხე ექიმს", body: "მომდევნო საუბრისთვის მომზადებული, არადიაგნოსტიკური კითხვები.", tone: "amber" as Tone, rows: ["რა არის მთავარი პრიორიტეტი?", "რა უნდა განვიხილოთ?", "როდის გადავხედოთ გეგმას?"] },
    { icon: Stethoscope, title: "თერაპიის დაკვირვების სია", body: "შესაძლო მიდგომები მტკიცებულების სიმწიფით და კლინიკური საზღვრით.", tone: "violet" as Tone, rows: ["კოგნიტური მხარდაჭერა", "მოტორული განვითარება", "ნეირომოდულაციის კვლევა"] },
  ];

  return (
    <div className="space-y-5">
      <PortalPanel className="overflow-hidden p-0">
        <div className="grid gap-6 p-6 lg:grid-cols-[1.3fr_0.9fr] lg:p-8">
          <div>
            <StatusChip tone="cyan">{isKa ? "ოჯახისთვის უსაფრთხო კვლევის სივრცე" : "Family-safe research workspace"}</StatusChip>
            <h1 className="mt-5 max-w-4xl text-[clamp(2rem,3.7vw,3.85rem)] font-semibold leading-[1.04] tracking-[-0.055em] text-slate-950">
              {isKa ? "თქვენ მარტო არ ხართ. ერთად ვალაგებთ იმას, რაც ვიცით." : "You are not alone. We make sense of what we know—together."}
            </h1>
            <p className="mt-5 max-w-3xl text-base leading-8 text-slate-600">
              {isKa
                ? "ALEKSANDRA_BRAIN აკავშირებს კვლევას, ოჯახის დაკვირვებებს და ექიმთან გადასამოწმებელ კითხვებს, რათა საუბარი იყოს მშვიდი, ზუსტი და უსაფრთხო."
                : "ALEKSANDRA_BRAIN connects research, family observations, and clinician-reviewed questions for safer conversations."}
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link href={`/${locale}/dashboard`} className="rounded-full bg-slate-950 px-5 py-3 text-sm font-bold text-white shadow-xl shadow-slate-950/15 transition hover:-translate-y-0.5">
                {isKa ? "მართვის პანელი" : "Open command center"}
              </Link>
              <Link href={`/${locale}/how-it-works`} className="rounded-full border border-slate-200 bg-white px-5 py-3 text-sm font-bold text-slate-800 transition hover:-translate-y-0.5 hover:border-cyan-300">
                {isKa ? "როგორ მუშაობს" : "How it works"}
              </Link>
            </div>
          </div>
          <div className="relative min-h-72 overflow-hidden rounded-[1.75rem] border border-cyan-100 bg-gradient-to-br from-cyan-50 via-white to-blue-50 p-6">
            <div className="absolute -right-8 top-8 h-44 w-44 rounded-full bg-cyan-300/30 blur-3xl" />
            <div className="absolute left-8 top-14 h-24 w-24 rounded-full border border-cyan-200" />
            <div className="absolute right-16 top-8 h-16 w-16 rounded-full border border-blue-200" />
            <div className="relative z-10 grid h-full place-items-center">
              <div className="grid grid-cols-3 gap-5 text-center">
                {[
[BookOpen, isKa ? "მტკიცებულება" : "Evidence"],
	                  [UsersRound, isKa ? "ზრუნვის გუნდი" : "Care team"],
	                  [FlaskConical, isKa ? "კვლევა" : "Research"],
                ].map(([Icon, label], index) => {
                  const IconComponent = Icon as LucideIcon;
                  return (
                    <div key={String(label)} className={`grid place-items-center rounded-full ${index === 1 ? "h-24 w-24 bg-emerald-500 text-white" : "h-20 w-20 bg-white text-blue-700"} shadow-xl shadow-blue-900/10 ring-1 ring-blue-100`}>
                      <IconComponent className="h-9 w-9" />
                      <span className="sr-only">{String(label)}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </PortalPanel>

      <JourneyStrip />

      <section className="grid gap-4 xl:grid-cols-4">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <PortalPanel key={card.title} className={`overflow-hidden bg-gradient-to-br ${toneClasses[card.tone].card} p-5 ring-1 ${toneClasses[card.tone].ring}`}>
              <div className="flex items-start justify-between gap-3">
                <div className={`grid h-11 w-11 place-items-center rounded-2xl ${toneClasses[card.tone].icon}`}>
                  <Icon className="h-5 w-5" />
                </div>
                <StatusChip tone={card.tone}>{isKa ? "განხილვა" : "review"}</StatusChip>
              </div>
              <h2 className="mt-4 text-lg font-bold tracking-[-0.03em] text-slate-950">{card.title}</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">{card.body}</p>
              <div className="mt-4 space-y-2">
                {card.rows.map((row) => (
                  <div key={row} className="flex items-center justify-between rounded-2xl border border-white/70 bg-white/72 px-3 py-3 text-sm text-slate-700">
                    <span>{row}</span>
                    <ArrowRight className="h-4 w-4 text-slate-400" />
                  </div>
                ))}
              </div>
            </PortalPanel>
          );
        })}
      </section>

      <PortalPanel className="p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-start gap-4">
            <span className="grid h-14 w-14 shrink-0 place-items-center rounded-3xl bg-blue-600 text-white shadow-lg shadow-blue-600/20"><UsersRound className="h-7 w-7" /></span>
            <div>
              <h2 className="text-2xl font-bold tracking-[-0.04em] text-slate-950">{isKa ? "კვლევის მხარდაჭერა — მკურნალობას ექიმები წყვეტენ" : "Research support — doctors decide treatment"}</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{isKa ? "ALEKSANDRA_BRAIN აგროვებს ცოდნას. თქვენი ზრუნვის გუნდი ამატებს კონტექსტს, გამოცდილებას და საბოლოო კლინიკურ გადაწყვეტილებას." : "ALEKSANDRA_BRAIN organizes knowledge. Your care team adds context, experience, and the final clinical decision."}</p>
            </div>
          </div>
          <Link href={`/${locale}/resources`} className="rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-bold text-slate-800 transition hover:border-blue-300 hover:bg-blue-50">
            რესურსების ნახვა
          </Link>
        </div>
      </PortalPanel>
    </div>
  );
}

function JourneyStrip() {
  const steps = [
    ["ინფორმაცია შეგროვდა", "მიმდინარე", CheckCircle2, "blue"],
["მტკიცებულება შეგროვდა", "მიმდინარეობს", FileText, "cyan"],
	    ["მტკიცებულება განხილვაშია", "ახლა", Network, "blue"],
	    ["კითხვები ექიმისთვის", "შემდეგი", Heart, "amber"],
	    ["საუბარი ზრუნვის გუნდთან", "შემდეგი", UsersRound, "slate"],
	    ["გეგმა ერთად", "მიმდინარე", ShieldCheck, "emerald"],
  ] as const;
  return (
    <PortalPanel className="p-5">
      <h2 className="text-base font-bold text-slate-950">სად ვართ კვლევისა და ზრუნვის მხარდაჭერის გზაზე</h2>
      <div className="mt-5 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        {steps.map(([title, status, Icon, tone]) => (
          <div key={title} className="relative rounded-2xl border border-slate-100 bg-slate-50/75 p-4 text-center">
            <div className={`mx-auto grid h-11 w-11 place-items-center rounded-full ${toneClasses[tone].icon}`}><Icon className="h-5 w-5" /></div>
            <p className="mt-3 text-sm font-bold leading-5 text-slate-800">{title}</p>
            <p className="mt-1 text-xs text-slate-500">{status}</p>
          </div>
        ))}
      </div>
    </PortalPanel>
  );
}

export function PortalTopicPage({ locale, pageKey }: { locale: Locale; pageKey: PageKey }) {
  const page = contentFor(locale, pageKey);
  const Icon = page.icon;
  return (
    <div className="space-y-5">
      <PortalPanel className="overflow-hidden p-0">
        <div className="relative p-6 lg:p-8">
          <div className="absolute right-0 top-0 h-56 w-56 rounded-full bg-cyan-200/35 blur-3xl" />
          <div className="relative z-10 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-4xl">
              <StatusChip tone="cyan">{page.eyebrow}</StatusChip>
              <h1 className="mt-4 text-[clamp(2rem,4vw,4rem)] font-semibold leading-[1.02] tracking-[-0.055em] text-slate-950">{page.title}</h1>
              <p className="mt-4 max-w-3xl text-base leading-8 text-slate-600">{page.subtitle}</p>
            </div>
            <div className="grid h-24 w-24 shrink-0 place-items-center rounded-[2rem] bg-slate-950 text-white shadow-2xl shadow-slate-950/20">
              <Icon className="h-11 w-11" />
            </div>
          </div>
        </div>
      </PortalPanel>

      <section className="grid gap-4 md:grid-cols-3 xl:grid-cols-4">
        {page.metrics.map((metric) => (
          <PortalPanel key={metric.label} className={`bg-gradient-to-br ${toneClasses[metric.tone].card} p-5 ring-1 ${toneClasses[metric.tone].ring}`}>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">{metric.label}</p>
            <p className="mt-3 text-4xl font-semibold tracking-[-0.05em] text-slate-950">{metric.value}</p>
            <p className="mt-2 text-sm text-slate-500">{metric.detail}</p>
          </PortalPanel>
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        {page.cards.map((card) => (
          <PortalPanel key={card.title} className={`bg-gradient-to-br ${toneClasses[card.tone || "blue"].card} p-5 ring-1 ${toneClasses[card.tone || "blue"].ring}`}>
            <StatusChip tone={card.tone || "blue"}>{card.label}</StatusChip>
            <h2 className="mt-4 text-xl font-bold tracking-[-0.035em] text-slate-950">{card.title}</h2>
            <p className="mt-3 text-sm leading-7 text-slate-600">{card.body}</p>
          </PortalPanel>
        ))}
      </section>

      <div className="grid gap-4 xl:grid-cols-[1.5fr_0.8fr]">
        <PortalPanel className="p-5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-xl font-bold tracking-[-0.035em] text-slate-950">სამუშაო სია</h2>
            <StatusChip tone="slate">{locale === "ka" ? "ცოცხალი გვერდი" : "live route"}</StatusChip>
          </div>
          <div className="mt-4 overflow-hidden rounded-2xl border border-slate-100">
            {page.worklist.map((item, index) => (
              <div key={item.label} className={`grid gap-2 px-4 py-4 text-sm sm:grid-cols-[1fr_1.2fr_0.7fr] ${index % 2 === 0 ? "bg-white" : "bg-slate-50/70"}`}>
                <span className="font-bold text-slate-900">{item.label}</span>
                <span className="text-slate-600">{item.value}</span>
                <span className="font-semibold text-blue-700">{item.status}</span>
              </div>
            ))}
          </div>
        </PortalPanel>

        <PortalPanel className="p-5">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-blue-700" />
            <h2 className="text-lg font-bold tracking-[-0.03em] text-slate-950">{page.asideTitle}</h2>
          </div>
          <div className="mt-4 space-y-2">
            {page.asideItems.map((item) => (
              <div key={item} className="flex items-center gap-3 rounded-2xl border border-slate-100 bg-slate-50 px-3 py-3 text-sm text-slate-700">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </PortalPanel>
      </div>
    </div>
  );
}
