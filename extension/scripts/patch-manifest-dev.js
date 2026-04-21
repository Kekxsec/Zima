#!/usr/bin/env node
// Patches dist/manifest.json for local dev: replaces app.zima.app with localhost:3000

import { readFileSync, writeFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const manifestPath = resolve(__dirname, "../dist/manifest.json");
const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));

const DEV_URL = "http://localhost:3000";
const DEV_ORIGIN = "http://localhost:3000";

// Replace host_permissions
manifest.host_permissions = manifest.host_permissions.map((p) =>
  p.replace("https://app.zima.app/*", `${DEV_URL}/*`),
);

// Replace content script matches for zimaapp
for (const cs of manifest.content_scripts) {
  cs.matches = cs.matches.map((m) =>
    m.replace("https://*.zima.app/*", `${DEV_URL}/*`),
  );
}

// Widen CSP connect-src for localhost
if (manifest.content_security_policy?.extension_pages) {
  manifest.content_security_policy.extension_pages =
    manifest.content_security_policy.extension_pages.replace(
      "connect-src https://api.zima.app https://app.zima.app",
      `connect-src https://api.zima.app https://app.zima.app ${DEV_ORIGIN}`,
    );
}

writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
console.log("Manifest patched for dev (localhost:3000)");
