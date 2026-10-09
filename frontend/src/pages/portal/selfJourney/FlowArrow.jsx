import React from "react";

// Glowing green "next step" arrow between journey steps; tapping scrolls to the step whose data-testid is `to`.
export function FlowArrow({ testid, to, label, step, done = false }) {
  const go = () => {
    const el = document.querySelector(`[data-testid="${to}"]`);
    if (!el) return;
    el.style.scrollMarginTop = "76px";
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  return (
    <div className="flex flex-col items-center -my-1 select-none">
      <span aria-hidden="true" className="w-1.5 h-8 rounded-full bg-gradient-to-b from-emerald-200 to-emerald-500" />
      <button
        type="button"
        data-testid={testid}
        onClick={go}
        aria-label={`Go to the next step${step ? ` (${step}${done ? ", finished" : ""})` : ""}: ${label}`}
        title={label}
        className="sa-arrow-nudge relative w-[107px] h-[107px] sm:w-[147px] sm:h-[147px] rounded-full bg-emerald-500 hover:bg-emerald-600 text-white flex items-center justify-center cursor-pointer transition-colors focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-[10px] focus-visible:outline-emerald-700"
      >
        <i className="fa-solid fa-arrow-down text-[54px] sm:text-[74px]"></i>
        {step && (
          <span
            data-testid={`${testid}-step`}
            data-done={done ? "true" : "false"}
            className={`absolute -top-1 -right-4 sm:-right-3 whitespace-nowrap rounded-full border-2 text-[11px] sm:text-xs font-extrabold px-2.5 py-1 shadow-md transition-colors ${done ? "bg-purple-700 border-purple-200 text-white" : "bg-white border-emerald-200 text-emerald-700"}`}
          >
            {done && <i className="fa-solid fa-check mr-1"></i>}
            {step}
          </span>
        )}
      </button>
    </div>
  );
}
