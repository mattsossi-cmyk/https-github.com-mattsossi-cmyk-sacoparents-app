// Fill-in template used when AI suggested wording isn't available. Copies the parent's own questions, dates and times verbatim.
const DATE_TIME_RE =
  /\d|\b(?:mon|tues|wednes|thurs|fri|satur|sun)day\b|\b(?:today|tomorrow|tonight|weekend|morning|afternoon|evening|noon|midnight|next week|this week)\b|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d/i;
const BOUNDARY_RE =
  /\b(?:i|we)\s+(?:will not|won't|can't|cannot|can not|am not|'m not|do not|don't|will no longer|will stop|'ll stop|am unable|'m unable)\b|\bplease\s+(?:do not|don't|stop)\b|\b(?:is|are)\s+not\s+(?:ok|okay|acceptable)\b/i;

const norm = (s) => s.replace(/[\u2018\u2019]/g, "'");

export function essentialsOf(raw) {
  const sentences = (raw || "")
    .split(/(?<=[.!?])\s+|\n+/)
    .map((s) => s.trim())
    .filter(Boolean);
  const questions = sentences.filter((s) => s.includes("?"));
  const details = sentences.filter((s) => !s.includes("?") && (DATE_TIME_RE.test(s) || BOUNDARY_RE.test(norm(s))));
  return { questions, details };
}

export function fillInTemplate(raw, greyRock = false) {
  const { questions, details } = essentialsOf(raw);
  const lines = greyRock ? [] : ["Hi,", ""];
  lines.push('[One calm sentence saying what this is about, e.g. "About pickup:"]');
  if (details.length) lines.push("", ...details);
  if (questions.length) lines.push("", ...questions);
  if (!details.length && !questions.length) lines.push("", "[The facts: what, when and where]", "[Your request or question]");
  lines.push("", '[Optional: one clear next step, e.g. "Please reply by ___."]');
  if (!greyRock) lines.push("", "Thanks,", "[Your name]");
  return lines.join("\n");
}
