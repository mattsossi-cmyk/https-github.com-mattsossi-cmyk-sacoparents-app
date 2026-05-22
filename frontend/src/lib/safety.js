/**
 * Safety guardrail — detects concerning language in user-entered text and
 * surfaces immediate crisis resources without ever blocking the user from
 * continuing to write. Designed to be NON-MODAL so an abuser can't see a popup.
 *
 * Tiered by severity:
 *   - "danger" : immediate physical / suicide risk → 911 + 988 + DV hotline
 *   - "support": ongoing distress, abuse pattern → DV hotline + Safety page
 *   - null     : nothing concerning detected
 */

// Word-boundary regex (case-insensitive). Avoid false positives like
// "tomorrow night" matching "night" or "knife in the drawer" matching cooking.
function w(pattern) {
  return new RegExp(`(?:^|\\b)${pattern}(?:\\b|$)`, "i");
}

const DANGER_PATTERNS = [
  w("kill (?:myself|me|him|her|them|us)"),
  w("want(?:s)? to die"),
  w("end(?:ing)? (?:my|her|his) life"),
  w("take my (?:own )?life"),
  w("can'?t go on"),
  w("commit suicide"),
  w("suicidal"),
  w("self[- ]harm(?:ing)?"),
  w("(?:going to|gonna|i'll|i will) hurt (?:him|her|them|us|the kids?)"),
  w("(?:he|she|they) (?:will|going to|gonna) kill"),
  w("threaten(?:ed|ing|s)? to kill"),
  w("(?:has|have|got) a gun"),
  w("scared (?:for|of) my life"),
];

const SUPPORT_PATTERNS = [
  w("(?:he|she|they) (?:hits?|hit|hitting|beats?|beat|beating|chokes?|choked|punches?|punched|slaps?|slapped|strangles?|strangled|kicks?|kicked) me"),
  w("domestic (?:violence|abuse)"),
  w("(?:emotional|physical|verbal|sexual|financial) abuse"),
  w("(?:he|she|they) (?:hits?|hit|hitting|beats?|beat|beating) (?:the )?(?:kids?|children|baby|her|him)"),
  w("(?:i('?| a)m|i feel) (?:not )?safe"),
  w("(?:i('?| a)m|i feel) (?:afraid|scared|terrified) (?:of|to)"),
  w("(?:restraining|protection|protective) order"),
  w("(?:rape|raped|sexual assault)"),
  w("forced me to"),
  w("locked me (?:in|out)"),
  w("controls (?:my|me|the) (?:money|finances|phone)"),
  w("won'?t let me (?:leave|go|see|talk)"),
  w("stalking (?:me|us)"),
];

export function detectSafetyConcern(text) {
  if (!text || typeof text !== "string") return null;
  const t = text.trim();
  if (t.length < 3) return null;

  for (const re of DANGER_PATTERNS) {
    if (re.test(t)) return "danger";
  }
  for (const re of SUPPORT_PATTERNS) {
    if (re.test(t)) return "support";
  }
  return null;
}

/**
 * Returns the resource bundle to show for a given severity.
 */
export function safetyResources(level) {
  if (level === "danger") {
    return {
      level: "danger",
      title: "If you're in immediate danger",
      message:
        "Please reach out to someone now. You don't have to write anything more here first.",
      actions: [
        { label: "Call 911", href: "tel:911", primary: true },
        {
          label: "Call 988 — Suicide & Crisis Lifeline",
          href: "tel:988",
        },
        {
          label: "Text START to 88788 — National DV Hotline",
          href: "sms:88788?body=START",
        },
      ],
      tone: "danger",
    };
  }
  if (level === "support") {
    return {
      level: "support",
      title: "It sounds like you may be facing a difficult situation",
      message:
        "Confidential, free, 24/7 support is available. This app is preparation only — it is not a substitute for safety planning.",
      actions: [
        {
          label: "Call 1-800-799-7233 — National DV Hotline",
          href: "tel:18007997233",
          primary: true,
        },
        {
          label: "Chat thehotline.org",
          href: "https://www.thehotline.org/",
          external: true,
        },
        { label: "View safety resources", to: "/safety" },
      ],
      tone: "warm",
    };
  }
  return null;
}
