import React from "react";

// Small Self Journey entry to the quick check (the retake once it's been done). Wording stays neutral.
export function SafetyScreenLink({ done, onOpen }) {
  return (
    <button
      type="button"
      data-testid="self-safety-screen-link"
      onClick={onOpen}
      className="inline-flex items-center gap-1.5 min-h-9 px-3 py-1.5 rounded-full border border-[#E5E0EE] bg-white text-[#3D1A78] text-xs font-semibold hover:bg-[#F5F1FB] transition-colors"
    >
      <i className="fa-solid fa-clipboard-check" aria-hidden="true"></i>
      {done ? "Quick check-in · retake" : "Quick check-in"}
    </button>
  );
}
