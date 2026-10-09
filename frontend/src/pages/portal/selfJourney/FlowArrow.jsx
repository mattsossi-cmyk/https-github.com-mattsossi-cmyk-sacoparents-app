import React from "react";

// Green "next step" arrow placed between stacked journey pictures.
export function FlowArrow({ testid, label }) {
  return (
    <div data-testid={testid} aria-hidden="true" className="flex flex-col items-center -my-1 select-none">
      <span className="w-1.5 h-8 rounded-full bg-gradient-to-b from-emerald-200 to-emerald-500" />
      <span className="sa-arrow-nudge w-40 h-40 sm:w-[220px] sm:h-[220px] rounded-full bg-emerald-500 text-white shadow-[0_18px_40px_-10px_rgba(16,185,129,0.65)] ring-8 sm:ring-[12px] ring-emerald-100 flex items-center justify-center">
        <i className="fa-solid fa-arrow-down text-[80px] sm:text-[110px]"></i>
      </span>
      {label && <span className="mt-1.5 text-[11px] font-bold uppercase tracking-wider text-emerald-700">{label}</span>}
    </div>
  );
}
