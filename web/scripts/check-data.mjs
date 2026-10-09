// Runs before `next build` (spec 11.9). Validates every data file against the shared
// schemas and refuses to build a production site from mock data.
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { FILES, ReplaySchema, SCENES } from "../src/lib/schemas.mjs";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const dataDir = join(root, "public", "data");
const errors = [];

function load(rel) {
  const path = join(dataDir, rel);
  if (!existsSync(path)) {
    errors.push(`${rel}: missing (run \`npm run fixtures\` for preview data, or the Python export)`);
    return null;
  }
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch (err) {
    errors.push(`${rel}: invalid JSON (${err.message})`);
    return null;
  }
}

function check(rel, schema) {
  const data = load(rel);
  if (data === null) return null;
  const result = schema.safeParse(data);
  if (!result.success) {
    const issue = result.error.issues[0];
    errors.push(`${rel}: ${issue.path.join(".")} ${issue.message}`);
    return null;
  }
  return result.data;
}

let mock = false;
for (const [rel, schema] of Object.entries(FILES)) {
  const data = check(rel, schema);
  if ((rel === "meta.json" || rel === "corridor.json") && data?.mock) mock = true;
}
for (const scene of SCENES) {
  const replay = check(`replays/${scene}.json`, ReplaySchema);
  if (replay?.mock) mock = true;
}

const mustBeReal = process.env.VERCEL_ENV === "production" || process.env.CI_REQUIRE_REAL_DATA === "1";
if (mock && mustBeReal) {
  errors.push(
    "mock data present (meta.mock or a replay is flagged mock) but this build requires real results. " +
      "Run the Python pipeline: python tasks.py export",
  );
}

if (errors.length) {
  console.error("check-data failed:\n  - " + errors.join("\n  - "));
  process.exit(1);
}
console.log(`check-data: ${Object.keys(FILES).length + SCENES.length} files valid${mock ? " (MOCK preview data)" : ""}`);
