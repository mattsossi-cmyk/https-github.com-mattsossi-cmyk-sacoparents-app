import React from "react";

import { MAIN_SPOT, PILLARS, STATUS_PILL, STEPS } from "./courtContent";

const box = ([top, left, width, height]) => ({ top: `${top}%`, left: `${left}%`, width: `${width}%`, height: `${height}%` });

export function Spot({ testid, spot, label, hints, main = false, className = "", onClick, children }) {
  return (
    <button
      type="button"
      data-testid={testid}
      aria-label={label}
      title={label}
      onClick={onClick}
      style={box(spot)}
      className={`court-spot absolute rounded-xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#7b2cbf] ${main ? "court-spot-main rounded-[35px]" : ""} ${hints ? "hint" : ""} ${className}`}
    >
      {children}
    </button>
  );
}

function StepPill({ n, status }) {
  const [label, tone, icon] = STATUS_PILL[status];
  return (
    <span
      data-testid={`court-step-${n}-status`}
      data-status={status}
      className={`absolute bottom-1 left-1 sm:bottom-2 sm:left-2 inline-flex items-center gap-1 rounded-full px-1.5 sm:px-2 py-0.5 text-[8px] sm:text-[11px] font-bold shadow ${tone}`}
    >
      <i className={`fa-solid ${icon}`}></i>
      {label}
    </span>
  );
}

function HintsToggle({ hints, onToggle }) {
  return (
    <div className="flex items-center justify-between gap-2 mb-2.5">
      <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-purple-700 whitespace-nowrap">Tap the picture or the cards</span>
      <button
        type="button"
        data-testid="court-hints-toggle"
        aria-pressed={hints}
        onClick={onToggle}
        className="bg-[#f2ebfc] hover:bg-[#e7dbf8] text-[#3b1566] border border-[#e7dbf8] px-3 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 whitespace-nowrap transition-colors"
      >
        <i className={`fa-solid ${hints ? "fa-eye" : "fa-eye-slash"}`}></i>
        <span>{hints ? "Hide Action Buttons" : "Show Action Buttons"}</span>
      </button>
    </div>
  );
}

// The Court-Ordered Journey artwork with clickable hotspots and live step progress (top on phones, right column on desktop).
export function CourtJourneyArt({ hints, onToggleHints, statusOf, onAccept, onStep, onPillar }) {
  return (
    <div>
      <HintsToggle hints={hints} onToggle={onToggleHints} />
      <div data-testid="court-art" className="relative w-full rounded-3xl overflow-hidden shadow-lg border border-purple-100 bg-white">
        <img
          data-testid="court-art-img"
          src="/images/court-journey-640.webp"
          srcSet="/images/court-journey-640.webp 640w, /images/court-journey.webp 1024w"
          sizes="(min-width: 1024px) 440px, 100vw"
          width={1024}
          height={1536}
          alt="SA CoParents Court-Ordered Path: accept your court-ordered invite, then complete four steps: your co-parenting assessment, reflect on your parenting, identify your child's specific needs, and create your Foundation Statement."
          className="w-full h-auto block"
        />
        <Spot testid="court-spot-accept" spot={MAIN_SPOT} label="Accept Your Court-Ordered Invite" hints={hints} main onClick={onAccept} />
        {STEPS.map((s) => (
          <Spot key={s.n} testid={`court-spot-step-${s.n}`} spot={s.spot} label={s.title} hints={hints} onClick={() => onStep(s)}>
            <StepPill n={s.n} status={statusOf(s.card)} />
          </Spot>
        ))}
        {PILLARS.map((p) => (
          <Spot key={p.key} testid={`court-spot-pillar-${p.key}`} spot={p.spot} label={p.title} hints={hints} onClick={() => onPillar(p)} />
        ))}
      </div>
    </div>
  );
}
