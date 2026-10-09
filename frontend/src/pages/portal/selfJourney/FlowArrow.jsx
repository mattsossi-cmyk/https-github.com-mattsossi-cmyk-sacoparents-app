import React from "react";

// Green "next step" arrow placed between stacked journey pictures.
export function FlowArrow({ testid, label }) {
  return (
    <div data-testid={testid} aria-hidden="true" className="flex flex-col items-center -my-1 select-none">
      <span className="w-0.5 h-4 rounded-full bg-gradient-to-b from-emerald-200 to-emerald-500" />
      <span className="sa-arrow-nudge w-11 h-11 rounded-full bg-emerald-500 text-white shadow-[0_6px_16px_-4px_rgba(16,185,129,0.6)] ring-4 ring-emerald-100 flex items-center justify-center">
        <i className="fa-solid fa-arrow-down text-lg"></i>
      </span>
      {label && <span className="mt-1.5 text-[11px] font-bold uppercase tracking-wider text-emerald-700">{label}</span>}
    </div>
  );
}
