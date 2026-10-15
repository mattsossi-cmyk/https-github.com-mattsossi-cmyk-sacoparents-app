/**
 * Shared constants, defaults, presets and localStorage helpers for
 * SacoparentsPortal and its sub-components.
 */

export const BIFF_LOG_KEY = "sacoparents_biff_logs";
export const ALIGN_RECORDS_KEY = "sacoparents_align_records";
// Child medical/educational/psychological record folders are switched off for privacy.
export const RECORDS_ENABLED = false;
export const MILESTONE_KEY = "sacoparents_milestone_logs";
export const FOUNDATION_KEY = "sacoparents_foundation_statement";
export const LEGAL_REPORT_KEY = "sacoparents_legal_report";
export const HEALTH_INDEX_KEY = "sacoparents_health_index";
export const COURT_KEY_KEY = "sacoparents_court_key";
export const REASSESSMENT_KEY = "sacoparents_reassessments";
export const SYNC_PENDING_KEY = "sacoparents_sync_pending";
export const SAFETY_ACK_KEY = "sacoparents_safety_screen_ack";
export const SAFETY_PLAN_KEY = "sacoparents_safety_plan";
// Per-topic draft store for the Guided Journey chat wizard so parents
// can resume a mid-wizard session on their next visit. Actual key at
// runtime: `sacoparents_guided_draft_${topic}`. Drafts auto-expire after
// GUIDED_DRAFT_TTL_MS (14 days) so we don't hand parents stale material.
export const GUIDED_DRAFT_KEY_PREFIX = "sacoparents_guided_draft_";
export const GUIDED_DRAFT_TTL_MS = 14 * 24 * 60 * 60 * 1000;
// Snapshot Library (iter227): committed Guided Journey runs so a
// parent can re-download the last-N cards without re-running the
// wizard.
export const SNAPSHOT_HISTORY_KEY = "sacoparents_snapshot_history";
export const SNAPSHOT_HISTORY_MAX = 12;
// Guide Follow-up Nudge (iter231): track path pick + first
// engagement to trigger a "how's it going?" check-in on the next
// visit if the parent picked a path but never opened a tile.
export const PATH_PICKED_KEY = "sacoparents_path_picked_at";
export const FIRST_ENGAGEMENT_KEY = "sacoparents_first_engagement_at";
export const FOLLOWUP_DISMISSED_KEY = "sacoparents_followup_dismissed_at";
// Minimum time between path-pick and first-visit-follow-up so we
// don't nag someone who picked their path 20 minutes ago and is
// still exploring.
export const FOLLOWUP_MIN_HOURS = 24;
// After a "not now, thanks" dismiss, wait this long before showing
// the follow-up again.
export const FOLLOWUP_SNOOZE_DAYS = 7;

// Preset drafts for the scenario chips; wording suggestions always come from the AI.
export const PRESETS = {
  late_handoff: {
    raw: "You were late again by 20 minutes! You have zero respect for my time or the schedule.",
  },
  expense_request: {
    raw: "I bought the required school uniforms and you need to pay me back half right now. Stop ignoring your duties!",
  },
  schedule_change: {
    raw: "I need to switch next weekend because I have a work event. You always refuse to help out.",
  },
  medical_update: {
    raw: "I took Alex to the doctor. You never check in on his asthma symptoms as usual.",
  },
};

export const DEFAULT_ALIGNMENTS = [
  {
    id: 1,
    category: "Medical",
    title: "Pediatric Asthma Management Plan",
    provider: "Dr. Evelyn Vance",
    date: "2026-08-14",
    summary:
      "Daily preventative inhaler approved. Emergency inhaler remains in backpack.",
  },
  {
    id: 2,
    category: "Educational",
    title: "Q1 Reading Progress Assessment",
    provider: "Oakridge Elementary",
    date: "2026-09-10",
    summary:
      "Reading at grade level. Recommended 20 minutes quiet reading nightly.",
  },
  {
    id: 3,
    category: "Psychological",
    title: "Child Transition Consultation",
    provider: "Dr. Marcus Thorne",
    date: "2026-07-22",
    summary:
      "Child benefits from visual calendar checklists in both bedrooms.",
  },
];

// Built-in sample entries older builds pre-filled into every account. Kept only so they can be removed.
const SAMPLES = {
  milestones: [
    { id: 1, type: "success", title: "On-Time Handoff Completed", date: "2026-09-22", note: "Exchanged at neutral drop-off point without friction." },
    { id: 2, type: "friction", title: "Schedule Request Delay", date: "2026-09-18", note: "Required 24-hr reminder before confirmation." },
  ],
  biff_logs: [
    { id: 1, timestamp: "2026-09-20 14:30", category: "Handoff Delay", original: "You are late again.", biff: "Thank you for checking in. Arrived at 4:15 PM due to traffic." },
  ],
};

export const withoutSamples = (field, list) =>
  Array.isArray(list) ? list.filter((e) => !SAMPLES[field].some((s) => Object.keys(s).every((k) => e?.[k] === s[k]))) : [];

export const DEFAULT_FOUNDATION =
  "Our primary goal remains the emotional wellbeing, stability, and health of our child. We commit to clear, low-conflict BIFF communication, respecting schedule boundaries, and sharing vital medical, educational, and psychological records promptly.";

export const DEFAULT_LEGAL_REPORT = {
  sigA: "",
  sigB: "",
  sigMed: "Matt Sossi, Licensed Mediator (San Antonio, TX)",
};

export const DEFAULT_HEALTH_INDEX = { s1: 7, s2: 6, s3: 5 };

export function readJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (raw == null) return fallback;
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

export function writeJson(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* ignore quota */
  }
}

export function readString(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw == null ? fallback : raw;
  } catch {
    return fallback;
  }
}

export function writeString(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* ignore quota */
  }
}

export function computeHealthLabel(avg) {
  if (avg >= 7.5) return "High Alignment";
  if (avg >= 5.5) return "Moderate Alignment";
  return "Low Alignment";
}

/**
 * Given a milestones array, count the number of consecutive days
 * (starting from the most recent kudos day and walking backwards)
 * that contain at least one `source: "biff_kudos"` milestone.
 *
 * Streak ends the first day with zero kudos milestones.
 * Skips days with no milestones at all — streak resumes only if
 * consecutive kudos-days form an unbroken chain.
 */
export function computeKudosStreak(milestones, now = new Date()) {
  if (!Array.isArray(milestones) || milestones.length === 0) return 0;
  const kudosDates = new Set();
  for (const m of milestones) {
    if (m && m.source === "biff_kudos" && m.date) {
      // Normalise to YYYY-MM-DD (dates are already in that format for kudos)
      kudosDates.add(String(m.date).substring(0, 10));
    }
  }
  if (kudosDates.size === 0) return 0;
  // Walk backwards from the most recent kudos day.
  const sorted = [...kudosDates].sort().reverse();
  const mostRecent = sorted[0];
  let cursor = new Date(`${mostRecent}T00:00:00Z`);
  // If the most recent kudos is more than 1 day older than today, the
  // streak is broken (parent stopped using the tone-safe copy) — don't
  // count it as an active streak.
  const today = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate())
  );
  const gapDays = Math.floor((today - cursor) / (24 * 60 * 60 * 1000));
  if (gapDays > 1) return 0;
  let streak = 0;
  const dayMs = 24 * 60 * 60 * 1000;
  while (true) {
    const iso = cursor.toISOString().substring(0, 10);
    if (kudosDates.has(iso)) {
      streak += 1;
      cursor = new Date(cursor.getTime() - dayMs);
    } else {
      break;
    }
  }
  return streak;
}
