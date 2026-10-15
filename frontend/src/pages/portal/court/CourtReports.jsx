import React, { useState } from "react";
import { toast } from "sonner";

import { api } from "../../../lib/api";
import { CourtSendSummary } from "./CourtSendSummary";
import { Tool } from "./CourtTools";

async function downloadCompletionSummary() {
  const res = await api.get("/court-path/completion-summary.pdf", { responseType: "blob" });
  const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "SA_CoParents_Completion_Summary.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

function CompletionRow({ complete }) {
  const [busy, setBusy] = useState(false);
  const download = async () => {
    setBusy(true);
    try {
      await downloadCompletionSummary();
      toast.success("Your summary is downloading.");
    } catch (err) {
      toast.error(
        err?.response?.status === 409
          ? "Your summary unlocks once everything your professional asked for is finished and saved to your account."
          : "Couldn't build your summary right now. Please try again."
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="sm:col-span-2 space-y-2">
      <Tool
        testid="court-complete-download"
        icon="fa-award"
        tone={complete ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}
        title="Completion Summary"
        sub={complete ? "One page: each requested assessment is done, with dates. No answers." : "Unlocks when every requested assessment is done"}
        onClick={download}
        busy={busy}
        disabled={!complete}
        className="w-full"
      />
      {complete && <CourtSendSummary />}
    </div>
  );
}

// The one place for every Court-page PDF.
export function CourtReports({ cc, checklist, compare, complete, signedIn }) {
  const ready = compare.data?.state === "ready";
  return (
    <section id="court-reports" data-testid="court-reports" className="scroll-mt-6">
      <h3 className="text-xl sm:text-2xl font-extrabold text-[#3b1566] mb-1">Reports</h3>
      <p className="text-sm text-[#5f6368] mb-4">Every PDF for your court-ordered path. You download them yourself; nothing is filed or sent for you.</p>
      <div className="grid sm:grid-cols-2 gap-3">
        {signedIn && <CompletionRow complete={complete} />}
        <Tool testid="court-tool-pdf" icon="fa-file-pdf" title="Court-Ready Summary PDF" sub="Your summary report" onClick={cc.pdf} busy={cc.busy === "pdf"} />
        <Tool testid="court-checklist-download" icon="fa-list-check" title="Court Checklist PDF" sub="What's done and what's left" onClick={checklist.download} busy={checklist.downloading} disabled={!checklist.data} />
        <Tool
          testid="court-tool-compare-pdf"
          icon="fa-people-arrows"
          title="Comparison PDF"
          sub={ready ? "Side-by-side results for mediation" : "Available once both parents share"}
          onClick={compare.downloadPdf}
          busy={compare.pdfBusy}
          className={`sm:col-span-2 ${ready ? "" : "opacity-70"}`}
        />
      </div>
    </section>
  );
}
