/**
 * DeepDiveFocusPanel — reusable "one-question-per-screen" wrapper for the
 * Med / Edu / Psych deep-dive pages.
 *
 * Contract:
 *   - `items` = the current section's items (as supplied by the schema).
 *   - `renderItem(item)` = the caller's existing Item renderer.
 *   - Emits `onCrossToPrevSection` / `onCrossToNextSection` when the parent
 *     hits Previous on question 1 or Next on the last question.
 *   - Persists nothing itself — the parent handles auto-save.
 *
 * Design notes:
 *   - Default is ON (`focusMode=true` in the parent). Parent controls it.
 *   - Auto-advance is deliberately absent here — the deep-dive items mix
 *     likert / single / multi / textarea. Any multi or textarea would
 *     jump before the parent finishes typing. Parent taps Next.
 */
import React from "react";
import { ArrowLeft, ArrowRight, LayoutList } from "lucide-react";

export function FocusModeToggle({ focusMode, onToggle, testid = "deepdive-toggle-focus" }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={!focusMode}
      title={focusMode ? "Show every question in this section" : "Focus on one question at a time"}
      data-testid={testid}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[0.6875rem] font-semibold border border-[#D6CFE8] text-[#3D1A78] hover:border-[#3D1A78] shrink-0"
    >
      <LayoutList size={12} />
      {focusMode ? "Show all" : "One at a time"}
    </button>
  );
}

export function FocusItemProgress({ qIdx, total, sectionIdx, sectionTotal, testid = "deepdive-focus-progress" }) {
  const pct = total > 0 ? Math.round(((qIdx + 1) / total) * 100) : 0;
  return (
    <div className="mt-3">
      <div className="flex items-center justify-between text-[0.6875rem] text-[#4B4567] mb-1">
        <span data-testid={testid}>
          Question {Math.min(qIdx + 1, total)} of {total} · Section {sectionIdx + 1} of {sectionTotal}
        </span>
      </div>
      <div className="h-1.5 w-full bg-[#EEE9F7] rounded-full overflow-hidden">
        <div
          className="h-full bg-[#3D1A78] transition-all"
          style={{ width: `${pct}%` }}
          data-testid={`${testid}-bar`}
        />
      </div>
    </div>
  );
}

export function FocusItemCard({ item, children, testid }) {
  return (
    <div
      key={item.id}
      className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-6 sm:p-8 shadow-sm animate-[fadeUp_240ms_ease-out]"
      data-testid={testid}
    >
      {children}
    </div>
  );
}

export function FocusItemNav({
  onPrev,
  onNext,
  canPrev,
  isLast,
  onFinish,
  finishLabel = "Generate report",
  finishTestid,
  prevTestid,
  nextTestid,
  busy,
}) {
  return (
    <div className="mt-6 sticky bottom-4 bg-white/85 backdrop-blur border border-[#E5E0EE] rounded-full p-2 flex items-center justify-between gap-2">
      <button
        type="button"
        onClick={onPrev}
        disabled={!canPrev}
        data-testid={prevTestid}
        className="inline-flex items-center gap-1 px-4 py-2 rounded-full text-sm border border-[#E5E0EE] text-[#3D1A78] disabled:opacity-40"
      >
        <ArrowLeft size={13} /> Previous
      </button>
      {isLast ? (
        <button
          type="button"
          onClick={onFinish}
          disabled={busy}
          data-testid={finishTestid}
          className="inline-flex items-center gap-1 px-4 py-2 rounded-full text-sm bg-[#3D1A78] text-white hover:brightness-110 disabled:opacity-60"
        >
          {finishLabel}
        </button>
      ) : (
        <button
          type="button"
          onClick={onNext}
          data-testid={nextTestid}
          className="inline-flex items-center gap-1 px-4 py-2 rounded-full text-sm bg-[#3D1A78] text-white hover:brightness-110"
        >
          Next <ArrowRight size={13} />
        </button>
      )}
    </div>
  );
}
