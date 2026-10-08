import React from "react";

import { useCourtChecklist } from "./useCourtChecklist";

const ICON = {
  done: "fa-solid fa-circle-check text-emerald-600",
  in_progress: "fa-solid fa-circle-half-stroke text-amber-500",
  todo: "fa-regular fa-circle text-slate-300",
};

function Row({ item }) {
  const done = item.status === "done";
  return (
    <li data-testid={`court-checklist-item-${item.key}`} data-status={item.status} className="flex items-start gap-3 py-2.5">
      <i className={`${ICON[item.status]} text-base mt-0.5 shrink-0`} aria-hidden="true"></i>
      <div className="min-w-0 flex-1">
        <p className={`text-sm font-semibold ${done ? "text-slate-800" : "text-slate-700"}`}>{item.label}</p>
        <p className={`text-[11px] leading-snug ${done ? "text-emerald-700" : item.status === "in_progress" ? "text-amber-700" : "text-slate-500"}`}>
          {done ? item.detail : item.detail ? `${item.detail}. ${item.hint}` : item.hint}
        </p>
      </div>
    </li>
  );
}

export function CourtChecklistCard({ modules, courtKey, hidden }) {
  const { data, error, load, download, downloading } = useCourtChecklist({ modules, courtKey, hidden });
  const pct = data ? Math.round((data.done / data.total) * 100) : 0;
  return (
    <div data-testid="court-checklist-card" className="bg-white rounded-2xl p-6 border border-purple-100 shadow-md mt-6">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h4 className="text-sm font-extrabold text-[#3B1C6B] uppercase tracking-wider flex items-center gap-2">
            <i className="fa-solid fa-list-check text-purple-600"></i> Your Court Checklist
          </h4>
          <p className="text-[11px] text-slate-500 mt-0.5">What's done and what's left. Bring it to your mediator.</p>
        </div>
        {data && (
          <span data-testid="court-checklist-count" className="text-[10px] font-bold uppercase tracking-wider text-purple-700 bg-purple-50 border border-purple-100 px-2 py-0.5 rounded-full">
            {data.done} of {data.total} done
          </span>
        )}
      </div>
      {error ? (
        <div data-testid="court-checklist-error" className="mt-4 text-xs text-rose-700">
          We couldn't load your checklist.{" "}
          <button type="button" data-testid="court-checklist-retry" onClick={load} className="font-bold underline">
            Try again
          </button>
        </div>
      ) : !data ? (
        <div data-testid="court-checklist-loading" className="mt-4 space-y-2 animate-pulse">
          <div className="h-3 w-full rounded bg-purple-100" />
          <div className="h-3 w-5/6 rounded bg-slate-100" />
          <div className="h-3 w-2/3 rounded bg-slate-100" />
        </div>
      ) : (
        <>
          <div className="mt-4 w-full bg-purple-100 rounded-full h-2">
            <div data-testid="court-checklist-bar" className="bg-purple-600 h-2 rounded-full transition-[width] duration-500" style={{ width: `${pct}%` }} />
          </div>
          <ul data-testid="court-checklist-list" className="mt-2 divide-y divide-purple-50">
            {data.items.map((it) => (
              <Row key={it.key} item={it} />
            ))}
          </ul>
        </>
      )}
      <button
        type="button"
        data-testid="court-checklist-download"
        onClick={download}
        disabled={downloading || !data}
        className="mt-4 w-full py-3 px-4 bg-purple-900 hover:bg-purple-950 disabled:opacity-60 text-white text-xs font-bold rounded-xl shadow transition-colors flex items-center justify-center gap-2"
      >
        <i className={`fa-solid ${downloading ? "fa-spinner fa-spin" : "fa-file-arrow-down"}`}></i>
        <span>Download Checklist PDF</span>
      </button>
    </div>
  );
}
