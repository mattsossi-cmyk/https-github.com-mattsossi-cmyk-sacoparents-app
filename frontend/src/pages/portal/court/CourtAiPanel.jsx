import React, { useState } from "react";

import { api } from "../../../lib/api";

const FAIL = "The AI guide couldn't respond right now. Please try again.";
const ghostBtn =
  "w-full py-2.5 px-4 bg-white hover:bg-purple-50 disabled:opacity-60 text-purple-900 border border-purple-200 text-xs font-semibold rounded-xl transition-colors flex items-center justify-center gap-2";

function useCourtGuide(safetyFlag) {
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const ask = async (question) => {
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post("/court-path/ai/guide", { question, safety_flagged: !!safetyFlag });
      setAnswer(data.answer);
    } catch (e) {
      const detail = e?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : FAIL);
    } finally {
      setBusy(false);
    }
  };
  return { answer, busy, error, ask };
}

function GuideAnswer({ guide }) {
  if (guide.busy)
    return (
      <p data-testid="court-ai-loading" className="text-xs text-slate-500 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce"></span>
        <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce [animation-delay:120ms]"></span>
        <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce [animation-delay:240ms]"></span>
        <span className="ml-1">Your guide is thinking…</span>
      </p>
    );
  if (guide.error) return <p data-testid="court-ai-error" className="text-[11px] text-rose-700">{guide.error}</p>;
  if (!guide.answer) return null;
  return (
    <div data-testid="court-ai-answer" className="rounded-xl border border-purple-100 bg-white p-3 space-y-2 text-xs">
      <p data-testid="court-ai-answer-text" className="text-slate-700 leading-relaxed">{guide.answer}</p>
      <p className="text-[10px] text-slate-400">General information only, not legal advice. For your specific case, ask your attorney or mediator.</p>
    </div>
  );
}

export function CourtAiPanel({ safetyFlag, verified, doneCount, total, busy, onPdf, onBiff, onSync, alignHost }) {
  const [text, setText] = useState("");
  const guide = useCourtGuide(safetyFlag);
  const send = () => text.trim().length >= 3 && !guide.busy && guide.ask(text.trim());
  return (
    <div data-testid="court-ai-panel" className="glass-ai-panel rounded-2xl p-6 shadow-lg lg:sticky lg:top-6">
      <div className="flex items-center justify-between pb-4 border-b border-purple-100 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-purple-600 text-white flex items-center justify-center text-sm shadow">
            <i className="fa-solid fa-scale-balanced"></i>
          </div>
          <div>
            <h4 className="font-bold text-[#3B1C6B] text-base leading-tight">Emergent AI Court Guide</h4>
            <p className="text-[11px] text-slate-500 font-medium">Court Pathway Companion</p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span> Active
        </span>
      </div>
      <div data-testid="court-ai-readiness" className="bg-purple-50/80 border border-purple-100 rounded-xl p-4 mb-5 text-xs leading-relaxed text-slate-700">
        <p className="font-semibold text-[#3B1C6B] mb-1">Court pathway readiness:</p>
        <p data-testid="court-ai-readiness-text" className="text-slate-600">
          {verified ? "Case code verified" : "Case code not entered yet"} &bull; {doneCount} of {total} modules complete.
        </p>
        <p className="text-slate-500 mt-1">Ask me about your court-ordered steps. I share general guidance, not legal advice.</p>
      </div>
      <div className="space-y-3 mb-5">
        <label htmlFor="court-ai-query" className="block text-xs font-bold text-[#3B1C6B]">Ask AI for Court Order Guidance</label>
        <div className="flex gap-2">
          <input
            id="court-ai-query"
            data-testid="court-ai-query"
            type="text"
            value={text}
            maxLength={1000}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder="Ask about your court-ordered steps or BIFF framing…"
            className="flex-1 min-w-0 bg-white text-xs border border-purple-200 rounded-xl px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-purple-500 shadow-sm"
          />
          <button
            type="button"
            data-testid="court-ai-ask"
            onClick={send}
            disabled={guide.busy || text.trim().length < 3}
            className="bg-purple-600 hover:bg-purple-700 disabled:opacity-60 text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow transition-colors shrink-0"
          >
            {guide.busy ? <i className="fa-solid fa-spinner fa-spin"></i> : "Ask"}
          </button>
        </div>
        <GuideAnswer guide={guide} />
      </div>
      <div className="space-y-2.5">
        <button
          type="button"
          data-testid="court-ai-pdf"
          onClick={onPdf}
          disabled={!!busy}
          className="w-full py-3 px-4 disabled:opacity-60 bg-gradient-to-r from-purple-700 to-indigo-800 hover:from-purple-800 hover:to-indigo-900 text-white text-xs font-bold rounded-xl shadow transition-colors flex items-center justify-center gap-2"
        >
          <i className={`fa-solid ${busy === "pdf" ? "fa-spinner fa-spin" : "fa-file-pdf"}`}></i>
          <span>Generate Court-Ready PDF Report</span>
        </button>
        <button type="button" data-testid="court-ai-biff" onClick={onBiff} className={ghostBtn}>
          <i className="fa-solid fa-wand-magic-sparkles text-purple-600"></i>
          <span>Run BIFF Communication Check</span>
        </button>
        <button type="button" data-testid="court-ai-sync" onClick={onSync} disabled={!!busy} className={ghostBtn}>
          <i className={`fa-solid ${busy === "sync" ? "fa-spinner fa-spin" : "fa-rotate"} text-purple-600`}></i>
          <span>Save Case &amp; Open {alignHost}</span>
        </button>
      </div>
      <div className="mt-5 pt-3 border-t border-purple-100 text-center">
        <span className="text-[10px] text-slate-400 font-medium">Private &amp; secure &bull; General guidance, not legal advice</span>
      </div>
    </div>
  );
}
