import React from "react";

// Green "next step" arrow placed between stacked journey pictures.
export function FlowArrow({ testid, label }) {
  return (
    <div data-testid={testid} aria-hidden="true" className="flex flex-col items-center -my-1 select-none">
      <span className="w-1.5 h-8 rounded-full bg-gradient-to-b from-emerald-200 to-emerald-500" />
      <span className="sa-arrow-nudge w-[107px] h-[107px] sm:w-[147px] sm:h-[147px] rounded-full bg-emerald-500 text-white flex items-center justify-center">
        <i className="fa-solid fa-arrow-down text-[54px] sm:text-[74px]"></i>
      </span>
      {label && <span className="mt-1.5 text-[11px] font-bold uppercase tracking-wider text-emerald-700">{label}</span>}
    </div>
  );
}
