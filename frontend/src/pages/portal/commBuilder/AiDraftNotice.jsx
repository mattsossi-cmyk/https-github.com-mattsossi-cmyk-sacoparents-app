import React from "react";

// Shown directly above every draft box that can be sent for AI suggested wording.
export function AiDraftNotice({ testid, className = "" }) {
  return (
    <p data-testid={testid} role="note" className={`flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-[11.5px] leading-relaxed text-amber-950 ${className}`}>
      <i className="fa-solid fa-circle-info mt-0.5 text-amber-700" aria-hidden="true"></i>
      <span>
        <strong>Before you type:</strong> when you tap Get suggested wording, this draft is sent to an outside AI service to suggest wording. Leave out full
        names, addresses, and medical, school or other sensitive details. Nothing is sent to your co-parent.
      </span>
    </p>
  );
}
