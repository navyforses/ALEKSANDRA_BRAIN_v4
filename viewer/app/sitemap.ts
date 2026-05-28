import type { MetadataRoute } from "next";
import { SITE_URL, localizedPath, sitemapRoutes, type Locale } from "@/lib/seo";

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  const locales: Locale[] = ["ka", "en"];

  return locales.flatMap((locale) =>
    sitemapRoutes.map((path) => ({
      url: new URL(localizedPath(locale, path), SITE_URL).toString(),
      lastModified,
      changeFrequency: path === "/" ? "weekly" : "monthly",
      priority: path === "/" ? 1 : 0.72,
    })),
  );
}
