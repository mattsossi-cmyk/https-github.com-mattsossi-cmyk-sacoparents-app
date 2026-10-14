import React, { useState } from "react";
import { toast } from "sonner";

import { api } from "../../../lib/api";
import { CourtSendSummary } from "./CourtSendSummary";

// Shown once everything the parent was asked for is done: a one-page, answers-free summary they can download.
export function CourtCompleteCard({ count }) {
  const [busy, setBusy] = useState(false);
  const download = async () => {
    setBusy(true);
    try {
      const res = await api.get("/court-path/completion-summary.pdf", { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = "SA_CoParents_Completion_Summary.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      toast.success("Your summary is downloading.");
    } catch (err) {
      const msg = err?.response?.status === 409
        ? "Your summary unlocks once everything your professional asked for is finished and saved to your account."
        : "Couldn't build your summary right now. Please try again.";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  };
  return (
    <section data-testid="court-complete-card" className="rounded-2xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-white p-4 sm:p-5 shadow-sm animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="flex items-start gap-3">
        <span aria-hidden className="shrink-0 h-10 w-10 rounded-full bg-emerald-600 text-white grid place-items-center">
          <i className="fa-solid fa-check text-base" />
        </span>
        <div className="min-w-0">
          <h3 data-testid="court-complete-title" className="text-lg sm:text-xl font-extrabold text-[#1F5C3B] leading-tight">
            You&rsquo;ve finished what your professional asked for
          </h3>
          <p className="text-sm text-slate-600 mt-1 leading-relaxed">
            All {count} requested {count === 1 ? "assessment is" : "assessments are"} done. Download a one-page summary showing each one is finished, with dates. It doesn&rsquo;t include any of your answers.
          </p>
          <button type="button" onClick={download} disabled={busy} data-testid="court-complete-download"
            className="mt-3 inline-flex items-center gap-2 rounded-full bg-emerald-700 hover:bg-emerald-800 text-white px-4 py-2 text-sm font-bold transition-colors disabled:opacity-60">
            <i className={`fa-solid ${busy ? "fa-spinner fa-spin" : "fa-file-arrow-down"}`} aria-hidden /> Download your summary
          </button>
          <CourtSendSummary />
        </div>
      </div>
    </section>
  );
}
