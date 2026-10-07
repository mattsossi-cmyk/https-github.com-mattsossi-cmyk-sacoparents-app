import CONTENT from "../selfAssessmentContent.json";

// Copy lives in selfAssessmentContent.json — mirrored on the backend
// (self_assessment_content.json) so the PDF stays in lockstep.
export { CONTENT };

export const SCALE = CONTENT.scale;
export const SECTIONS = CONTENT.sections;
export const REFLECTIONS = CONTENT.reflection.questions;
const MAX_VALUE = Math.max(...SCALE.map((s) => s.value));
export const QUESTION_COUNT = SECTIONS.reduce((n, s) => n + s.questions.length, 0);
export const scaleLabel = (v) => SCALE.find((s) => s.value === v)?.label || "";

// Flat, ordered list of chat steps. Each step knows how to tell if it is done.
export const STEPS = [
  { type: "intro", id: "intro" },
  ...SECTIONS.flatMap((s) =>
    s.questions.map((q, i) => ({
      type: "rate",
      id: `${s.key}_${i + 1}`,
      section: s,
      index: i,
      prompt: q,
    }))
  ),
  ...REFLECTIONS.map((q, i) => ({ type: "reflect", id: q.key, index: i, prompt: q.prompt })),
  { type: "goal", id: "goal" },
];

export const isStepDone = (step, draft) => {
  if (step.type === "intro") return !!draft.started;
  if (step.type === "rate") return draft.answers[step.id] != null;
  if (step.type === "reflect") return draft.reflections[step.id] != null;
  return draft.goal != null;
};

export const currentStepIndex = (draft) => {
  const idx = STEPS.findIndex((s) => !isStepDone(s, draft));
  return idx === -1 ? STEPS.length : idx;
};

export const scoreAnswers = (answers) => {
  const sections = {};
  let total = 0;
  SECTIONS.forEach((s) => {
    const raw = s.questions.reduce((n, _q, i) => n + (answers[`${s.key}_${i + 1}`] || 0), 0);
    sections[s.key] = Math.round((raw * 100) / (s.questions.length * MAX_VALUE));
    total += raw;
  });
  return {
    overall: Math.round((total * 100) / (QUESTION_COUNT * MAX_VALUE)),
    sections,
    answered: Object.keys(answers).length,
    question_count: QUESTION_COUNT,
  };
};

export const bandFor = (score) => CONTENT.bands.find((b) => score >= b.min) || null;

// "May 2026", or "May 12, 2026" when two entries share a month (mirrors PDF).
export const entryLabel = (entries, i) => {
  const d = new Date(entries[i].completed_at);
  const month = d.toLocaleDateString("en-US", { month: "long", year: "numeric" });
  const clash =
    entries.filter(
      (e) =>
        new Date(e.completed_at).toLocaleDateString("en-US", { month: "long", year: "numeric" }) === month
    ).length > 1;
  return clash
    ? d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })
    : month;
};

// Short x-axis label for the progress chart: "May 2026", or "May 12" when two entries share a month.
export const chartLabel = (entries, i) => {
  const d = new Date(entries[i].completed_at);
  const full = entryLabel(entries, i);
  return full.includes(",")
    ? d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
    : d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
};

// Chart series colours — mirrored in backend self_assessment_pdf.SERIES_RGB.
export const SERIES_COLORS = {
  overall: "#4c2889",
  child_focus: "#40a040",
  self_awareness: "#8b5cf6",
  communication: "#0284c7",
  differences: "#e67e22",
};

export const emptyDraft = (parentName) => ({
  started: false,
  parent_name: parentName || "",
  answers: {},
  reflections: {},
  goal: null,
});

export const toDraftPayload = (d) => ({
  started: !!d.started,
  parent_name: d.parent_name || "",
  answers: d.answers || {},
  reflections: d.reflections || {},
  goal: d.goal ?? null,
});

export const readJson = (key, fallback) => {
  try {
    const v = JSON.parse(window.localStorage.getItem(key) || "null");
    return v ?? fallback;
  } catch {
    return fallback;
  }
};

export const writeJson = (key, value) => {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage unavailable */
  }
};
