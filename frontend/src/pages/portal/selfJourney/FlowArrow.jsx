import React from "react";

const SIZES = {
  lg: {
    line: "w-1.5 h-8",
    btn: "w-[107px] h-[107px] sm:w-[147px] sm:h-[147px]",
    icon: "text-[54px] sm:text-[74px]",
    badge: "-top-1 -right-4 sm:-right-3 text-[0.6875rem] sm:text-xs px-2.5 py-1",
    glow: "",
  },
  sm: {
    line: "w-1 h-4",
    btn: "w-[54px] h-[54px] sm:w-[74px] sm:h-[74px]",
    icon: "text-[27px] sm:text-[37px]",
    badge: "-top-1.5 left-[72%] text-[0.625rem] sm:text-[0.6875rem] px-2 py-0.5",
    glow: "sa-arrow-sm",
  },
};

// Smooth-scrolls to the element whose data-testid is `to`, clearing the sticky header.
export function scrollToTestId(to) {
  const el = document.querySelector(`[data-testid="${to}"]`);
  if (!el) return;
  el.style.scrollMarginTop = "76px";
  el.scrollIntoView({ behavior: "smooth", block: "start" });
}

// Glowing green "next step" arrow between journey steps; tap scrolls to the step `to`.
export function FlowArrow({ testid, to, label, step, done = false, size = "lg" }) {
  const s = SIZES[size];
  return (
    <div className="flex flex-col items-center -my-1 select-none">
      <span aria-hidden="true" className={`${s.line} rounded-full bg-gradient-to-b from-emerald-200 to-emerald-500`} />
      <button
        type="button"
        data-testid={testid}
        onClick={() => scrollToTestId(to)}
        aria-label={`Go to the next step${step ? ` (${step}${done ? ", finished" : ""})` : ""}: ${label}`}
        title={label}
        className={`sa-arrow-nudge ${s.glow} relative ${s.btn} rounded-full bg-emerald-500 hover:bg-emerald-600 text-white flex items-center justify-center cursor-pointer transition-colors focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-[10px] focus-visible:outline-emerald-700`}
      >
        <i className={`fa-solid fa-arrow-down ${s.icon}`}></i>
        {step && (
          <span
            data-testid={`${testid}-step`}
            data-done={done ? "true" : "false"}
            className={`absolute ${s.badge} whitespace-nowrap rounded-full border-2 font-extrabold shadow-md transition-colors ${done ? "bg-purple-700 border-purple-200 text-white" : "bg-white border-emerald-200 text-emerald-700"}`}
          >
            {done && <i className="fa-solid fa-check mr-1"></i>}
            {step}
          </span>
        )}
      </button>
    </div>
  );
}
