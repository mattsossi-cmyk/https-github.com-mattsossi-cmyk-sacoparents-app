import React from "react";
import { toast } from "sonner";

import { fillInTemplate } from "./fillInTemplate";

// Shown when AI didn't return wording that kept every date, time, question and boundary. No tone rating is shown.
export function SuggestUnavailable({ tp, raw, greyRock, onRetry, onUseTemplate, busy }) {
  const template = fillInTemplate(raw, greyRock);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(template);
      toast.success("Template copied. Replace the [brackets] before you send it.");
    } catch {
      toast.error("Couldn't copy. Please select the text and copy it.");
    }
  };
  const btn = "text-xs font-bold px-3 py-1.5 rounded-lg transition-colors disabled:opacity-60";
  return (
    <div data-testid={`${tp}-unavailable`} className="rounded-xl bg-white text-slate-800 border border-amber-200 p-4 space-y-3">
      <div>
        <p data-testid={`${tp}-unavailable-title`} className="text-sm font-bold text-amber-900">
          <i className="fa-solid fa-circle-exclamation mr-1.5" aria-hidden="true"></i>Suggested wording isn&rsquo;t available right now
        </p>
        <p className="text-[0.75rem] text-slate-600 mt-1 leading-relaxed">AI didn&rsquo;t check this draft, so there&rsquo;s no tone rating. Try again, or start from the fill-in template below.</p>
      </div>
      <button type="button" data-testid={`${tp}-retry`} onClick={onRetry} disabled={busy} className={`${btn} bg-purple-700 hover:bg-purple-800 text-white`}>
        <i className={`fa-solid ${busy ? "fa-spinner fa-spin" : "fa-rotate-right"} mr-1.5`} aria-hidden="true"></i>Try again
      </button>
      <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-3">
        <p className="text-[0.625rem] font-bold uppercase tracking-wider text-slate-700">Fill-in template &middot; not checked by AI</p>
        <p className="text-[0.6875rem] text-slate-500 mb-2">Your own questions, dates and times are copied exactly. Replace the [brackets] before you send.</p>
        <pre data-testid={`${tp}-template`} className="whitespace-pre-wrap break-words font-sans text-[0.75rem] text-slate-800 leading-relaxed">{template}</pre>
        <div className="flex flex-wrap gap-2 mt-3">
          <button type="button" data-testid={`${tp}-template-copy`} onClick={copy} className={`${btn} bg-white border border-slate-300 hover:bg-slate-100 text-slate-800`}>
            <i className="fa-regular fa-copy mr-1.5" aria-hidden="true"></i>Copy template
          </button>
          <button type="button" data-testid={`${tp}-template-use`} onClick={() => onUseTemplate(template)} className={`${btn} bg-white border border-slate-300 hover:bg-slate-100 text-slate-800`}>
            <i className="fa-solid fa-pen mr-1.5" aria-hidden="true"></i>Put in draft box
          </button>
        </div>
      </div>
    </div>
  );
}
