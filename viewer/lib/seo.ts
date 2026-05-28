import type { Metadata } from "next";

export type Locale = "en" | "ka";

export const SITE_URL = "https://viewer-sigma-two.vercel.app";
export const BRAND = "ALEKSANDRA_BRAIN";
export const DEFAULT_OG_IMAGE = "/og-image.png";

export type SeoRoute =
  | "home"
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

type RouteCopy = {
  path: string;
  title: Record<Locale, string>;
  description: string;
};

export const routeSeo: Record<SeoRoute, RouteCopy> = {
  home: {
    path: "/",
    title: {
      ka: "ALEKSANDRA_BRAIN — ბავშვთა HIE კვლევის სამუშაო სივრცე",
      en: "ALEKSANDRA_BRAIN — Pediatric HIE Research Workspace",
    },
    description: "ოჯახისა და კლინიკური გუნდისთვის შექმნილი სამუშაო სივრცე, სადაც მხოლოდ წყაროთი დადასტურებული HIE მონაცემი ჩანს; მონაცემის არქონისას გვერდი ამას პირდაპირ აღნიშნავს.",
  },
  today: {
    path: "/today",
    title: { ka: "დღეს | ALEKSANDRA_BRAIN", en: "Today | ALEKSANDRA_BRAIN" },
    description: "დღევანდელი კლინიკური ფოკუსის სივრცე, რომელიც შეჯამებას მხოლოდ არსებული ჩანაწერის საფუძველზე აჩვენებს; სხვა შემთხვევაში წერს, რომ მონაცემი არ არის.",
  },
  dashboard: {
    path: "/dashboard",
    title: { ka: "მართვის პანელი | ALEKSANDRA_BRAIN", en: "Clinical Dashboard | ALEKSANDRA_BRAIN" },
    description: "კლინიკური მართვის პანელი აჩვენებს მხოლოდ რეალურად ატვირთულ HIE ჩანაწერებს, წყაროებსა და ექიმთან გადასამოწმებელ საკითხებს.",
  },
  brain: {
    path: "/brain",
    title: { ka: "ციფრული ტვინის ლაბორატორია | ALEKSANDRA_BRAIN", en: "Digital Twin Brain Lab | ALEKSANDRA_BRAIN" },
    description: "ციფრული ტვინის ლაბორატორია MRI-სა და კლინიკურ ფენებს აჩვენებს მხოლოდ მაშინ, როცა შესაბამისი დადასტურებული მონაცემი არსებობს.",
  },
  hypotheses: {
    path: "/hypotheses",
    title: { ka: "ჰიპოთეზები | ALEKSANDRA_BRAIN", en: "Hypotheses | ALEKSANDRA_BRAIN" },
    description: "კვლევითი ჰიპოთეზების სივრცე evidence-ს, სტატუსს, რისკს და შემდეგ მოქმედებას აჩვენებს მხოლოდ წყაროთი დადასტურებული ჩანაწერის არსებობისას.",
  },
  therapies: {
    path: "/therapies",
    title: { ka: "თერაპიები | ALEKSANDRA_BRAIN", en: "Therapies | ALEKSANDRA_BRAIN" },
    description: "თერაპიული იდეები წარმოდგენილია მხოლოდ რეალური წყაროს, evidence-ის დონისა და უსაფრთხოების საზღვრის არსებობისას.",
  },
  timeline: {
    path: "/timeline",
    title: { ka: "ქრონოლოგია | ALEKSANDRA_BRAIN", en: "Timeline | ALEKSANDRA_BRAIN" },
    description: "ქრონოლოგია აჩვენებს მხოლოდ რეალურად დამატებულ დაკვირვებებს, ვიზიტებს, კვლევით მოვლენებსა და follow-up ამოცანებს.",
  },
  "evidence-map": {
    path: "/evidence-map",
    title: { ka: "მტკიცებულების რუკა | ALEKSANDRA_BRAIN", en: "Evidence Map | ALEKSANDRA_BRAIN" },
    description: "მტკიცებულების რუკა წყაროებს, ჰიპოთეზებს, კითხვებსა და შემდეგ ნაბიჯს აჩვენებს მხოლოდ დადასტურებული ჩანაწერების არსებობისას.",
  },
  cohorts: {
    path: "/cohorts",
    title: { ka: "კვლევითი ჯგუფები | ALEKSANDRA_BRAIN", en: "Study Cohorts | ALEKSANDRA_BRAIN" },
    description: "კვლევითი ჯგუფების გვერდი გაერთიანებულ ჯგუფებსა და შედეგებს აჩვენებს მხოლოდ მაშინ, როცა შესაბამისი რეალური მონაცემი არსებობს.",
  },
  "data-integrations": {
    path: "/data-integrations",
    title: { ka: "მონაცემები და ინტეგრაციები | ALEKSANDRA_BRAIN", en: "Data & Integrations | ALEKSANDRA_BRAIN" },
    description: "მონაცემებისა და ინტეგრაციების გვერდი აღწერს მხოლოდ რეალურად დაკავშირებულ წყაროებს, წარმოშობას და შემოწმების პროცესს.",
  },
  papers: {
    path: "/papers",
    title: { ka: "კვლევითი წყაროები | ALEKSANDRA_BRAIN", en: "Research Papers | ALEKSANDRA_BRAIN" },
    description: "კვლევითი წყაროების ბიბლიოთეკა პუბლიკაციებსა და evidence-ის დონეს აჩვენებს მხოლოდ სრული citation-ის ან დადასტურებული წყაროს არსებობისას.",
  },
  alerts: {
    path: "/alerts",
    title: { ka: "განახლებები | ALEKSANDRA_BRAIN", en: "Alerts & Updates | ALEKSANDRA_BRAIN" },
    description: "განახლებების გვერდი აჩვენებს მხოლოდ რეალურად დაფიქსირებულ ახალ წყაროებს, კომენტარებსა და დაკვირვების სიის ცვლილებებს.",
  },
  resources: {
    path: "/resources",
    title: { ka: "ოჯახის რესურსები | ALEKSANDRA_BRAIN", en: "Family Resources | ALEKSANDRA_BRAIN" },
    description: "ოჯახის რესურსები brief-სა და კითხვებს ქმნის მხოლოდ არსებული დადასტურებული მონაცემებიდან; სხვა შემთხვევაში მიუთითებს, რომ მონაცემი არ არის.",
  },
  "how-it-works": {
    path: "/how-it-works",
    title: { ka: "როგორ მუშაობს | ALEKSANDRA_BRAIN", en: "How This Works | ALEKSANDRA_BRAIN" },
    description: "გვერდი განმარტავს real-data წესს: სისტემა არ იგონებს მონაცემს, აჩვენებს მხოლოდ დადასტურებულ ჩანაწერს და გადაწყვეტილებას ექიმთან ტოვებს.",
  },
  support: {
    path: "/support",
    title: { ka: "დახმარება | ALEKSANDRA_BRAIN", en: "Help & Support | ALEKSANDRA_BRAIN" },
    description: "დახმარების გვერდი აღწერს გამოყენების წესებს და მიუთითებს, რომ ყველა მონაცემზე დაფუძნებული პასუხი მხოლოდ დადასტურებული ჩანაწერიდან უნდა მოდიოდეს.",
  },
  settings: {
    path: "/settings",
    title: { ka: "პარამეტრები | ALEKSANDRA_BRAIN", en: "Settings | ALEKSANDRA_BRAIN" },
    description: "პარამეტრები აღწერს ენას, ხედვის რეჟიმს და უსაფრთხოების საზღვრის ტექსტებს რეალური მონაცემის ჩვენების წესთან ერთად.",
  },
  audit: {
    path: "/audit",
    title: { ka: "აუდიტი | ALEKSANDRA_BRAIN", en: "Audit Trail | ALEKSANDRA_BRAIN" },
    description: "აუდიტის ჟურნალი განკუთვნილია რეალური ცვლილებების, მიმოხილვების და გუნდის მოქმედებების გამჭვირვალე ისტორიისთვის.",
  },
  knowledge: {
    path: "/knowledge",
    title: { ka: "ცოდნის ბაზა | ALEKSANDRA_BRAIN", en: "Knowledge Base | ALEKSANDRA_BRAIN" },
    description: "ცოდნის ბაზა აერთიანებს მხოლოდ დადასტურებულ წყაროებს, ჰიპოთეზებსა და კვლევის პროცესს ოჯახისთვის გასაგებ სტრუქტურაში.",
  },
};

