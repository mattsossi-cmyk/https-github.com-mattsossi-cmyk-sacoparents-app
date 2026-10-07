import React, { useState } from "react";
import { toast } from "sonner";

import { api } from "../../../lib/api";
import { CONTENT } from "./content";
import { CoachBubble } from "./ChatBubbles";
import { CentralMessage, CycleStrip, ProgressHistory, ScoreCards } from "./ProgressPanel";

const pick = (e) => ({
  completed_at: e.completed_at,
  parent_name: e.parent_name || "",
  answers: e.answers,
  reflections: e.reflections || {},
  goal: e.goal || "",
});

function useDownloadPdf() {
  const [busy, setBusy] = useState(false);
  const download = async (entry, history) => {
    setBusy(true);
    try {
      const res = await api.post(
        "/self-assessment/pdf",
        { entry: pick(entry), history: history.map(pick) },
        { responseType: "blob" }
      );
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = "SA_CoParents_Self_Assessment.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      toast.success("Your Self-Assessment PDF is ready.");
    } catch {
      toast.error("Couldn't build the PDF right now. Please try again.");
    } finally {
      setBusy(false);
    }
  };
  return { busy, download };
}

export function OverviewPanel({ history, celebrate, onStartNew, onClose }) {
  const { busy, download } = useDownloadPdf();
  const latest = history[history.length - 1];
  if (!latest) return null;
  return (
    <div data-testid="sa-overview" className="space-y-4">
      {celebrate && <CoachBubble testid="sa-completion-message">{CONTENT.completion_message}</CoachBubble>}
      <ScoreCards scores={latest.scores} />
      <ProgressHistory history={history} />
      <CentralMessage />
      {latest.goal && (
        <div data-testid="sa-current-goal" className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3">
          <div className="text-[10px] uppercase font-bold tracking-wider text-emerald-800">{CONTENT.goal.label}</div>
          <p className="text-sm font-semibold text-slate-900 mt-0.5 break-words">{latest.goal}</p>
        </div>
      )}
      <CycleStrip />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
        <button
          type="button"
          data-testid="sa-download-pdf"
          disabled={busy}
          onClick={() => download(latest, history)}
          className="py-2.5 rounded-full bg-[#4c2889] hover:bg-[#371a68] disabled:opacity-60 text-white text-xs font-bold transition-colors"
        >
          <i className={`fa-solid ${busy ? "fa-spinner fa-spin" : "fa-file-pdf"} mr-1.5`}></i>
          {busy ? "Building PDF…" : "Download PDF"}
        </button>
        <button
          type="button"
          data-testid="sa-start-new"
          onClick={onStartNew}
          className="py-2.5 rounded-full bg-white hover:bg-purple-50 border border-purple-300 text-purple-900 text-xs font-bold transition-colors"
        >
          <i className="fa-solid fa-rotate mr-1.5"></i>
          Start my next Self-Assessment
        </button>
      </div>
      <button
        type="button"
        data-testid="sa-close"
        onClick={onClose}
        className="w-full py-2 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
      >
        Close
      </button>
    </div>
  );
}
