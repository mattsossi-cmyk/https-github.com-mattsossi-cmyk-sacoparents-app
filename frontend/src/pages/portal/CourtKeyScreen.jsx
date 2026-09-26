import React from "react";

export function CourtKeyScreen({
  courtKeyInput,
  onChange,
  onVerify,
  courtKeyError,
  courtKeyLoading,
}) {
  return (
    <div className="space-y-4" data-testid="screen-court-key">
      <div className="bg-white p-5 rounded-2xl shadow-sm border border-purple-200 space-y-4">
        <div className="border-b border-slate-100 pb-3">
          <span className="bg-purple-100 text-purple-900 text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase">
            sacoparentsalign.com Integration
          </span>
          <h2 className="text-lg font-bold text-slate-800 mt-1">
            Enter Professional Access Key
          </h2>
          <p className="text-xs text-slate-500">
            Provided by your court-appointed mediator, parenting coordinator, or
            family lawyer.
          </p>
        </div>

        <div className="space-y-3">
          <label className="block text-xs font-bold text-slate-700">
            Professional Key Code
          </label>
          <input
            type="text"
            data-testid="court-key-input"
            value={courtKeyInput}
            onChange={(e) => onChange(e.target.value)}
            className="w-full p-3 border border-slate-300 rounded-xl text-sm font-mono tracking-wider focus:ring-2 focus:ring-purple-600 focus:outline-none"
            placeholder="e.g. ALIGN-SA-2026"
          />
          {courtKeyError && (
            <p
              data-testid="court-key-error"
              className="text-[11px] text-rose-600 font-semibold"
            >
              {courtKeyError}
            </p>
          )}
          <p className="text-[10px] text-slate-400">
            Demo Keys: Use{" "}
            <button
              type="button"
              data-testid="demo-key-1"
              onClick={() => onChange("ALIGN-SA-2026")}
              className="text-purple-700 font-bold underline"
            >
              ALIGN-SA-2026
            </button>{" "}
            or{" "}
            <button
              type="button"
              data-testid="demo-key-2"
              onClick={() => onChange("COURT-8842")}
              className="text-purple-700 font-bold underline"
            >
              COURT-8842
            </button>
          </p>
        </div>

        <button
          onClick={onVerify}
          data-testid="verify-court-key-btn"
          disabled={courtKeyLoading}
          className="w-full bg-purple-950 hover:bg-purple-900 disabled:opacity-60 disabled:cursor-not-allowed text-white font-bold py-3 rounded-xl text-xs flex items-center justify-center gap-2 transition shadow"
        >
          <i className="fa-solid fa-key"></i>{" "}
          {courtKeyLoading ? "Verifying…" : "Verify & Sync Joint Case"}
        </button>
      </div>
    </div>
  );
}
