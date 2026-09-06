/**
 * AIDraftedPill.jsx — a small badge that marks a summary block or
 * clause as "AI-drafted" so mediators and attorneys immediately see
 * which portions of a report came from the LLM (vs. verbatim parent
 * input or deterministic anchors).
 *
 * Usage:
 *   <AIDraftedPill model={report.ai_summary_model} />
 *   <AIDraftedPill model="claude" tone="amber" />
 *
 * `model` maps to a human-readable label:
 *   "claude" → "Claude Sonnet 4.5"
 *   "gpt"    → "GPT 5.6 Terra"
 * Anything else falls back to a generic "AI-drafted" label.
 */
import React from "react";
import { Sparkles } from "lucide-react";

const MODEL_LABEL = {
  claude: "Claude Sonnet 4.5",
  gpt: "GPT 5.6 Terra",
};

const TONE_CLASSES = {
  neutral: "border-[#D6CFE8] text-[#3D1A78] bg-[#F5F1FB]",
  blue: "border-[#B7D9EE] text-[#1E6FA8] bg-[#EAF3FA]",
  amber: "border-[#E6D8C1] text-[#8A4610] bg-[#FFF6EA]",
  green: "border-[#C7E5D3] text-[#0F5638] bg-[#EEF7F1]",
};

export default function AIDraftedPill({
  model = "claude",
  tone = "neutral",
  className = "",
  testId = "ai-drafted-pill",
}) {
  const label = MODEL_LABEL[model] || "AI-drafted";
  const toneClass = TONE_CLASSES[tone] || TONE_CLASSES.neutral;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] ${toneClass} ${className}`}
      data-testid={testId}
      data-model={model}
      title="This paragraph was drafted by a language model from the neutral compare payload. Parent answers themselves stay verbatim."
    >
      <Sparkles size={11} strokeWidth={2.4} aria-hidden />
      AI-drafted · <span className="normal-case font-medium">{label}</span>
    </span>
  );
}
