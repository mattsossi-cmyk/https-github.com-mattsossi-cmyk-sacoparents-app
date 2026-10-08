import React from "react";

import { MAIN_SPOT, PILLARS, STATUS_PILL, STEPS } from "./courtContent";

const box = ([top, left, width, height]) => ({ top: `${top}%`, left: `${left}%`, width: `${width}%`, height: `${height}%` });

function Spot({ testid, spot, label, hints, main = false, onClick, children }) {
  return (
    <button
      type="button"
      data-testid={testid}
      aria-label={label}
      title={label}
      onClick={onClick}
      style={box(spot)}
      className={`court-spot absolute rounded-xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#7b2cbf] ${main ? "court-spot-main rounded-[35px]" : ""} ${hints ? "hint" : ""}`}
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
      className={`absolute top-1 right-1 sm:top-2 sm:right-2 inline-flex items-center gap-1 rounded-full px-1.5 sm:px-2 py-0.5 text-[8px] sm:text-[11px] font-bold shadow ${tone}`}
    >
      <i className={`fa-solid ${icon}`}></i>
      {label}
    </span>
  );
}

// The Court-Ordered Journey artwork with clickable hotspots and live step progress.
export function CourtJourneyArt({ hints, statusOf, onAccept, onStep, onPillar }) {
  return (
    <div data-testid="court-art" className="relative w-full rounded-[18px] overflow-hidden shadow-[0_10px_30px_rgba(0,0,0,0.12)] bg-white">
      <img
        data-testid="court-art-img"
        src="/images/court-journey.webp"
        srcSet="/images/court-journey-640.webp 640w, /images/court-journey.webp 1024w"
        sizes="(max-width: 640px) 100vw, 900px"
        alt="SA CoParents Court-Ordered Journey: accept your invite, then complete four steps"
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
  );
}
