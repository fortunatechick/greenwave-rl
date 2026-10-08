// Removes the Next build cache. Turbopack's cache served stale CSS after edits to
// globals.css, so every production build starts clean.
import { rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

rmSync(join(dirname(fileURLToPath(import.meta.url)), "..", ".next"), { recursive: true, force: true });
