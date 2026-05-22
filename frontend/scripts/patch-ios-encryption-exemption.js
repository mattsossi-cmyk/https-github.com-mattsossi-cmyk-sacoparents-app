#!/usr/bin/env node
/**
 * Patches the Capacitor-generated iOS Info.plist so Apple's Export
 * Compliance question is answered automatically on every build.
 *
 * SA Coparents only uses standard iOS HTTPS / system-provided encryption,
 * so it is EXEMPT from Export Compliance (ECCN 5D992.c).
 *
 * Run AFTER `npx cap add ios` or `npx cap sync ios`.
 *
 * What it sets:
 *   ITSAppUsesNonExemptEncryption = false
 *
 * This single key tells Apple "no, my app does not use non-exempt encryption"
 * so App Store Connect stops asking on every TestFlight / release submission.
 */
const fs = require("fs");
const path = require("path");

const INFO_PLIST = path.resolve(
  __dirname,
  "..",
  "ios",
  "App",
  "App",
  "Info.plist"
);

if (!fs.existsSync(INFO_PLIST)) {
  console.log(
    `[encryption-exemption] ${INFO_PLIST} not found — skipping. Run \`npx cap add ios\` first.`
  );
  process.exit(0);
}

let plist = fs.readFileSync(INFO_PLIST, "utf8");

if (plist.includes("ITSAppUsesNonExemptEncryption")) {
  console.log(
    "[encryption-exemption] ITSAppUsesNonExemptEncryption already set — nothing to do."
  );
  process.exit(0);
}

// Insert key/value right before the closing </dict></plist>
const insertion = `	<key>ITSAppUsesNonExemptEncryption</key>
	<false/>
`;

plist = plist.replace("</dict>\n</plist>", `${insertion}</dict>\n</plist>`);
fs.writeFileSync(INFO_PLIST, plist);

console.log(
  "[encryption-exemption] OK — added ITSAppUsesNonExemptEncryption=false to Info.plist."
);
