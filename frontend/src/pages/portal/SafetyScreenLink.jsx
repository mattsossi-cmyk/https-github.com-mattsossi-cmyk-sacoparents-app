import React from "react";

// Small Self Journey entry to the quick Safety Screen (the retake once it's been done).
export function SafetyScreenLink({ done, onOpen }) {
  return (
    <button
      type="button"
      data-testid="self-safety-screen-link"
      onClick={onOpen}
      className="inline-flex items-center gap-1.5 min-h-9 px-3 py-1.5 rounded-full border border-rose-200 bg-white text-rose-800 text-xs font-semibold hover:bg-rose-50 transition-colors"
    >
      <i className="fa-solid fa-shield-heart" aria-hidden="true"></i>
      {done ? "Safety Screen · retake" : "Safety Screen"}
    </button>
  );
}
