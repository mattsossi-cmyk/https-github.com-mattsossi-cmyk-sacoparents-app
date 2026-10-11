import React from "react";

import { PILLARS, POINTS } from "./courtContent";

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
