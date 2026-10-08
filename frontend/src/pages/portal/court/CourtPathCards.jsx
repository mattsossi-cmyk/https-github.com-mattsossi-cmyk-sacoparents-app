import React from "react";

const card =
  "bg-white rounded-2xl p-5 sm:p-6 border border-purple-100 shadow-sm flex items-start gap-4 sm:gap-5 transition-[transform,box-shadow] duration-200 hover:-translate-y-0.5 hover:shadow-md";
const iconBox =
  "w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-purple-100 text-purple-800 flex items-center justify-center text-xl sm:text-2xl shrink-0";

function ModuleRow({ m, onOpen }) {
  return (
    <button
      type="button"
      data-testid={`court-module-${m.key}`}
      data-status={m.status}
      onClick={() => onOpen(m)}
      className="w-full text-left bg-slate-50 hover:bg-purple-50 border border-slate-200 hover:border-purple-200 rounded-xl px-3 py-2 flex items-center gap-3 transition-colors"
    >
      <span className="shrink-0 w-7 h-7 rounded-lg bg-purple-100 text-purple-800 font-bold text-xs flex items-center justify-center">{m.letter}</span>
      <span className="min-w-0 flex-1 text-xs font-semibold text-slate-800">{m.title}</span>
      <span className={`shrink-0 text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded-full border ${m.chip}`}>{m.label}</span>
      <i className="fa-solid fa-arrow-right text-slate-400 text-[10px]"></i>
    </button>
  );
}

function ActionCard({ testid, icon, title, body, cta, onClick, busy }) {
  return (
    <button type="button" data-testid={testid} onClick={onClick} disabled={busy} className={`${card} w-full text-left disabled:opacity-70`}>
      <div className={iconBox}>
        <i className={`fa-solid ${icon}`}></i>
      </div>
      <div className="min-w-0">
        <h3 className="text-lg sm:text-xl font-bold text-[#3B1C6B]">{title}</h3>
        <p className="text-sm text-slate-600 mt-1">{body}</p>
        <span className="inline-flex items-center gap-1.5 mt-2 text-xs font-bold text-purple-700">
          {busy ? <i className="fa-solid fa-spinner fa-spin"></i> : <i className="fa-solid fa-arrow-right"></i>}
          {cta}
        </span>
      </div>
    </button>
  );
}

export function CourtPathCards({ modules, doneCount, onOpenModule, onReports, onSupportChild, pdfBusy }) {
  return (
    <div data-testid="court-path-cards" className="space-y-4">
      <div data-testid="court-card-assessments" className={card}>
        <div className={iconBox}>
          <i className="fa-solid fa-clipboard-list"></i>
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <h3 className="text-lg sm:text-xl font-bold text-[#3B1C6B]">Complete Assessments</h3>
            <span data-testid="court-modules-done" className="text-[10px] font-bold uppercase tracking-wider text-purple-700 bg-purple-50 border border-purple-100 px-2 py-0.5 rounded-full">
              {doneCount} of {modules.length} complete
            </span>
          </div>
          <p className="text-sm text-slate-600 mt-1">Follow your court order requirements through three structured alignment modules.</p>
          <div className="mt-3 space-y-2">
            {modules.map((m) => (
              <ModuleRow key={m.key} m={m} onOpen={onOpenModule} />
            ))}
          </div>
        </div>
      </div>
      <ActionCard
        testid="court-card-reports"
        icon="fa-file-contract"
        title="Generate Reports"
        body="Your responses are organized into court-ready reports for your professional and the court."
        cta="Download court-ready PDF"
        onClick={onReports}
        busy={pdfBusy}
      />
      <ActionCard
        testid="court-card-child"
        icon="fa-people-group"
        title="Support Your Child"
        body="Focus on your child's needs and move forward with clarity, reducing litigation friction."
        cta="Open your child's needs"
        onClick={onSupportChild}
      />
    </div>
  );
}