export const sitemapRoutes = Object.values(routeSeo).map((route) => route.path);

export function localizedPath(locale: Locale, path: string) {
  return `/${locale}${path === "/" ? "" : path}`;
}

export function absoluteUrl(path: string) {
  return new URL(path, SITE_URL).toString();
}

export function alternateLanguages(path: string) {
  return {
    "ka-GE": localizedPath("ka", path),
    en: localizedPath("en", path),
    "x-default": localizedPath("en", path),
  };
}

export function buildPageMetadata(locale: Locale, route: SeoRoute): Metadata {
  const copy = routeSeo[route];
  return buildCustomMetadata(locale, copy.path, copy.title[locale], copy.description);
}

export function buildCustomMetadata(
  locale: Locale,
  path: string,
  title: string,
  description: string,
): Metadata {
  const canonical = localizedPath(locale, path);
  const ogAlt = locale === "ka" ? "ALEKSANDRA_BRAIN-ის ციფრული ტვინის კვლევის სამუშაო სივრცე" : "ALEKSANDRA_BRAIN digital brain research workspace";

  return {
    metadataBase: new URL(SITE_URL),
    title,
    description,
    alternates: {
      canonical,
      languages: alternateLanguages(path),
    },
    openGraph: {
      type: "website",
      siteName: BRAND,
      locale: locale === "ka" ? "ka_GE" : "en_US",
      alternateLocale: locale === "ka" ? ["en_US"] : ["ka_GE"],
      url: canonical,
      title,
      description,
      images: [
        {
          url: DEFAULT_OG_IMAGE,
          width: 1200,
          height: 630,
          alt: ogAlt,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [DEFAULT_OG_IMAGE],
    },
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        "max-image-preview": "large",
        "max-snippet": -1,
        "max-video-preview": -1,
      },
    },
  };
}
