import React from "react";

const btn =
  "rounded-2xl bg-white border border-[#e0d5ed] hover:border-[#5c2c8e] hover:bg-[#f2ebfc] px-4 py-3.5 text-left flex items-center gap-3 transition-colors disabled:opacity-60";

function Tool({ testid, icon, title, sub, onClick, busy, tone = "bg-[#f2ebfc] text-[#5c2c8e]", className = "" }) {
  return (
    <button type="button" data-testid={testid} onClick={onClick} disabled={busy} className={`${btn} ${className}`}>
      <span className={`shrink-0 w-10 h-10 rounded-xl flex items-center justify-center ${tone}`}>
        <i className={`fa-solid ${busy ? "fa-spinner fa-spin" : icon}`}></i>
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-bold text-[#3b1566] break-words">{title}</span>
        <span data-testid={`${testid}-sub`} className="block text-[11px] text-[#5f6368] break-words">{sub}</span>
      </span>
    </button>
  );
}

// Court tools under the artwork: case details, court-ready PDF, BIFF check, save case & open the professional site.
export function CourtTools({ cc, courtKey, compare, onCase, onBiff }) {
  const ready = compare.data?.state === "ready";
  return (
    <section data-testid="court-tools">
      <h2 className="text-xl sm:text-2xl font-extrabold text-[#3b1566] mb-1">Your Court Tools</h2>
      <p className="text-sm text-[#5f6368] mb-4">Everything you need for your court-ordered path, in one place.</p>
      <div className="grid sm:grid-cols-2 gap-3">
        <Tool
          testid="court-tool-case"
          icon={cc.verified ? "fa-circle-check" : "fa-key"}
          tone={cc.verified ? "bg-emerald-50 text-emerald-700" : "bg-[#f2ebfc] text-[#5c2c8e]"}
          title={cc.verified ? `Case ${courtKey}` : "Enter Case Code"}
          sub={cc.verified ? "Verified · update your details" : "Accept your court-ordered invite"}
          onClick={onCase}
        />
        <Tool testid="court-tool-pdf" icon="fa-file-pdf" title="Court-Ready PDF" sub="Download your summary report" onClick={cc.pdf} busy={cc.busy === "pdf"} />
        <Tool
          testid="court-tool-compare-pdf"
          icon="fa-people-arrows"
          title="Comparison PDF"
          sub={ready ? "Side-by-side results for mediation" : "Available once both parents share"}
          onClick={compare.downloadPdf}
          busy={compare.pdfBusy}
          className={ready ? "" : "opacity-70"}
        />
        <Tool testid="court-tool-biff" icon="fa-wand-magic-sparkles" title="BIFF Communication Check" sub="Review your saved messages" onClick={onBiff} />
        <Tool testid="court-tool-sync" icon="fa-rotate" title="Save Case & Open" sub={cc.alignHost} onClick={cc.sync} busy={cc.busy === "sync"} className="sm:col-span-2" />
      </div>
    </section>
  );
}

export function CourtModulesCard({ modules, onOpenModule }) {
  return (
    <div data-testid="court-modules" className="bg-white rounded-2xl p-6 border border-[#e0d5ed] shadow-md">
      <h4 className="text-sm font-extrabold text-[#3b1566] uppercase tracking-wider flex items-center gap-2">
        <i className="fa-solid fa-layer-group text-[#5c2c8e]"></i> Court Modules
      </h4>
      <p className="text-[11px] text-slate-500 mt-0.5 mb-3">The modules your professional reviews.</p>
      <div className="space-y-2">
        {modules.map((m) => (
          <button
            key={m.key}
            type="button"
            data-testid={`court-module-${m.key}`}
            data-status={m.status}
            onClick={() => onOpenModule(m)}
            className="w-full flex items-center gap-3 text-left rounded-xl border border-[#f2ebfc] hover:border-[#5c2c8e] hover:bg-[#faf8fd] px-3.5 py-3 transition-colors"
          >
            <span className="shrink-0 w-8 h-8 rounded-full bg-[#3b1566] text-white font-extrabold text-sm flex items-center justify-center">{m.letter}</span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-bold text-[#3b1566]">{m.title}</span>
              <span className="block text-[11px] text-[#5f6368]">{m.body}</span>
            </span>
            <span className={`shrink-0 text-[10px] font-bold px-2 py-0.5 rounded-full border ${m.chip}`}>{m.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
