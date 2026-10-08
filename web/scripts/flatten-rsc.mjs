// Runs after `next build`. The static export writes per-segment RSC payloads as nested
// files (demo/__next.demo/__PAGE__.txt) while the client router requests them with dots
// (demo/__next.demo.__PAGE__.txt). A plain static host has no rewrite for that, so link
// prefetches 404. This copies each nested payload to the dotted name it is requested by.
import { copyFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const out = join(dirname(fileURLToPath(import.meta.url)), "..", "out");
let copied = 0;

function flatten(dir, base, prefix) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) flatten(path, base, `${prefix}.${name}`);
    else {
      const target = join(base, `${prefix}.${name}`);
      if (!existsSync(target)) {
        copyFileSync(path, target);
        copied++;
      }
    }
  }
}

function walk(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (!statSync(path).isDirectory() || name === "_next" || name === "data") continue;
    if (name.startsWith("__next.")) flatten(path, dir, name);
    else walk(path);
  }
}

if (existsSync(out)) {
  walk(out);
  console.log(`flatten-rsc: ${copied} segment payload(s) copied`);
}
