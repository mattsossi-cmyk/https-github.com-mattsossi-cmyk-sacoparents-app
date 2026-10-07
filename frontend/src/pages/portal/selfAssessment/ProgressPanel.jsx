import React from "react";

import { CONTENT, SECTIONS, bandFor, entryLabel } from "./content";

export function ScoreCards({ scores }) {
  const band = bandFor(scores.overall);
  return (
    <div data-testid="sa-score-cards" className="space-y-2">
      <div className="rounded-2xl bg-[#4c2889] text-white p-4 flex items-center justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-[0.16em] font-bold text-purple-200">Overall score</div>
          {band && <div className="text-xs font-semibold text-purple-100 mt-0.5">{band.label}</div>}
        </div>
        <div data-testid="sa-overall-score" className="text-3xl font-extrabold leading-none">
          {scores.overall}
          <span className="text-base font-bold text-purple-200">/100</span>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {SECTIONS.map((s) => {
          const v = scores.sections[s.key];
          const b = bandFor(v);
          return (
            <div key={s.key} data-testid={`sa-section-score-${s.key}`} className="rounded-xl border border-purple-100 bg-white p-3">
              <div className="text-[11px] font-semibold text-slate-600 leading-tight">{s.score_label}</div>
              <div className="text-xl font-extrabold text-[#4c2889] mt-1">{v}</div>
              {b && <div className="text-[10px] text-slate-500">{b.label}</div>}
              <div className="h-1.5 rounded-full bg-purple-50 mt-1.5 overflow-hidden">
                <div className="h-full bg-purple-600 rounded-full transition-[width] duration-700" style={{ width: `${v}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Delta({ from, to }) {
  const d = to - from;
  const cls = d > 0 ? "text-emerald-700" : d < 0 ? "text-rose-700" : "text-slate-500";
  return (
    <span className={`font-bold ${cls}`}>
      {from} → {to}
    </span>
  );
}

export function ProgressHistory({ history }) {
  if (!history.length) return null;
  const first = history[0].scores.sections;
  const latest = history[history.length - 1].scores.sections;
  return (
    <div data-testid="sa-progress" className="rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
      <h4 className="text-sm font-extrabold text-slate-900">Your Progress</h4>
      <ul data-testid="sa-progress-list" className="space-y-1">
        {history.map((h, i) => (
          <li key={h.id} data-testid={`sa-progress-row-${i}`} className="flex justify-between text-[13px] text-slate-700">
            <span>{entryLabel(history, i)}</span>
            <span className="font-bold text-[#4c2889]">{h.scores.overall}/100</span>
          </li>
        ))}
      </ul>
      {history.length > 1 ? (
        <ul className="space-y-1 border-t border-slate-100 pt-2">
          {SECTIONS.map((s) => (
            <li key={s.key} data-testid={`sa-progress-delta-${s.key}`} className="flex justify-between text-[13px] text-slate-700">
              <span>{s.score_label}</span>
              <Delta from={first[s.key]} to={latest[s.key]} />
            </li>
          ))}
        </ul>
      ) : (
        <p data-testid="sa-progress-first-note" className="text-[11px] text-slate-500 border-t border-slate-100 pt-2">
          This is your starting point. Your next Self-Assessment will show how each area has changed.
        </p>
      )}
    </div>
  );
}

export function CentralMessage() {
  return (
    <div data-testid="sa-central-message" className="rounded-2xl bg-purple-50 border border-dashed border-purple-300 px-4 py-3">
      <p className="text-[13px] leading-relaxed text-purple-950 font-medium" style={{ fontFamily: "Georgia, serif" }}>
        <i className="fa-solid fa-quote-left text-purple-400 mr-1.5"></i>
        {CONTENT.central_message}
      </p>
    </div>
  );
}

export function CycleStrip() {
  return (
    <div data-testid="sa-cycle-strip" className="flex flex-wrap items-center justify-center gap-1 text-[10.5px] font-bold text-purple-900">
      {CONTENT.cycle.map((c, i) => (
        <React.Fragment key={c}>
          <span className="px-2 py-1 rounded-full bg-white border border-purple-200">{c}</span>
          {i < CONTENT.cycle.length - 1 && <i className="fa-solid fa-arrow-right text-[9px] text-purple-400"></i>}
        </React.Fragment>
      ))}
    </div>
  );
}
