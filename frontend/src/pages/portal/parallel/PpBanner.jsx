import React from "react";

// Wide Self Journey banner that opens the Parallel Parenting Option Builder.
export function PpBanner({ onOpen }) {
  return (
    <button
      type="button"
      data-testid="door-self-card-parallel"
      onClick={onOpen}
      className="relative w-full overflow-hidden text-left rounded-2xl bg-gradient-to-r from-purple-900 to-indigo-900 text-white p-4 shadow-md hover:shadow-lg transition-[box-shadow,transform] hover:-translate-y-0.5"
    >
      <span className="absolute -bottom-8 -left-8 w-28 h-28 bg-purple-500/25 rounded-full blur-2xl" />
      <span className="absolute -top-8 -right-8 w-28 h-28 bg-indigo-400/25 rounded-full blur-2xl" />
      <span className="relative flex items-center gap-3">
        <span className="shrink-0 w-12 h-12 rounded-full bg-white/15 flex items-center justify-center">
          <i className="fa-solid fa-people-arrows text-lg"></i>
        </span>
        <span className="min-w-0 flex-1">
          <span className="inline-flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider bg-white/15 px-2 py-0.5 rounded-full text-purple-100">
            <i className="fa-solid fa-shield-halved"></i> Independent Planning Tool
          </span>
          <span className="block text-sm font-black mt-1">Parallel Parenting Option Builder</span>
          <span className="block text-[11px] text-purple-100 leading-snug">
            Parent separately. Support your child together. 6 short steps, a guide chat and a plan PDF.
          </span>
        </span>
        <span className="shrink-0 w-8 h-8 rounded-full bg-white/15 flex items-center justify-center">
          <i className="fa-solid fa-chevron-right text-xs"></i>
        </span>
      </span>
    </button>
  );
}
