import React, { useState } from "react";
import { toast } from "sonner";

const fmt = (iso) => new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

function GoalRow({ entry, last, onReached }) {
  const [busy, setBusy] = useState(false);
  const reached = !!entry.reached_at;
  const toggle = async () => {
    setBusy(true);
    try {
      await onReached(entry.id, !reached);
      if (!reached) toast.success("Goal reached. That's real progress.");
    } catch {
      toast.error("Couldn't update this goal. Please try again.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <li data-testid={`sa-goal-row-${entry.id}`} className="relative pl-7 pb-5 last:pb-0">
      {!last && <span className="absolute left-[9px] top-5 bottom-0 w-0.5 bg-purple-200" aria-hidden="true" />}
      <span className={`absolute left-0 top-0.5 w-5 h-5 rounded-full grid place-items-center text-white text-[0.625rem] ${reached ? "bg-emerald-600" : "bg-purple-700"}`}>
        <i className={`fa-solid ${reached ? "fa-check" : "fa-flag"}`} aria-hidden="true"></i>
      </span>
      <p className="text-[0.8125rem] font-semibold text-slate-900 break-words">{entry.goal}</p>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-[0.6875rem]">
        <span data-testid={`sa-goal-set-${entry.id}`} className="text-slate-600">Set {fmt(entry.completed_at)}</span>
        {reached ? (
          <span data-testid={`sa-goal-reached-${entry.id}`} className="font-bold text-emerald-700">Reached {fmt(entry.reached_at)}</span>
        ) : (
          <span data-testid={`sa-goal-open-${entry.id}`} className="font-semibold text-amber-700">In progress</span>
        )}
        <button
          type="button"
          data-testid={`sa-goal-toggle-${entry.id}`}
          onClick={toggle}
          disabled={busy}
          className={`rounded-full px-2.5 py-1 font-bold transition-colors disabled:opacity-60 ${reached ? "text-slate-500 hover:text-slate-800" : "bg-emerald-600 hover:bg-emerald-700 text-white"}`}
        >
          {busy ? <i className="fa-solid fa-spinner fa-spin"></i> : reached ? "Undo" : "Mark as reached"}
        </button>
      </div>
    </li>
  );
}

// Every goal set at the end of a Self-Assessment, newest first, with the date set and the date reached.
export function GoalTimeline({ history, onReached }) {
  const goals = history.filter((h) => (h.goal || "").trim()).reverse();
  return (
    <div data-testid="sa-goal-timeline" className="rounded-2xl border border-slate-200 bg-white p-4">
      <h5 className="text-sm font-extrabold text-slate-900 mb-3">My communication goals</h5>
      {goals.length === 0 ? (
        <p data-testid="sa-goal-timeline-empty" className="text-[0.75rem] text-slate-500">
          No goals yet. Each Self-Assessment ends with setting one, and it will show up here.
        </p>
      ) : (
        <ol>
          {goals.map((g, i) => (
            <GoalRow key={g.id} entry={g} last={i === goals.length - 1} onReached={onReached} />
          ))}
        </ol>
      )}
    </div>
  );
}
