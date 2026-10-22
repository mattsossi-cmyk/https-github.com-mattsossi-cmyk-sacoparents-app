import React from "react";
import { useNavigate } from "react-router-dom";

import { useCalmMode } from "../lib/useCalmMode";
import "./JourneyFlow.css";

/*
  SA CoParents — Journey Flow
  Order: Self Journey → Start with Safety → split into
         Co-Parenting path or Parallel Parenting path → Child's Needs → Export PDF
*/

// Real screens. "print" = the same Export PDF as the header button.
export const ROUTES = {
  self: "/dashboard?open=self-assessment",
  safety: "/start-with-safety",
  coparenting: "/dashboard?open=coparenting-assessment",
  parallelNext: "/dashboard?open=parallel-builder",
  parallelBuilder: "/dashboard?open=parallel-builder-steps",
  childNeeds: "/dashboard?open=child-needs",
  exportPdf: "print",
};

// Pictures live in public/images/journey/ (public/journey/ would clash with the /journey address).
const IMG = (name) => `/images/journey/${name}.webp`;

function Arrow({ color = "#5b2db3" }) {
  return (
    <div className="jf-arrow" aria-hidden="true">
      <svg width="16" height="48" viewBox="0 0 16 48">
        <line x1="8" y1="0" x2="8" y2="40" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
        <path d="M2 36 L8 46 L14 36" fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

function StepCard({ id, step, title, subtitle, img, alt, onGo, tone = "purple" }) {
  return (
    <button type="button" className={`jf-card jf-${tone}`} onClick={() => onGo(id)} data-testid={`journey-flow-step-${id}`}>
      {step && <span className="jf-step">{step}</span>}
      <img src={img} alt={alt} className="jf-img" loading="lazy" />
      <span className="jf-title">{title}</span>
      <span className="jf-sub">{subtitle}</span>
    </button>
  );
}

function PathSplit({ go }) {
  return (
    <section className="jf-split" aria-label="Choose your path" data-testid="journey-flow-split">
      <div className="jf-path jf-path-green" data-testid="journey-flow-path-coparenting">
        <div className="jf-path-label">
          <span className="jf-pill jf-pill-green">Yes · lower conflict</span>
          <h2>Co-Parenting Path</h2>
        </div>
        <Arrow color="#2e9d4a" />
        <StepCard id="coparenting" step="Step 3" title="CoParenting Assessment" subtitle="Communication · decisions · plan"
          img={IMG("coparent")} alt="CoParenting Assessment card" onGo={go} tone="green" />
      </div>
      <div className="jf-path jf-path-purple" data-testid="journey-flow-path-parallel">
        <div className="jf-path-label">
          <span className="jf-pill jf-pill-purple">Yes · There are Safety Concerns</span>
          <h2>Parallel Parenting Path</h2>
        </div>
        <Arrow />
        <StepCard id="parallelNext" step="Step 3" title="What's Next" subtitle="Build your parallel plan"
          img={IMG("next")} alt="What's Next screen" onGo={go} />
        <Arrow />
        <StepCard id="parallelBuilder" step="Step 4" title="Parallel Parenting Builder" subtitle="Contact · exchanges · decisions"
          img={IMG("parallel")} alt="Parallel Parenting Option Builder screen" onGo={go} />
      </div>
    </section>
  );
}

// `actions` (optional) opens a step in place, e.g. inside the Self Journey screen; otherwise each step goes to ROUTES.
export default function JourneyFlow({ actions = {}, embedded = false }) {
  const navigate = useNavigate();
  const { calm } = useCalmMode();
  const go = (key) => {
    if (actions[key]) return actions[key]();
    if (ROUTES[key] === "print") return window.print();
    return navigate(ROUTES[key]);
  };

  return (
    <div className={`jf-page${embedded ? " jf-embedded" : ""}${calm ? " calm-mode" : ""}`} data-testid="journey-flow">
      <header className="jf-header">
        <h1>Your journey, step by step</h1>
        <p>
          Start with your Self Journey, then the safety check. Your answers guide you to the
          co-parenting path or the parallel parenting path. Both lead to your child&apos;s needs.
        </p>
      </header>

      <section className="jf-column">
        <StepCard id="self" step="Step 1" title="Self Journey" subtitle="Reflect, learn, grow"
          img={IMG("self")} alt="Self Assessment screen" onGo={go} />
        <Arrow />
        <StepCard id="safety" step="Step 2" title="Start with Safety" subtitle="Private family check-in"
          img={IMG("safety")} alt="Start with Safety screen" onGo={go} />
        <Arrow />
        <div className="jf-decision" role="note" data-testid="journey-flow-decision">
          <span>Safe to work together?</span>
        </div>
      </section>

      <PathSplit go={go} />

      <section className="jf-column">
        <div className="jf-join" aria-hidden="true" />
        <Arrow />
        <StepCard id="childNeeds" step="Both paths" title="Identify Your Child's Needs" subtitle="Educational · medical · psychological"
          img={IMG("needs")} alt="Identify Your Child's Needs screen" onGo={go} />
        <Arrow />
        <button type="button" className="jf-export" onClick={() => go("exportPdf")} data-testid="journey-flow-export-pdf">
          Export PDF · ready for mediation
        </button>
      </section>
    </div>
  );
}
