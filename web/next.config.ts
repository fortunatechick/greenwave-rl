import type { NextConfig } from "next";

// Static export: SUMO cannot run on Vercel, so the site only replays recorded
// simulations and renders exported results. No server, no API routes.
const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
