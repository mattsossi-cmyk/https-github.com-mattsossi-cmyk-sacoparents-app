import React from "react";
import { useNavigate } from "react-router-dom";
import { Check, RefreshCw } from "lucide-react";

import { useAuth } from "../context/AuthContext";
import { useCalmMode } from "../lib/useCalmMode";
import { useCaseSettings } from "../lib/useCaseSettings";
import { useCheckinLink } from "../lib/useCheckinLink";
import { useSelfAssessmentHistory } from "./portal/selfAssessment/useSelfAssessmentHistory";
import "./JourneyFlow.css";

/*
  SA CoParents — Journey Flow
  Order: Self Journey → Start with Safety → split into
         Co-Parenting path or Parallel Parenting path → Child's Needs → Foundation Statement → Export PDF
*/

// Real screens. "print" = the same Export PDF as the header button.
// Start with Safety opens the Family check-in on SACOparentsAlign directly (useCheckinLink), in a new tab.
export const ROUTES = {
  self: "/self-journey/guided",
  coparenting: "/dashboard?open=coparenting-assessment",
  parallelBuilder: "/dashboard?open=parallel-builder-steps",
  childNeeds: "/dashboard?open=child-needs",
  foundation: "/dashboard?open=foundation",
  retakeSelfAssessment: "/dashboard?open=self-assessment",
  exportPdf: "print",
};

// In-app only reminder (no emails): shown once the last Self-Assessment is 6+ weeks old.
function RetakeReminder({ dueDays, onStart }) {
  return (
    <section className="jf-reminder" data-testid="journey-flow-retake-reminder">
      <span className="jf-reminder-icon" aria-hidden="true"><RefreshCw size={18} /></span>
      <div className="jf-reminder-body">
        <h2>Time to retake your Self-Assessment</h2>
        <p>
          It&apos;s been {Math.floor(dueDays / 7)} weeks since your last one. Retaking it shows how far you&apos;ve come.
        </p>
        <button type="button" className="jf-reminder-btn" onClick={onStart} data-testid="journey-flow-retake-start">
          Start my Self-Assessment
        </button>
      </div>
    </section>
  );
}

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

// `href` (even null while it loads) makes the card a link that opens in a new tab.
// `done` shows a small "Done" tick (Start with Safety, once SACOparentsAlign has confirmed the check-in).
function StepCard({ id, step, title, subtitle, img, alt, onGo, href, tone = "purple", done = null }) {
  const body = (
    <>
      {step && <span className="jf-step">{step}</span>}
      {done && (
        <span className="jf-done" data-testid={`journey-flow-${id}-done`}>
          <Check size={14} strokeWidth={3} aria-hidden="true" /> Done
          <span className="sr-only">, confirmed by SACOparentsAlign{typeof done === "string" ? ` on ${done}` : ""}</span>
        </span>
      )}
      <img src={img} alt={alt} className="jf-img" loading="lazy" />
      <span className="jf-title">{title}</span>
      <span className="jf-sub">{subtitle}</span>
    </>
  );
  const cls = `jf-card jf-${tone}`;
  const testid = `journey-flow-step-${id}`;
  if (href !== undefined) {
    return (
      <a href={href || undefined} aria-disabled={!href} target="_blank" rel="noopener noreferrer" className={cls} data-testid={testid}>
        {body}
        <span className="sr-only"> (opens SACOparentsAlign in a new tab)</span>
      </a>
    );
  }
  return <button type="button" className={cls} onClick={() => onGo(id)} data-testid={testid}>{body}</button>;
}

function PathSplit({ go }) {
  return (
    <section className="jf-split" aria-label="Choose your path" data-testid="journey-flow-split">
      <div className="jf-path jf-path-green" data-testid="journey-flow-path-coparenting">
        <div className="jf-path-label">
          <span className="jf-pill jf-pill-green">No · lower conflict</span>
          <h2>Co-Parenting Path</h2>
        </div>
        <Arrow color="#2e9d4a" />
        <StepCard id="coparenting" step="Step 3" title="CoParenting Assessment" subtitle="Communication · decisions · plan"
          img={IMG("coparent")} alt="CoParenting Assessment card" onGo={go} tone="green" />
      </div>
      <div className="jf-path jf-path-purple" data-testid="journey-flow-path-parallel">
        <div className="jf-path-label">
          <span className="jf-pill jf-pill-purple">Yes · there are safety concerns</span>
          <h2>Parallel Parenting Path</h2>
        </div>
        <Arrow />
        <StepCard id="parallelBuilder" step="Step 3" title="Parallel Parenting Builder" subtitle="Contact · exchanges · decisions"
          img={IMG("parallel")} alt="Parallel Parenting Option Builder screen" onGo={go} />
      </div>
    </section>
  );
}

// `actions` (optional) opens a step in place, e.g. inside the Self Journey screen; otherwise each step goes to ROUTES.
export default function JourneyFlow({ alignUrl, actions = {}, embedded = false }) {
  const navigate = useNavigate();
  const { calm } = useCalmMode();
  const checkinHref = useCheckinLink(alignUrl);
  // Only a confirmation from SACOparentsAlign counts; nothing is shown otherwise.
  const caseSettings = useCaseSettings();
  const checkinDone = caseSettings?.setup_complete ? caseSettings.setup_completed_on || true : null;
  const { user } = useAuth();
  const { dueDays } = useSelfAssessmentHistory(embedded ? null : user?.user_id);
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

      {/* The embedded copy (Self Journey screen) already has its own "Time to reassess" banner. */}
      {!embedded && dueDays > 0 && <RetakeReminder dueDays={dueDays} onStart={() => go("retakeSelfAssessment")} />}

      <section className="jf-column">
        <StepCard id="self" step="Step 1" title="Self Journey" subtitle="Reflect, learn, grow"
          img={IMG("self")} alt="Self Assessment screen" onGo={go} />
        <Arrow />
        <StepCard id="safety" step="Step 2" title="Start with Safety" subtitle="Private family check-in"
          img={IMG("safety")} alt="Start with Safety screen" href={checkinHref} done={checkinDone} />
        <Arrow />
        <div className="jf-decision" role="note" data-testid="journey-flow-decision">
          <span>Are there safety concerns?</span>
        </div>
      </section>

      <PathSplit go={go} />

      <section className="jf-column">
        <div className="jf-join" aria-hidden="true" />
        <Arrow />
        <StepCard id="childNeeds" step="Both paths" title="Identify Your Child's Needs" subtitle="Educational · medical · psychological"
          img={IMG("needs")} alt="Identify Your Child's Needs screen" onGo={go} />
        <Arrow />
        <StepCard id="foundation" step="Both paths" title="Create Your Foundation Statement" subtitle="Shared goals · values · your child's future"
          img={IMG("foundation")} alt="Create Your Foundation Statement screen" onGo={go} />
        <Arrow />
        <button type="button" className="jf-export" onClick={() => go("exportPdf")} data-testid="journey-flow-export-pdf">
          Export PDF · ready for mediation
        </button>
      </section>
    </div>
  );
}
