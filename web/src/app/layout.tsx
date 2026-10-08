import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono, Instrument_Serif } from "next/font/google";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { meta, siteUrl } from "@/lib/data";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"], display: "swap" });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"], display: "swap" });
const instrumentSerif = Instrument_Serif({
  variable: "--font-instrument-serif",
  subsets: ["latin"],
  weight: "400",
  style: "italic",
  display: "swap",
});

const description =
  "Deep reinforcement learning for adaptive traffic signal control under mixed Indian traffic, " +
  "with a passenger-weighted, fairness-aware reward and an honest generalisation study.";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: "GreenWave-RL: signal timing, learned", template: "%s · GreenWave-RL" },
  description,
  alternates: { canonical: "/" },
  openGraph: {
    title: "GreenWave-RL: signal timing, learned",
    description,
    url: siteUrl,
    siteName: "GreenWave-RL",
    images: [{ url: "/og.png", width: 1200, height: 630, alt: "GreenWave-RL" }],
    type: "website",
  },
  twitter: { card: "summary_large_image", title: "GreenWave-RL", description, images: ["/og.png"] },
  icons: { icon: [{ url: "/favicon.svg", type: "image/svg+xml" }, { url: "/favicon-32.png", sizes: "32x32" }] },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#0A0C0F" },
    { media: "(prefers-color-scheme: light)", color: "#F6F7F9" },
  ],
};

// Runs while the HTML is parsed, so the stored or system theme applies before first paint.
const themeScript = `(function(){try{var t=localStorage.getItem("theme");if(t!=="light"&&t!=="dark"){t=window.matchMedia("(prefers-color-scheme: light)").matches?"light":"dark"}document.documentElement.setAttribute("data-theme",t)}catch(e){}})()`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      data-theme="dark"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} ${instrumentSerif.variable} antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="flex min-h-screen flex-col">
        <a
          href="#content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-md focus:bg-surface-2 focus:px-3 focus:py-2"
        >
          Skip to content
        </a>
        {meta.mock ? (
          <div
            role="status"
            className="relative z-40 border-b border-amber/40 bg-amber/15 px-4 py-2 text-center text-sm font-medium text-amber"
          >
            Preview data — not real results
          </div>
        ) : null}
        <SiteHeader />
        <main id="content" className="flex-1">
          {children}
        </main>
        <SiteFooter />
      </body>
    </html>
  );
}
