import React from "react";

const PATH_LABEL = {
  parent: "Co-Parenting Journey",
  court: "Court-Ordered Journey",
};

/**
 * GuideFollowupModal — iter231 "How's it going?" nudge.
 *
 * Shown on the next visit AFTER a parent picked a path (via
 * IntroChatBot or the Doors Gateway) but never opened their
 * first tile / assessment / tool. The Guide checks in with a
 * friendly two-CTA modal: "Show me my first assessment" (routes
 * back into the picked door) or "Not now, thanks" (dismisses
 * for a week).
 *
 * Copy stays deterministic (no LLM) so it matches the founder's
 * voice from IntroChatBot verbatim.
 *
 * Props:
 *   - open : bool
 *   - onClose : () => void
 *   - onDismissForWeek : () => void
 *   - onResume : () => void          // routes back into the chosen door
 *   - path : 'parent' | 'court'
 *   - daysSincePick : int
 *   - parentName : string | null
 */
export function GuideFollowupModal({
  open,
  onClose,
  onDismissForWeek,
  onResume,
  path,
  daysSincePick,
  parentName,
}) {
  if (!open) return null;
  const greeting = parentName ? `Hi ${parentName},` : "Hi there,";
  const label = PATH_LABEL[path] || "SA CoParents journey";
  const days = Math.max(1, Number(daysSincePick) || 1);

  return (
    <div
      className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 no-print"
      data-testid="guide-followup-modal"
    >
      <div className="bg-white w-full max-w-sm sm:rounded-2xl rounded-t-2xl shadow-xl flex flex-col">
        <div className="flex justify-between items-start border-b border-slate-100 p-3">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-purple-700 to-purple-900 flex items-center justify-center shrink-0">
              <i className="fa-solid fa-hands-holding-child text-white text-sm"></i>
            </div>
            <div className="min-w-0">
              <div className="text-[0.5625rem] font-bold text-purple-800 uppercase tracking-wider">
                Checking in
              </div>
              <h3 className="font-bold text-slate-800 text-sm truncate">
                SA CoParents Guide
              </h3>
            </div>
          </div>
          <button
            type="button"
            data-testid="guide-followup-close"
            onClick={onClose}
            aria-label="Close"
            className="text-slate-400 hover:text-slate-600 p-1 shrink-0"
          >
            <i className="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>

        <div
          className="p-3 space-y-3 bg-slate-50"
          data-testid="guide-followup-body"
        >
          <div className="p-2.5 bg-white border border-slate-200 rounded-2xl rounded-tl-sm text-[0.75rem] text-slate-800 leading-snug shadow-sm">
            {greeting} how’s it going?
          </div>
          <div className="p-2.5 bg-white border border-slate-200 rounded-2xl rounded-tl-sm text-[0.75rem] text-slate-800 leading-snug shadow-sm">
            You picked the <b>{label}</b>{" "}
            {days === 1 ? "yesterday" : `${days} days ago`} and I don’t
            think you’ve opened your first assessment yet.
          </div>
          <div className="p-2.5 bg-white border border-slate-200 rounded-2xl rounded-tl-sm text-[0.75rem] text-slate-800 leading-snug shadow-sm">
            No pressure — every family moves at its own pace. When
            you’re ready, I’ll take you straight there so you don’t
            have to hunt for it.
          </div>
        </div>

        <div className="p-3 space-y-2 border-t border-slate-100 bg-white">
          <button
            type="button"
            data-testid="guide-followup-resume"
            onClick={onResume}
            className={
              path === "court"
                ? "w-full py-2.5 bg-amber-700 hover:bg-amber-800 text-white rounded-lg font-bold text-xs"
                : "w-full py-2.5 bg-purple-800 hover:bg-purple-900 text-white rounded-lg font-bold text-xs"
            }
          >
            <i className="fa-solid fa-arrow-right mr-1"></i>
            Show me my first assessment
          </button>
          <button
            type="button"
            data-testid="guide-followup-dismiss-week"
            onClick={onDismissForWeek}
            className="w-full py-1.5 text-[0.6875rem] text-slate-500 hover:text-slate-700 underline"
          >
            Not now, thanks — remind me next week
          </button>
        </div>
      </div>
    </div>
  );
}
