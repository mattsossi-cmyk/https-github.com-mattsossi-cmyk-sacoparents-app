import React from "react";

import { CourtDialog } from "./CourtDialog";
import { STATUS_PILL } from "./courtContent";

export function CourtStepDialog({ step, item, onClose, onOpen, onAskAi }) {
  if (!step) return null;
  const status = item?.status || "loading";
  const [label, tone, icon] = STATUS_PILL[status];
  const note = item ? (status === "done" ? item.detail : item.detail || "You haven't started this step yet.") : "";
  return (
    <CourtDialog open onClose={onClose} testid="court-step-dialog" title={step.title} desc={step.body}>
      <div data-testid="court-step-dialog-progress" className="bg-[#f2ebfc] border border-[#e7dbf8] rounded-xl px-4 py-3 mb-5">
        <p className="text-[11px] font-extrabold uppercase tracking-wider text-[#5c2c8e] mb-1.5">Your progress</p>
        <span data-testid="court-step-dialog-status" className={`inline-flex items-center gap-1.5 text-[11px] font-bold px-2.5 py-1 rounded-full border border-black/5 ${tone}`}>
          <i className={`fa-solid ${icon}`}></i>
          {label}
        </span>
        {note && <p data-testid="court-step-dialog-detail" className="text-xs text-[#5f6368] mt-1.5">{note}</p>}
      </div>
      <div className="flex flex-col sm:flex-row gap-2.5">
        <button
          type="button"
          data-testid="court-step-dialog-open"
          onClick={onOpen}
          className="flex-1 bg-[#2fa144] hover:bg-[#268537] text-white font-bold py-3 px-5 rounded-lg transition-colors"
        >
          {status === "done" ? `Review Step ${step.n}` : status === "in_progress" ? `Continue Step ${step.n}` : `Start Step ${step.n}`}
          <i className="fa-solid fa-arrow-right ml-2"></i>
        </button>
        <button
          type="button"
          data-testid="court-step-dialog-ask-ai"
          onClick={onAskAi}
          className="flex-1 bg-[#f2ebfc] hover:bg-[#e7dbf8] text-[#3b1566] border border-[#e7dbf8] font-bold py-3 px-5 rounded-lg transition-colors"
        >
          <i className="fa-solid fa-wand-magic-sparkles mr-2"></i>Ask Emergent AI
        </button>
      </div>
    </CourtDialog>
  );
}
