import React from "react";

import { MENU, STATUS_PILL } from "./courtContent";

function Status({ testid, status }) {
  const [label, , icon] = STATUS_PILL[status];
  const tone = status === "done" ? "text-emerald-700" : status === "in_progress" ? "text-amber-700" : "text-slate-500";
  return (
    <span data-testid={testid} data-status={status} className={`inline-flex items-center gap-1 text-[11px] font-bold whitespace-nowrap ${tone}`}>
      <i className={`fa-solid ${icon}`}></i>
      {label}
    </span>
  );
}

function AskedTick({ testid, asked, onToggle }) {
  return (
    <button type="button" role="checkbox" aria-checked={asked} data-testid={testid} onClick={onToggle} className="inline-flex items-center gap-2 text-[12px] font-semibold text-[#3b1566] rounded-lg px-1 py-1 hover:bg-[#f2ebfc] transition-colors">
      <span className={`w-5 h-5 rounded-md border-2 grid place-items-center transition-colors ${asked ? "bg-[#5c2c8e] border-[#5c2c8e] text-white" : "bg-white border-slate-300 text-transparent"}`}>
        <i className="fa-solid fa-check text-[10px]" aria-hidden="true"></i>
      </span>
      Asked by my professional
    </button>
  );
}

function ProNote({ testid, asked, name }) {
  return asked ? (
    <span data-testid={testid} className="inline-flex items-center gap-1 rounded-full bg-[#f2ebfc] text-[#4a1d7a] px-2 py-0.5 text-[10.5px] font-bold">
      <i className="fa-solid fa-user-tie" aria-hidden="true"></i>
      Set by {name || "your professional"}
    </span>
  ) : (
    <span data-testid={testid} className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-800">
      <i className="fa-solid fa-circle-info" aria-hidden="true"></i>
      Your professional asked for this
    </span>
  );
}

function MenuRow({ o, status, asked, pro, proName, onToggle, onOpen }) {
  const tp = `court-menu-${o.key}`;
  return (
    <li data-testid={tp} data-asked={asked ? "true" : "false"} className={`rounded-2xl border bg-white shadow-sm transition-[box-shadow,border-color] hover:shadow-md ${asked ? "border-[#5c2c8e] ring-2 ring-[#5c2c8e]/15" : "border-purple-100"}`}>
      <button type="button" data-testid={`${tp}-open`} onClick={onOpen} className="w-full text-left p-3.5 sm:p-4 flex items-start gap-3 sm:gap-4">
        <span className={`w-10 h-10 sm:w-12 sm:h-12 rounded-2xl ${o.tile} text-white grid place-items-center text-lg shrink-0 shadow-sm`}>
          <i className={`fa-solid ${o.icon}`} aria-hidden="true"></i>
        </span>
        <span className="flex-1 min-w-0">
          <span className="block text-base sm:text-lg font-bold text-[#3B1C6B] leading-tight">{o.title}</span>
          <span className="block text-xs text-slate-600 mt-1 leading-relaxed">{o.body}</span>
        </span>
        <i className="fa-solid fa-chevron-right text-[#5c2c8e] pt-1" aria-hidden="true"></i>
      </button>
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-purple-50 px-3 sm:px-4 py-1.5">
        <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <AskedTick testid={`${tp}-asked`} asked={asked} onToggle={onToggle} />
          {pro && <ProNote testid={`${tp}-pro-note`} asked={asked} name={proName} />}
        </span>
        <Status testid={`${tp}-status`} status={status} />
      </div>
    </li>
  );
}

function Summary({ done, total }) {
  if (!total)
    return (
      <p data-testid="court-menu-summary" className="text-sm text-slate-600 mb-4 leading-relaxed">
        No assessments are marked as requested yet. Accept your court invite, or tick the ones your professional asked for below.
      </p>
    );
  const left = total - done;
  return (
    <div data-testid="court-menu-summary" className="mb-4">
      <p className="text-sm text-slate-700 leading-relaxed">
        <strong data-testid="court-menu-done-count" className="text-emerald-700">{done} of {total} done</strong>
        {" · "}
        <strong data-testid="court-menu-remaining-count" className={left ? "text-amber-700" : "text-emerald-700"}>{left} remaining</strong>
        <span className="text-slate-500"> · open them in any order</span>
      </p>
      <div className="mt-2 w-full bg-purple-100 rounded-full h-2">
        <div className="bg-[#5c2c8e] h-2 rounded-full transition-[width] duration-500" style={{ width: `${Math.round((done / total) * 100)}%` }} />
      </div>
    </div>
  );
}

// The one requested-assessments list: requested items first (done and remaining), then the others you can tick.
export function CourtMenu({ statusFor, requested, proKeys = [], proName, onToggle, onOpen }) {
  const asked = MENU.filter((o) => requested.includes(o.key));
  const others = MENU.filter((o) => !requested.includes(o.key));
  const done = asked.filter((o) => statusFor(o.key) === "done").length;
  const row = (o) => (
    <MenuRow key={o.key} o={o} status={statusFor(o.key)} asked={requested.includes(o.key)} pro={proKeys.includes(o.key)} proName={proName} onToggle={() => onToggle(o.key)} onOpen={() => onOpen(o.key)} />
  );
  return (
    <section data-testid="court-menu" className="scroll-mt-6">
      <h3 className="text-xl sm:text-2xl font-extrabold text-[#3B1C6B]">Your requested assessments</h3>
      <Summary done={done} total={asked.length} />
      {asked.length > 0 && <ul data-testid="court-menu-requested" className="space-y-3">{asked.map(row)}</ul>}
      {others.length > 0 && (
        <>
          <p data-testid="court-menu-others-label" className={`text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2 ${asked.length ? "mt-6" : ""}`}>
            {asked.length ? "Not requested · tick any others your professional asked for" : "All assessments"}
          </p>
          <ul data-testid="court-menu-others" className="space-y-3">{others.map(row)}</ul>
        </>
      )}
    </section>
  );
}
