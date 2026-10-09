import React from "react";

function CheckItem({ listKey, item, on, onToggle }) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={on}
      data-testid={`pp-check-item-${listKey}-${item.id}`}
      onClick={() => onToggle(listKey, item.id)}
      className={`w-full text-left rounded-xl border-2 p-3.5 flex items-start gap-3 transition-[border-color,background-color] ${
        on ? "border-[#4a2574] bg-[#f4f0fa]" : "border-slate-200 bg-white hover:border-purple-300 hover:bg-purple-50/40"
      }`}
    >
      <span className={`mt-0.5 shrink-0 w-5 h-5 rounded-md border-2 flex items-center justify-center ${on ? "border-[#4a2574] bg-[#4a2574] text-white" : "border-slate-300"}`}>
        {on && <i className="fa-solid fa-check text-[10px]"></i>}
      </span>
      <span className="text-sm font-semibold text-slate-900">{item.label}</span>
    </button>
  );
}

// One quick-check list (Child-Focused, Safeguards, Court-Order self-check, Professional Review); ticks autosave.
export function PpChecklist({ list, index, total, plan, onToggle, onNote, onBack, onNext }) {
  const ticked = plan.checks?.[list.key] || [];
  const last = index === total - 1;
  return (
    <div data-testid={`pp-check-${list.key}`} className="bg-white rounded-3xl border border-purple-100 shadow-lg p-5 sm:p-8 space-y-5">
      <div className="flex items-start gap-4">
        <div className="shrink-0 w-12 h-12 rounded-2xl bg-purple-100 text-[#4a2574] flex items-center justify-center text-xl">
          <i className={`fa-solid ${list.icon}`}></i>
        </div>
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wider text-[#8251b8]">
            Quick check {index + 1} of {total}
          </p>
          <h2 data-testid="pp-check-title" className="text-2xl sm:text-3xl font-extrabold text-[#2d1548]">{list.title}</h2>
          <p className="text-sm text-slate-600 mt-1">{list.intro}</p>
        </div>
      </div>
      {list.note && (
        <p data-testid="pp-check-note" className="text-xs text-amber-900 bg-amber-50 border border-amber-200 rounded-xl p-3">
          <i className="fa-solid fa-circle-info mr-1.5"></i>
          {list.note}
        </p>
      )}
      <div className="space-y-2.5">
        {list.items.map((it) => (
          <CheckItem key={it.id} listKey={list.key} item={it} on={ticked.includes(it.id)} onToggle={onToggle} />
        ))}
      </div>
      <div>
        <label htmlFor={`pp-notes-${list.key}`} className="text-sm font-bold text-slate-900">
          Anything to add? <span className="font-normal text-slate-500">(optional)</span>
        </label>
        <textarea
          id={`pp-notes-${list.key}`}
          data-testid={`pp-notes-${list.key}`}
          value={plan.notes[list.key] || ""}
          maxLength={1000}
          rows={3}
          onChange={(e) => onNote(list.key, e.target.value)}
          placeholder="Anything you want to remember or raise with a professional."
          className="mt-2 w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#8251b8]"
        />
      </div>
      <div className="flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <button
          type="button"
          data-testid="pp-check-back"
          onClick={onBack}
          className="px-5 py-3 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-sm font-semibold transition-colors"
        >
          <i className="fa-solid fa-arrow-left mr-2"></i>Back
        </button>
        <div className="flex items-center gap-3 justify-between sm:justify-end">
          <span data-testid="pp-check-count" className="text-xs text-slate-500">
            {ticked.length} of {list.items.length} ticked
          </span>
          <button
            type="button"
            data-testid="pp-check-next"
            onClick={onNext}
            className="px-6 py-3 rounded-xl bg-[#388e3c] hover:bg-[#2e7d32] text-white text-sm font-bold shadow-md transition-colors"
          >
            {last ? "See My Plan" : "Save & Continue"}
            <i className="fa-solid fa-arrow-right ml-2"></i>
          </button>
        </div>
      </div>
    </div>
  );
}
