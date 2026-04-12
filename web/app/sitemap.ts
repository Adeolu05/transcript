import type { MetadataRoute } from "next";
import { SITE_URL } from "../lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
    const base = SITE_URL.replace(/\/$/, "");
    return [
        {
            url: base,
            lastModified: new Date(),
            changeFrequency: "monthly",
            priority: 1,
        },
        {
            url: `${base}/app`,
            lastModified: new Date(),
            changeFrequency: "monthly",
            priority: 0.8,
        },
        {
            url: `${base}/privacy`,
            lastModified: new Date(),
            changeFrequency: "yearly",
            priority: 0.3,
        },
        {
            url: `${base}/terms`,
            lastModified: new Date(),
            changeFrequency: "yearly",
            priority: 0.3,
        },
    ];
}
