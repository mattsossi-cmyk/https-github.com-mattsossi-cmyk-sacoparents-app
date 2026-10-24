/**
 * Self Journey "your path": the personalized starting point (progress.stage) and the conflict level built from it.
 * The parent's own safety pick ("concern") always wins: the safety path. Nothing here is ever locked or hidden,
 * except "Working together" on the high and safety paths.
 */
import React from "react";
import { X } from "lucide-react";

export const STAGES = [
  { id: "separated", name: "Just separated or divorcing", desc: "Everything is new and you're finding your footing.", focus: ["self-assessment", "child-needs"] },
  { id: "planning", name: "Developing a parenting plan", desc: "You're working out schedules, decisions and agreements.", focus: ["child-needs", "foundation"] },
  { id: "communication", name: "Communication is difficult", desc: "Conversations with the other parent often go badly.", focus: ["self-assessment", "coparenting"] },
  { id: "ongoing", name: "Managing an ongoing arrangement", desc: "A plan exists and you want it to work better.", focus: ["coparenting", "child-needs"] },
  { id: "highConflict", name: "Dealing with high conflict", desc: "Disagreements are frequent, intense or ongoing.", focus: ["coparenting", "mediation"] },
];

export const CONFLICT_LEVELS = {
  cooperative: {
    label: "Cooperative",
    coparenting: "Joint planning can work for your family. Look for shared ground and decisions you can make together.",
    mediation: "Standard child-focused mediation may fit well. Come ready with options you could both accept.",
    nextStep: "Plan a child-focused mediation session or a joint planning conversation.",
  },
  difficult: {
    label: "Communication is difficult",
    coparenting: "Keep messages short, structured and written, about one topic at a time. The BIFF tool can help.",
    mediation: "Ask about mediation with clear ground rules, a written agenda or online sessions.",
    nextStep: "Use the BIFF tool to keep each message brief, informative, friendly and firm.",
  },
  high: {
    label: "High conflict",
    coparenting: "Brief, factual, written communication and parallel parenting usually work best. Joint sessions aren't suggested.",
    mediation: "Ask a professional about separate-room (shuttle) or attorney-assisted options instead of joint sessions.",
    nextStep: "Ask a family law professional about parallel parenting and separate-room mediation.",
  },
  safety: {
    label: "Safety first",
    coparenting: "This page won't suggest direct communication. Parallel parenting and structured, written tools may be a better fit.",
    mediation: "Joint or standard mediation may not be appropriate. Talk with an advocate or professional about separate-room mediation, attorney-assisted negotiation or protective measures.",
    nextStep: "Talk with a family violence advocate or a family law professional before any joint process.",
  },
};

// Safety always wins, then the parent's own starting point.
export function conflictLevel(progress) {
  if (progress.safety?.status === "concern") return "safety";
  if (progress.stage === "highConflict") return "high";
  if (progress.stage === "communication") return "difficult";
  return "cooperative";
}

export const hidesWorkingTogether = (level) => level === "high" || level === "safety";

export const isRecommended = (stage, slug) => Boolean(STAGES.find((s) => s.id === stage)?.focus.includes(slug));

export function StagePicker({ value, onPick }) {
  return (
    <section className="sj-stage" data-testid="sj-stage">
      <h2 className="sj-subhead" id="sj-stage-label">Where are you right now?</h2>
      <p className="sj-small" style={{ margin: "0 0 8px" }}>Optional. We&apos;ll point out the pages that fit best. Every page stays open.</p>
      <div className="sj-choice-list" role="radiogroup" aria-labelledby="sj-stage-label">
        {STAGES.map((s) => (
          <button key={s.id} type="button" role="radio" aria-checked={value === s.id}
            className={`sj-choice ${value === s.id ? "is-on" : ""}`} onClick={() => onPick(value === s.id ? null : s.id)}
            data-testid={`sj-stage-${s.id}`}>
            <strong>{s.name}</strong>
            <span>{s.desc}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

export function RecommendedBadge() {
  return <span className="sj-rec-badge" data-testid="sj-recommended">Recommended for you</span>;
}

export function PathNote({ level, page }) {
  const l = CONFLICT_LEVELS[level];
  return (
    <div className={`sj-notice ${level === "safety" ? "sj-notice-warning" : "sj-path-note"}`} data-testid={`sj-path-note-${page}`} data-level={level}>
      <strong>Your path: {l.label}.</strong> {l[page]}
    </div>
  );
}

export function PathCard({ stage, level, onChange }) {
  const s = STAGES.find((x) => x.id === stage);
  return (
    <section className="sj-card sj-path-card" data-testid="sj-path-card" data-level={level}>
      <div className="sj-path-card-head">
        <h2 className="sj-card-title">Your path</h2>
        <button type="button" className="sj-text-btn" onClick={onChange} data-testid="sj-path-change">Change</button>
      </div>
      <p className="sj-small" style={{ margin: 0 }} data-testid="sj-path-stage">
        {s ? s.name : "You haven't chosen a starting point yet."}
      </p>
      <p className="sj-small" style={{ margin: "4px 0 0" }} data-testid="sj-path-level">
        <strong>{CONFLICT_LEVELS[level].label}</strong>
      </p>
    </section>
  );
}

// Shown on the next page after the green arrow on Steps 1–6 (never after the safety page). Calm on purpose.
export const STEP_DONE_TEXT = {
  1: "You took a positive step toward understanding where you are today.",
  2: "You took a positive step toward understanding yourself as a parent.",
  3: "You took a positive step toward understanding your co-parenting relationship.",
  4: "You took a positive step toward putting your child's needs at the center.",
  5: "You took a positive step toward naming what matters most for your child.",
  6: "You took a positive step toward calm, child-focused conversations.",
};

export function StepComplete({ number, next, onDismiss }) {
  return (
    <div className="sj-step-done" data-testid="sj-step-complete" data-step-number={number}>
      <p>
        <strong>Step {number} complete.</strong> {STEP_DONE_TEXT[number]}{" "}
        <span className="sj-step-done-next">Now: {next.title} · about {next.minutes} min</span>
      </p>
      <button type="button" className="sj-icon-btn" onClick={onDismiss} aria-label="Dismiss" data-testid="sj-step-complete-dismiss">
        <X size={16} aria-hidden="true" />
      </button>
    </div>
  );
}
