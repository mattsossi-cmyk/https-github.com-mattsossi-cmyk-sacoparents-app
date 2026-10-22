import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, FileDown } from "lucide-react";

import { SafetyFirstBanner } from "../components/caseSettings/SafetyFirstBanner";
import { useCalmMode } from "../lib/useCalmMode";
import "./JourneyFlow.css";

// Each step opens a real screen. "print" = the same Export PDF as the header button.
export const ROUTES = {
  self: "/dashboard?open=self-assessment",
  safety: "/start-with-safety",
  coparent: "/dashboard?open=coparenting-assessment",
  next: "/joint-agreement",
  parallel: "/dashboard?open=parallel-builder",
  needs: "/dashboard?open=child-needs",
  pdf: "print",
};

// Pictures live in public/images/journey/ (not public/journey/, which would clash with the /journey address).
const IMG = { self: "self", safety: "safety", coparent: "coparent", next: "next", parallel: "parallel", needs: "needs" };

const BEFORE = [
  { key: "self", n: 1, title: "Self Assessment", text: "Reflect on your strengths, growth areas and goals as a parent." },
  { key: "safety", n: 2, title: "Start with Safety", text: "A private Family check-in on SACOparentsAlign. Your co-parent never sees your answers." },
  { key: "coparent", n: 3, title: "Co-Parenting Assessment", text: "Look at how you and your co-parent communicate and make decisions." },
];
// Same two options, same wording, for every parent. The parent picks.
const PATHS = [
  { key: "next", title: "What's Next: Co-Parenting", text: "Build a Co-Parenting Agreement when you can plan together safely.", cta: "Open the Co-Parenting Agreement" },
  { key: "parallel", title: "Parallel Parenting Option Builder", text: "Parent side by side with less contact when talking together causes conflict or doesn't feel safe.", cta: "Open the builder" },
];
const AFTER = [
  { key: "needs", n: 5, title: "Identify Your Child's Needs", text: "Note your child's educational, medical and psychological needs." },
  { key: "pdf", n: 6, title: "Export PDF", text: "Save or print a copy to bring to your professional." },
];

function StepCard({ step, onGo }) {
  const pic = IMG[step.key];
  return (
    <button type="button" onClick={() => onGo(step.key)} data-testid={`journey-flow-step-${step.key}`} className="jf-card">
      {pic ? (
        <img src={`/images/journey/${pic}.webp`} alt="" className="jf-img" loading="lazy" />
      ) : (
        <span className="jf-img jf-img-icon" aria-hidden><FileDown size={34} /></span>
      )}
      <span className="jf-body">
        {step.n && <span className="jf-num" aria-hidden>{step.n}</span>}
        <span className="jf-title">{step.title}</span>
        <span className="jf-text">{step.text}</span>
        <span className="jf-cta">{step.cta || "Open"} <ArrowRight size={14} aria-hidden /></span>
      </span>
    </button>
  );
}

function Fork({ onGo, alignUrl, onQuickExit }) {
  return (
    <section data-testid="journey-flow-fork" aria-labelledby="jf-fork-title" className="jf-fork">
      <p className="jf-eyebrow"><span className="jf-num jf-num-inline" aria-hidden>4</span>Two paths</p>
      <h2 id="jf-fork-title" className="jf-fork-title">Choose your parenting arrangement</h2>
      <SafetyFirstBanner alignUrl={alignUrl} onQuickExit={onQuickExit} testid="journey-flow-safety-first"
        text="Safety comes first. Take your private Family check-in before you choose. Your co-parent never sees your answers." />
      <p className="jf-fork-note" data-testid="journey-flow-fork-note">
        Co-parenting fits when you can talk and plan together safely. Parallel parenting fits when contact causes conflict
        or doesn&apos;t feel safe. Your check-in can help you decide, and you can switch any time.
      </p>
      <div className="jf-paths">{PATHS.map((p) => <StepCard key={p.key} step={p} onGo={onGo} />)}</div>
    </section>
  );
}

export default function JourneyFlow({ onExportPdf, alignUrl, onQuickExit }) {
  const navigate = useNavigate();
  const { calm } = useCalmMode();
  const go = (key) => (ROUTES[key] === "print" ? onExportPdf() : navigate(ROUTES[key]));
  return (
    <div data-testid="journey-flow" className={`jf${calm ? " calm-mode" : ""}`}>
      <Link to="/dashboard" data-testid="journey-flow-home" className="jf-home"><ArrowLeft size={14} aria-hidden /> Home</Link>
      <h1 className="jf-h1">Your Journey</h1>
      <p className="jf-lede">Go step by step. After the Co-Parenting Assessment, pick the arrangement that fits your family.</p>
      <ol className="jf-list">
        {BEFORE.map((s) => <li key={s.key}><StepCard step={s} onGo={go} /></li>)}
        <li><Fork onGo={go} alignUrl={alignUrl} onQuickExit={onQuickExit} /></li>
        {AFTER.map((s) => <li key={s.key}><StepCard step={s} onGo={go} /></li>)}
      </ol>
    </div>
  );
}
