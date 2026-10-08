import type { MetadataRoute } from "next";
import { meta, siteUrl } from "@/lib/data";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date(meta.generated_at);
  return ["/", "/demo/", "/results/", "/method/", "/junction/", "/about/"].map((path) => ({
    url: `${siteUrl}${path}`,
    lastModified,
    changeFrequency: "monthly",
    priority: path === "/" ? 1 : 0.7,
  }));
}
