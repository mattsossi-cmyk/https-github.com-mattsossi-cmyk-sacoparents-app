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

function MenuRow({ o, status, asked, onToggle, onOpen }) {
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
        <AskedTick testid={`${tp}-asked`} asked={asked} onToggle={onToggle} />
        <Status testid={`${tp}-status`} status={status} />
      </div>
    </li>
  );
}

// Court page menu: every assessment a professional may ask for, in any order, with an "Asked by my professional" tick.
export function CourtMenu({ statusFor, requested, onToggle, onOpen }) {
  return (
    <section data-testid="court-menu" className="scroll-mt-6">
      <h3 className="text-xl sm:text-2xl font-extrabold text-[#3B1C6B]">Your Court-Ordered Journey</h3>
      <p className="text-sm text-slate-600 mb-4 leading-relaxed">
        Your professional may ask you to complete one or more of these. Tick the ones you were asked for, then open them in any order.
      </p>
      <ul className="space-y-3">
        {MENU.map((o) => (
          <MenuRow key={o.key} o={o} status={statusFor(o.key)} asked={requested.includes(o.key)} onToggle={() => onToggle(o.key)} onOpen={() => onOpen(o.key)} />
        ))}
      </ul>
    </section>
  );
}
