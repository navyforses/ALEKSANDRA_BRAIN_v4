import type { Metadata } from "next";

export type Locale = "en" | "ka";

export const SITE_URL = "https://viewer-sigma-two.vercel.app";
export const BRAND = "ALEKSANDRA_BRAIN";
export const DEFAULT_OG_IMAGE = "/og-image.png";

// The whole system lives on five surfaces. Today is the hub; the rest
// expand outward from it.
export type SeoRoute = "home" | "research" | "brain" | "brief" | "history";

type RouteCopy = {
  path: string;
  title: Record<Locale, string>;
  description: Record<Locale, string>;
};

export const routeSeo: Record<SeoRoute, RouteCopy> = {
  home: {
    path: "/",
    title: {
      ka: "ALEKSANDRA_BRAIN — რა მოხდა, რა ვაკეთო",
      en: "ALEKSANDRA_BRAIN — What happened, what to do",
    },
    description: {
      ka: "მუდმივად მომუშავე კვლევითი სისტემა ალექსანდრასთვის. ერთ ეკრანზე — რა იპოვა სისტემამ, რა მოითხოვს ყურადღებას და ერთი ნაბიჯით რა გააკეთო.",
      en: "A research system that never stops, for Aleksandra. One screen: what the system found, what needs you, and what you can do in a single step.",
    },
  },
  research: {
    path: "/research",
    title: {
      ka: "კვლევა | ALEKSANDRA_BRAIN",
      en: "Research | ALEKSANDRA_BRAIN",
    },
    description: {
      ka: "ცოცხალი კვლევის ხედვა — ნაშრომები, ჰიპოთეზები და თერაპიის კანდიდატები. ყოველი ფაქტი წყაროთი; წყაროს გარეშე — ცხადად ნათქვამი.",
      en: "The live research view — papers, hypotheses, and therapy candidates. Every fact carries a source; where there is none, it is stated plainly.",
    },
  },
  brain: {
    path: "/brain",
    title: {
      ka: "ტვინი | ALEKSANDRA_BRAIN",
      en: "Brain | ALEKSANDRA_BRAIN",
    },
    description: {
      ka: "MRI იხსნება ბრაუზერში და არასოდეს ტოვებს კომპიუტერს. პრივატულობა არქიტექტურის ნაწილია, არა შეზღუდვა.",
      en: "MRI opens in the browser and never leaves the computer. Privacy is part of the architecture, not a constraint.",
    },
  },
  brief: {
    path: "/brief",
    title: {
      ka: "კვირის რეზიუმე | ALEKSANDRA_BRAIN",
      en: "Weekly brief | ALEKSANDRA_BRAIN",
    },
    description: {
      ka: "რა აღმოაჩინა სისტემამ ბოლო 7 დღეში — იკითხება ეკრანზე, ერთი ჟესტით ხდება PDF ექიმთან წასაღებად.",
      en: "What the system found in the last 7 days — readable on screen, one gesture away from a PDF for the clinician.",
    },
  },
  history: {
    path: "/history",
    title: {
      ka: "ისტორია | ALEKSANDRA_BRAIN",
      en: "History | ALEKSANDRA_BRAIN",
    },
    description: {
      ka: "გამჭვირვალე ისტორია — რა გააკეთა სისტემამ, რა შესთავაზა, რა დაადასტურა შაკომ, რა დააბრუნა უკან. შავი ყუთი არ არსებობს.",
      en: "A transparent history — what the system did, what it proposed, what was confirmed, and what was undone. No black box.",
    },
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
  return buildCustomMetadata(
    locale,
    copy.path,
    copy.title[locale],
    copy.description[locale],
  );
}

export function buildCustomMetadata(
  locale: Locale,
  path: string,
  title: string,
  description: string,
): Metadata {
  const canonical = localizedPath(locale, path);
  const ogAlt =
    locale === "ka"
      ? "ALEKSANDRA_BRAIN — კვლევითი სისტემა ალექსანდრასთვის"
      : "ALEKSANDRA_BRAIN — a research system for Aleksandra";

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
      images: [{ url: DEFAULT_OG_IMAGE, width: 1200, height: 630, alt: ogAlt }],
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
