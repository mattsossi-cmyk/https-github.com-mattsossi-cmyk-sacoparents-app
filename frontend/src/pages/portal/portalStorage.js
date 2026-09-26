/**
 * Shared constants, defaults, presets and localStorage helpers for
 * SacoparentsPortal and its sub-components.
 */

export const BIFF_LOG_KEY = "sacoparents_biff_logs";
export const ALIGN_RECORDS_KEY = "sacoparents_align_records";
export const MILESTONE_KEY = "sacoparents_milestone_logs";
export const FOUNDATION_KEY = "sacoparents_foundation_statement";
export const LEGAL_REPORT_KEY = "sacoparents_legal_report";
export const HEALTH_INDEX_KEY = "sacoparents_health_index";
export const COURT_KEY_KEY = "sacoparents_court_key";
export const REASSESSMENT_KEY = "sacoparents_reassessments";
export const SYNC_PENDING_KEY = "sacoparents_sync_pending";
export const SAFETY_ACK_KEY = "sacoparents_safety_screen_ack";

export const PRESETS = {
  late_handoff: {
    raw: "You were late again by 20 minutes! You have zero respect for my time or the schedule.",
    biff:
      "Thank you for letting me know. I ran into unexpected traffic and arrived at 4:20 PM. I will plan for extra transit time for our next pickup on Friday.",
    flags: ["Hostile tone", "Accusatory phrase ('zero respect')"],
  },
  expense_request: {
    raw: "I bought the required school uniforms and you need to pay me back half right now. Stop ignoring your duties!",
    biff:
      "The total for the required school uniforms came to $80. Attached is the receipt for your half ($40). Please let me know if you can send reimbursement by the end of the month. Thanks.",
    flags: ["Demanding tone", "Blame language"],
  },
  schedule_change: {
    raw: "I need to switch next weekend because I have a work event. You always refuse to help out.",
    biff:
      "I have a mandatory work event next weekend (Oct 12-14). I would like to request swapping for the following weekend (Oct 19-21). Please let me know if that works for your calendar by Thursday. Thank you.",
    flags: ["Passive aggressive comment"],
  },
  medical_update: {
    raw: "I took Alex to the doctor. You never check in on his asthma symptoms as usual.",
    biff:
      "Alex had his regular pediatric checkup today. The doctor updated his asthma inhaler prescription. I have uploaded the visit summary to the Medical folder for your review.",
    flags: ["Personal attack ('You never check in')"],
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

export const DEFAULT_MILESTONES = [
  {
    id: 1,
    type: "success",
    title: "On-Time Handoff Completed",
    date: "2026-09-22",
    note: "Exchanged at neutral drop-off point without friction.",
  },
  {
    id: 2,
    type: "friction",
    title: "Schedule Request Delay",
    date: "2026-09-18",
    note: "Required 24-hr reminder before confirmation.",
  },
];

export const DEFAULT_FOUNDATION =
  "Our primary goal remains the emotional wellbeing, stability, and health of our child. We commit to clear, low-conflict BIFF communication, respecting schedule boundaries, and sharing vital medical, educational, and psychological records promptly.";

export const DEFAULT_LEGAL_REPORT = {
  sigA: "",
  sigB: "",
  sigMed: "Matt Sossi, Licensed Mediator (San Antonio, TX)",
};

export const DEFAULT_HEALTH_INDEX = { s1: 7, s2: 6, s3: 5 };

export const DEFAULT_BIFF_LOGS = [
  {
    id: 1,
    timestamp: "2026-09-20 14:30",
    category: "Handoff Delay",
    original: "You are late again.",
    biff: "Thank you for checking in. Arrived at 4:15 PM due to traffic.",
  },
];

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
