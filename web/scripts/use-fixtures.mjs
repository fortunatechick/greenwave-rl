// Copies web/fixtures (mock preview data) into public/data for local development.
// Refuses to overwrite real exported results unless --force is given.
import { cpSync, existsSync, readFileSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const target = join(root, "public", "data");
const metaPath = join(target, "meta.json");

if (existsSync(metaPath) && !process.argv.includes("--force")) {
  const meta = JSON.parse(readFileSync(metaPath, "utf8"));
  if (!meta.mock) {
    console.error("public/data holds real results; not overwriting. Use --force to replace them.");
    process.exit(1);
  }
}
rmSync(target, { recursive: true, force: true });
cpSync(join(root, "fixtures"), target, { recursive: true });
console.log("public/data <- fixtures (mock preview data)");
