import React from "react";

import { FlowArrow } from "../selfJourney/FlowArrow";
import { PILLARS, POINTS, STATUS_PILL, STEPS } from "./courtContent";

export function AcceptCard({ verified, courtKey, onAccept }) {
  return (
    <section data-testid="court-accept-card" className="bg-white/90 rounded-3xl border border-purple-100 shadow-sm p-5 sm:p-6">
      <ul className="grid sm:grid-cols-3 gap-3 mb-5">
        {POINTS.map(([icon, text], i) => (
          <li key={icon} data-testid={`court-point-${i}`} className="flex items-start gap-2.5 bg-[#f2ebfc] rounded-2xl p-3">
            <span className="shrink-0 w-8 h-8 rounded-full bg-white text-[#5c2c8e] flex items-center justify-center">
              <i className={`fa-solid ${icon}`}></i>
            </span>
            <span className="text-xs text-slate-700 leading-snug">{text}</span>
          </li>
        ))}
      </ul>
      <button
        type="button"
        data-testid="court-accept-btn"
        onClick={onAccept}
        className="w-full bg-gradient-to-b from-[#3fb453] to-[#2fa144] hover:from-[#36a249] hover:to-[#268537] text-white font-extrabold text-base sm:text-xl py-4 px-5 rounded-full shadow-lg shadow-emerald-200 flex items-center justify-center gap-3 transition-[transform,background-color] hover:-translate-y-0.5"
      >
        <i className="fa-solid fa-clipboard-check text-xl sm:text-2xl"></i>
        <span>{verified ? "Court-Ordered Invite Accepted" : "Accept Your Court-Ordered Invite"}</span>
        <i className="fa-solid fa-chevron-right"></i>
      </button>
      <p data-testid="court-accept-caption" className="text-center text-sm text-slate-600 mt-2.5">
        {verified ? (
          <span className="text-emerald-700 font-semibold">
            <i className="fa-solid fa-circle-check mr-1"></i>Case {courtKey} verified · tap to update your details
          </span>
        ) : (
          "Begin your court-ordered co-parenting journey."
        )}
      </p>
    </section>
  );
}

function StepStatus({ n, status }) {
  const [label, , icon] = STATUS_PILL[status];
  const tone = status === "done" ? "text-emerald-700" : status === "in_progress" ? "text-amber-700" : "text-slate-500";
  return (
    <span data-testid={`court-step-card-${n}-status`} data-status={status} className={`inline-flex items-center gap-1 text-[11px] font-bold ${tone}`}>
      <i className={`fa-solid ${icon}`}></i>
      {label}
    </span>
  );
}

export function StepCards({ statusOf, onStep }) {
  return (
    <section data-testid="court-step-cards">
      <h3 className="text-xl sm:text-2xl font-extrabold text-[#3B1C6B]">Your Court-Ordered Journey</h3>
      <p className="text-sm text-slate-600 mb-4">Follow the steps below to complete your assessments and prepare your information.</p>
      <div className="space-y-3 sm:space-y-4">
        {STEPS.map((s) => {
          const status = statusOf(s.card);
          return (
            <React.Fragment key={s.n}>
            {s.n > 1 && (
              <FlowArrow testid={`court-flow-arrow-${s.n}`} to={`court-step-card-${s.n}`} label={s.short} step={`${s.n} of ${STEPS.length}`} done={status === "done"} size="sm" />
            )}
            <button
              type="button"
              data-testid={`court-step-card-${s.n}`}
              onClick={() => onStep(s)}
              className={`step-card w-full text-left border rounded-2xl p-3.5 sm:p-5 flex items-start gap-3 sm:gap-4 hover:shadow-md transition-shadow ${s.tone.card}`}
            >
              <span className={`relative w-10 h-10 sm:w-12 sm:h-12 rounded-2xl ${s.tone.tile} text-white flex items-center justify-center text-lg sm:text-xl shrink-0 shadow-sm`}>
                <i className={`fa-solid ${s.icon}`}></i>
                <span className="absolute -top-2 -left-2 w-6 h-6 rounded-full bg-[#3b1566] text-white text-xs font-extrabold flex items-center justify-center border-2 border-white">{s.n}</span>
              </span>
              <span className="flex-1 min-w-0">
                <span className={`block text-base sm:text-lg font-bold ${s.tone.heading}`}>{s.short}</span>
                <span className="block text-xs text-slate-600 mt-0.5 sm:mt-1 leading-relaxed">{s.body}</span>
                <span className="block mt-2">
                  <StepStatus n={s.n} status={status} />
                </span>
              </span>
              <i className="fa-solid fa-chevron-right text-[#5c2c8e] pt-1"></i>
            </button>
            </React.Fragment>
          );
        })}
      </div>
    </section>
  );
}

export function PillarCards({ onPillar }) {
  return (
    <section data-testid="court-pillar-cards" className="bg-white/90 rounded-3xl border border-purple-100 shadow-sm p-5 sm:p-6">
      <h3 className="text-lg sm:text-xl font-extrabold text-[#3B1C6B] text-center">Your Information Helps Build the Bigger Picture</h3>
      <p className="text-sm text-slate-600 text-center mb-4">When both parents participate, SA CoParents can help identify:</p>
      <div className="grid grid-cols-2 gap-3">
        {PILLARS.map((p) => (
          <button
            key={p.key}
            type="button"
            data-testid={`court-pillar-card-${p.key}`}
            onClick={() => onPillar(p)}
            className="text-center rounded-2xl border border-[#e7dbf8] hover:border-[#5c2c8e] hover:bg-[#faf8fd] p-3.5 transition-colors"
          >
            <span className={`mx-auto mb-2 w-11 h-11 rounded-full ${p.tile} text-white flex items-center justify-center text-lg shadow-sm`}>
              <i className={`fa-solid ${p.icon}`}></i>
            </span>
            <span className="block text-sm font-bold text-[#3b1566]">{p.title}</span>
            <span className="block text-[11px] text-slate-600 leading-snug mt-0.5">{p.sub}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
