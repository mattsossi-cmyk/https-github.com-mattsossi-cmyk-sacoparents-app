import React from "react";

// Shown once everything the parent was asked for is done. The summary PDF itself lives in Reports.
export function CourtCompleteCard({ count }) {
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
            All {count} requested {count === 1 ? "assessment is" : "assessments are"} done. Your one-page completion summary is ready in{" "}
            <button type="button" onClick={() => document.getElementById("court-reports")?.scrollIntoView({ behavior: "smooth", block: "start" })} data-testid="court-complete-reports-link" className="font-bold text-emerald-800 underline underline-offset-2">Reports</button>. It doesn&rsquo;t include any of your answers.
          </p>
        </div>
      </div>
    </section>
  );
}
