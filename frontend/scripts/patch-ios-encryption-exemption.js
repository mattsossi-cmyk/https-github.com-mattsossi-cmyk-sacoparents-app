#!/usr/bin/env node
/**
 * Patches the Capacitor-generated iOS Info.plist so:
 *
 *   1. Apple's Export Compliance question is auto-answered "exempt"
 *      (SA CoParents only uses standard iOS HTTPS / system encryption).
 *
 *   2. No routing/navigation capability is ever silently enabled — SA
 *      Coparents is a co-parenting mediation prep app, NOT a navigation
 *      app. We actively strip MKDirectionsApplicationSupportedModes if
 *      anything ever inserts it.
 *
 * Run AFTER `npx cap add ios` or `npx cap sync ios`.
 *
 * Keys set:
 *   ITSAppUsesNonExemptEncryption = false  (skip Apple's encryption question)
 *
 * Keys removed:
 *   MKDirectionsApplicationSupportedModes  (forces Apple to ask for a
 *                                           Routing App Coverage File)
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
    `[ios-patch] ${INFO_PLIST} not found — skipping. Run \`npx cap add ios\` first.`
  );
  process.exit(0);
}

let plist = fs.readFileSync(INFO_PLIST, "utf8");
let changed = false;

// 1. Encryption exemption
if (!plist.includes("ITSAppUsesNonExemptEncryption")) {
  const insertion = `	<key>ITSAppUsesNonExemptEncryption</key>
	<false/>
`;
  plist = plist.replace("</dict>\n</plist>", `${insertion}</dict>\n</plist>`);
  changed = true;
  console.log(
    "[ios-patch] Added ITSAppUsesNonExemptEncryption=false (Export Compliance auto-answer)."
  );
} else {
  console.log("[ios-patch] ITSAppUsesNonExemptEncryption already set.");
}

// 2. Strip routing capability if it ever shows up (SA CoParents is not a nav app)
const ROUTING_KEY = "MKDirectionsApplicationSupportedModes";
if (plist.includes(ROUTING_KEY)) {
  // Match: <key>MKDirectionsApplicationSupportedModes</key>\n  <array>...</array>
  const routingPattern = new RegExp(
    `\\s*<key>${ROUTING_KEY}<\\/key>\\s*<array>[\\s\\S]*?<\\/array>`,
    "g"
  );
  plist = plist.replace(routingPattern, "");
  changed = true;
  console.log(
    `[ios-patch] Removed ${ROUTING_KEY} — SA CoParents is not a navigation app.`
  );
}

if (changed) {
  fs.writeFileSync(INFO_PLIST, plist);
  console.log("[ios-patch] OK — Info.plist updated.");
} else {
  console.log("[ios-patch] Nothing to change.");
}

