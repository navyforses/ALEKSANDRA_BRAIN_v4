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
  | "audit"
  | "papers"
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
    description: "ოჯახისა და კლინიკური გუნდისთვის შექმნილი სამუშაო სივრცე, რომელიც HIE კვლევას, პროგრესს, ჰიპოთეზებსა და ექიმთან გადასამოწმებელ ნაბიჯებს აერთიანებს.",
  },
  today: {
    path: "/today",
    title: { ka: "დღეს | ALEKSANDRA_BRAIN", en: "Today | ALEKSANDRA_BRAIN" },
    description: "დღევანდელი კლინიკური ფოკუსის, ოჯახის კითხვებისა და უსაფრთხო follow-up ნაბიჯების მოკლე, გასაგები შეჯამება.",
  },
  dashboard: {
    path: "/dashboard",
    title: { ka: "მართვის პანელი | ALEKSANDRA_BRAIN", en: "Clinical Dashboard | ALEKSANDRA_BRAIN" },
    description: "კლინიკური მართვის პანელი აჩვენებს HIE მონაცემებს, კვლევის ნაკადს, აქტივობასა და ექიმთან გადასამოწმებელ პრიორიტეტებს.",
  },
  brain: {
    path: "/brain",
    title: { ka: "ციფრული ტვინის ლაბორატორია | ALEKSANDRA_BRAIN", en: "Digital Twin Brain Lab | ALEKSANDRA_BRAIN" },
    description: "ციფრული ტვინის ლაბორატორია აერთიანებს MRI-ს, კლინიკურ ფენებსა და პროგრესის ვიზუალს უსაფრთხო, არადიაგნოსტიკურ კონტექსტში.",
  },
  hypotheses: {
    path: "/hypotheses",
    title: { ka: "ჰიპოთეზები | ALEKSANDRA_BRAIN", en: "Hypotheses | ALEKSANDRA_BRAIN" },
    description: "კვლევითი ჰიპოთეზების სივრცე აჩვენებს evidence-ს, სტატუსს, რისკს და შემდეგ მოქმედებას, სანამ იდეა კლინიკურ განხილვაზე გადავა.",
  },
  therapies: {
    path: "/therapies",
    title: { ka: "თერაპიები | ALEKSANDRA_BRAIN", en: "Therapies | ALEKSANDRA_BRAIN" },
    description: "თერაპიული იდეები წარმოდგენილია evidence-ის დონით, ასაკობრივი ფანჯრით, უსაფრთხოების საზღვრებითა და ექიმთან განხილვის საჭიროებით.",
  },
  timeline: {
    path: "/timeline",
    title: { ka: "ქრონოლოგია | ALEKSANDRA_BRAIN", en: "Timeline | ALEKSANDRA_BRAIN" },
    description: "ქრონოლოგია აერთიანებს დაკვირვებებს, ვიზიტებს, კვლევით მოვლენებსა და follow-up ამოცანებს დროით კონტექსტში.",
  },
  audit: {
    path: "/audit",
    title: { ka: "აუდიტი | ALEKSANDRA_BRAIN", en: "Audit Trail | ALEKSANDRA_BRAIN" },
    description: "აუდიტის ჟურნალი ინახავს ცვლილებების, მიმოხილვების და გუნდის მოქმედებების გამჭვირვალე ისტორიას.",
  },
  papers: {
    path: "/papers",
    title: { ka: "კვლევითი წყაროები | ALEKSANDRA_BRAIN", en: "Research Papers | ALEKSANDRA_BRAIN" },
    description: "კვლევითი წყაროების ბიბლიოთეკა აჩვენებს პუბლიკაციებს, relevance score-ს, evidence დონესა და HIE-სთან კავშირს.",
  },
  knowledge: {
    path: "/knowledge",
    title: { ka: "ცოდნის ბაზა | ALEKSANDRA_BRAIN", en: "Knowledge Base | ALEKSANDRA_BRAIN" },
    description: "ცოდნის ბაზა აერთიანებს წყაროებს, გრაფს, ჰიპოთეზებსა და კვლევის pipeline-ს ოჯახისათვის გასაგებ სტრუქტურაში.",
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
