import React from "react";

const btn =
  "rounded-2xl bg-white border border-[#e0d5ed] hover:border-[#5c2c8e] hover:bg-[#f2ebfc] px-4 py-3.5 text-left flex items-center gap-3 transition-colors disabled:opacity-60 disabled:hover:bg-white disabled:hover:border-[#e0d5ed]";

export function Tool({ testid, icon, title, sub, onClick, busy, disabled = false, tone = "bg-[#f2ebfc] text-[#5c2c8e]", className = "" }) {
  return (
    <button type="button" data-testid={testid} onClick={onClick} disabled={busy || disabled} className={`${btn} ${className}`}>
      <span className={`shrink-0 w-10 h-10 rounded-xl flex items-center justify-center ${tone}`}>
        <i className={`fa-solid ${busy ? "fa-spinner fa-spin" : icon}`}></i>
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-bold text-[#3b1566] break-words">{title}</span>
        <span data-testid={`${testid}-sub`} className="block text-[0.6875rem] text-[#5f6368] break-words">{sub}</span>
      </span>
    </button>
  );
}

// Case details, BIFF check, and save case & open the professional site (PDFs live in Reports).
export function CourtTools({ cc, courtKey, onCase, onBiff }) {
  return (
    <section data-testid="court-tools">
      <h4 className="text-sm font-extrabold text-[#3b1566] uppercase tracking-wider mb-3">Case &amp; message tools</h4>
      <div className="grid sm:grid-cols-2 gap-3">
        <Tool
          testid="court-tool-case"
          icon={cc.verified ? "fa-circle-check" : "fa-key"}
          tone={cc.verified ? "bg-emerald-50 text-emerald-700" : "bg-[#f2ebfc] text-[#5c2c8e]"}
          title={cc.verified ? `Case ${courtKey}` : "Enter Case Code"}
          sub={cc.verified ? "Verified · update your details" : "Accept your court-ordered invite"}
          onClick={onCase}
        />
        <Tool testid="court-tool-biff" icon="fa-wand-magic-sparkles" title="Communication Builder" sub="Review your saved messages" onClick={onBiff} />
        <Tool testid="court-tool-sync" icon="fa-rotate" title="Save Case & Open" sub={cc.alignHost} onClick={cc.sync} busy={cc.busy === "sync"} className="sm:col-span-2" />
      </div>
    </section>
  );
}
