// Generates public/og.png (1200 x 630), public/favicon.svg and public/favicon-32.png.
// The headline KPI on the card is read from the exported data, never typed.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const meta = JSON.parse(readFileSync(join(root, "public", "data", "meta.json"), "utf8"));

const h = meta.headline;
let kpi = "Results pending";
let kpiSub = "";
if (h.rl !== null && h.fixed !== null && h.fixed > 0) {
  const change = ((h.rl - h.fixed) / h.fixed) * 100;
  kpi = `${change < 0 ? "−" : "+"}${Math.abs(change).toFixed(0)}%`;
  kpiSub = `wait per person vs fixed-time, ${h.regime} demand`;
}
if (meta.mock) kpiSub = "preview data, not real results";

const glyph = (x, y, s) => `
  <g transform="translate(${x} ${y}) scale(${s})">
    <rect x="0.5" y="0.5" width="11" height="23" rx="5.5" fill="#181C22" stroke="#252A32"/>
    <circle cx="6" cy="5.5" r="2.4" fill="#8A93A0" opacity="0.45"/>
    <circle cx="6" cy="12" r="2.4" fill="#8A93A0" opacity="0.45"/>
    <circle cx="6" cy="18.5" r="2.4" fill="#3DDC84"/>
  </g>`;

const og = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="wave" x1="0" x2="1"><stop offset="0" stop-color="#3DDC84"/><stop offset="1" stop-color="#2BD4C8"/></linearGradient>
    <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
      <path d="M24 0H0V24" fill="none" stroke="#ffffff" stroke-opacity="0.035"/>
    </pattern>
  </defs>
  <rect width="1200" height="630" fill="#0A0C0F"/>
  <rect width="1200" height="630" fill="url(#grid)"/>
  <g opacity="0.9">
    <rect x="820" y="0" width="120" height="630" fill="#1B2027"/>
    <rect x="560" y="255" width="640" height="120" fill="#1B2027"/>
    <path d="M880 0V255M880 375V630M560 315H820M940 315H1200" stroke="#343B46" stroke-width="2" stroke-dasharray="14 14"/>
    <rect x="850" y="150" width="14" height="34" rx="3" fill="#CBD5E1"/>
    <rect x="850" y="196" width="14" height="34" rx="3" fill="#CBD5E1"/>
    <rect x="893" y="130" width="18" height="96" rx="3" fill="#C4B5FD"/>
    <rect x="872" y="204" width="6" height="15" rx="3" fill="#7DD3FC"/>
    <rect x="960" y="282" width="34" height="14" rx="3" fill="#CBD5E1"/>
    <rect x="1010" y="284" width="20" height="11" rx="4" fill="#FDE047"/>
    <rect x="700" y="335" width="34" height="14" rx="3" fill="#CBD5E1"/>
  </g>
  <rect width="700" height="630" fill="#0A0C0F" opacity="0.55"/>
  ${glyph(72, 70, 2.4)}
  <text x="118" y="112" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="34" font-weight="600" fill="#E8EAED">GreenWave<tspan fill="#8A93A0" font-weight="400">-RL</tspan></text>
  <text x="72" y="270" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="84" font-weight="600" fill="#E8EAED" letter-spacing="-3">Signal timing,</text>
  <text x="72" y="360" font-family="Georgia, serif" font-style="italic" font-size="92" fill="url(#wave)">learned.</text>
  <text x="72" y="500" font-family="Consolas, Menlo, monospace" font-size="64" font-weight="700" fill="url(#wave)">${kpi}</text>
  <text x="72" y="544" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="26" fill="#8A93A0">${kpiSub}</text>
</svg>`;

const favicon = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="7" fill="#0A0C0F"/>
  ${glyph(10, 4, 1)}
</svg>`;

await sharp(Buffer.from(og)).png().toFile(join(root, "public", "og.png"));
writeFileSync(join(root, "public", "favicon.svg"), favicon);
await sharp(Buffer.from(favicon), { density: 300 }).resize(32, 32).png().toFile(join(root, "public", "favicon-32.png"));
console.log(`og.png written (${kpi}${kpiSub ? ", " + kpiSub : ""})`);
