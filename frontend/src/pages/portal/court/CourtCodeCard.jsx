import React from "react";

const HINT = "Use the code from your court order, mediator, or attorney.";

export function CourtCodeCard({ code, onChange, onVerify, onAccept, status, busy, verified }) {
  const tone = status?.tone === "error" ? "text-rose-600 font-semibold" : status || verified ? "text-emerald-700 font-bold" : "text-slate-500 font-medium";
  const text = status?.text || (verified ? "Verified and linked to your portal." : HINT);
  return (
    <>
      <div data-testid="court-code-card" className="bg-white rounded-2xl p-6 border border-purple-100 shadow-md space-y-4 mt-6">
        <label htmlFor="court-code-input" className="text-sm font-extrabold text-[#3B1C6B] uppercase tracking-wider flex items-center gap-2">
          <i className="fa-solid fa-key text-purple-600"></i> Enter Court Case or Invite Code
        </label>
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            id="court-code-input"
            data-testid="court-code-input"
            type="text"
            value={code}
            maxLength={80}
            autoComplete="off"
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onVerify()}
            placeholder="e.g. SA-2026-8842"
            className="flex-1 min-w-0 bg-slate-50 border border-slate-300 rounded-xl px-4 py-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-purple-600"
          />
          <button
            type="button"
            data-testid="court-code-verify"
            onClick={onVerify}
            disabled={!!busy}
            className="bg-purple-900 hover:bg-purple-950 disabled:opacity-60 text-white font-bold text-xs px-5 py-3 rounded-xl shadow transition-colors shrink-0"
          >
            {busy === "verify" ? (
              <i className="fa-solid fa-spinner fa-spin"></i>
            ) : verified ? (
              <>
                <i className="fa-solid fa-circle-check mr-1.5"></i>Verified
              </>
            ) : (
              "Verify Code"
            )}
          </button>
        </div>
        <p data-testid="court-code-status" role="status" className={`text-xs ${tone}`}>
          {text}
        </p>
      </div>
      <div className="pt-4">
        <button
          type="button"
          data-testid="court-accept"
          onClick={onAccept}
          disabled={!!busy}
          className="w-full py-5 px-5 sm:px-8 bg-[#38A169] hover:bg-[#2F855A] disabled:opacity-70 text-white font-black rounded-2xl shadow-xl hover:shadow-2xl transition-[transform,box-shadow,background-color] hover:-translate-y-0.5 flex items-center justify-center gap-3 text-base sm:text-xl tracking-wide"
        >
          <span className="w-8 h-8 rounded-full bg-white text-emerald-700 flex items-center justify-center text-base shrink-0">
            <i className={`fa-solid ${busy === "accept" ? "fa-spinner fa-spin" : "fa-arrow-right"}`}></i>
          </span>
          <span>{verified ? "Continue Your Court Ordered Path" : "Accept Your Court Ordered Invite"}</span>
        </button>
      </div>
    </>
  );
}
