import React from "react";

export function CourtHero({ courtKey, mediator, alignHost }) {
  return (
    <div data-testid="court-hero" className="bg-white rounded-3xl p-6 sm:p-8 shadow-lg border border-purple-100 mb-8">
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
        <div className="md:col-span-8 space-y-4">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-purple-50 border border-purple-200 text-purple-900 flex items-center justify-center text-2xl sm:text-3xl shrink-0 shadow-sm">
              <i className="fa-solid fa-landmark"></i>
            </div>
            <div>
              <h2 className="text-3xl md:text-4xl font-extrabold text-[#3B1C6B]">Court Ordered Path</h2>
              <p className="text-slate-600 font-medium text-sm md:text-base mt-1">
                Complete your court-ordered assessments and reports through SA CoParents.
              </p>
            </div>
          </div>
          <div data-testid="court-hero-note" className="bg-purple-50/80 rounded-2xl p-4 border border-purple-100 flex items-center gap-3 text-xs text-purple-900 font-medium">
            <i className="fa-solid fa-shield-halved text-purple-600 text-lg shrink-0"></i>
            <span>
              Your mediator, attorney, or parenting coordinator reviews your reports on <strong>{alignHost}</strong>. Download
              court-ready PDFs to share with them and the court.
            </span>
          </div>
        </div>
        <div data-testid="court-hero-status" className="md:col-span-4 bg-slate-900 text-white p-6 rounded-2xl border border-slate-800 shadow-inner text-center space-y-2">
          <i className="fa-solid fa-gavel text-amber-400 text-4xl mb-2"></i>
          <h4 className="font-bold text-sm tracking-wide">COURT ORDERED TRACK</h4>
          <p className="text-[11px] text-slate-400">Family court co-parenting assessments &amp; reports</p>
          {courtKey ? (
            <div data-testid="court-hero-case" className="inline-block mt-2 px-3 py-1 bg-emerald-500/20 text-emerald-300 text-[10px] font-bold rounded-full border border-emerald-500/30 break-all">
              Case {courtKey} verified
            </div>
          ) : (
            <div data-testid="court-hero-case" className="inline-block mt-2 px-3 py-1 bg-amber-500/15 text-amber-300 text-[10px] font-bold rounded-full border border-amber-500/30">
              Awaiting your case code
            </div>
          )}
          {mediator && (
            <p data-testid="court-hero-mediator" className="text-[10px] text-slate-400 pt-1">
              Professional: {mediator}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
