import React, { useState } from "react";
import { toast } from "sonner";

import { AiGuardFrame, AiNoticeNeeded, useAiGuard } from "../../../components/aiNotice/AiGuard";
import { GuideChat } from "../guide/GuideChat";
import { AiLibraryDialog } from "./AiLibraryDialog";
import { useFraming } from "./useSaInsight";

export function TipBox({ tip, loading, testid = "sa-ai-tip" }) {
  return (
    <div data-testid={testid} className="bg-purple-50/80 border border-purple-100 rounded-xl p-4 text-xs leading-relaxed text-slate-700">
      <p className="font-semibold text-[#3B1C6B] mb-1">
        <i className="fa-solid fa-lightbulb text-purple-500 mr-1.5"></i>
        {tip.label}
      </p>
      {loading ? (
        <p data-testid={`${testid}-loading`} className="text-slate-500 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce"></span>
          <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce [animation-delay:120ms]"></span>
          <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce [animation-delay:240ms]"></span>
          <span className="ml-1">Your guide is thinking…</span>
        </p>
      ) : tip.needsNotice ? (
        <AiNoticeNeeded tp={testid} className="mb-0">AI tips appear here after you read and accept the AI privacy notice.</AiNoticeNeeded>
      ) : (
        <p data-testid={`${testid}-text`} className="text-slate-600">{tip.text}</p>
      )}
    </div>
  );
}

function FramingForm({ safetyFlag }) {
  const [text, setText] = useState("");
  const { result, busy, error, submit } = useFraming(safetyFlag);
  const guard = useAiGuard("self_assessment", text);
  const send = async () => {
    const t = text.trim();
    if (t.length < 3 || !(await guard.confirmSend(t))) return;
    submit(t);
  };
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(result.suggested);
      toast.success("Suggested wording copied.");
    } catch {
      toast.error("Couldn't copy. Please select the text and copy it.");
    }
  };
  return (
    <div className="space-y-3 mb-5">
      <label htmlFor="sa-ai-query" className="block text-xs font-bold text-[#3B1C6B]">
        Ask AI for communication framing
      </label>
      <AiGuardFrame tp="sa-ai-query" guard={guard}>
      <div className="flex gap-2">
        <input
          {...guard.inputProps}
          id="sa-ai-query"
          data-testid="sa-ai-query"
          type="text"
          value={text}
          maxLength={1000}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Describe a situation or paste a message…"
          className="flex-1 min-w-0 bg-white text-xs border border-purple-200 rounded-xl px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-purple-500 shadow-sm"
        />
        <button
          type="button"
          data-testid="sa-ai-submit"
          onClick={send}
          disabled={busy || text.trim().length < 3}
          className="bg-purple-600 hover:bg-purple-700 disabled:opacity-60 text-white text-xs font-semibold px-4 py-2.5 rounded-xl shadow transition-colors shrink-0"
        >
          {busy ? <i className="fa-solid fa-spinner fa-spin"></i> : "Submit Text"}
        </button>
      </div>
      </AiGuardFrame>
      {error && <p data-testid="sa-ai-error" className="text-[11px] text-rose-700">{error}</p>}
      {result && (
        <div data-testid="sa-ai-framing" className="rounded-xl border border-purple-100 bg-white p-3 space-y-2 text-xs">
          <p data-testid="sa-ai-framing-advice" className="text-slate-700">{result.advice}</p>
          {result.suggested && (
            <div className="rounded-lg bg-emerald-50 border border-emerald-100 p-2.5">
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="text-[10px] uppercase font-bold tracking-wider text-emerald-800">Suggested wording</span>
                <button type="button" data-testid="sa-ai-framing-copy" onClick={copy} className="text-[11px] font-semibold text-emerald-800 hover:underline">
                  <i className="fa-regular fa-copy mr-1"></i>Copy
                </button>
              </div>
              <p data-testid="sa-ai-framing-suggested" className="text-emerald-950">{result.suggested}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const ghostBtn =
  "w-full py-2.5 px-4 bg-white hover:bg-purple-50 text-purple-900 border border-purple-200 text-xs font-semibold rounded-xl transition-colors flex items-center justify-center gap-2";

// `chat` (optional): saved Guide chat shown in place of the one-off framing box.
export function AiInsightPanel({ tip, loading, safetyFlag, onOpenBiffCoach, onUseTemplate, biffBusy = false, chat = null }) {
  const [library, setLibrary] = useState(null);
  return (
    <div data-testid="sa-ai-panel" className={`glass-ai-panel rounded-2xl p-6 shadow-lg ${chat ? "" : "lg:sticky lg:top-6"}`}>
      <div className="flex items-center justify-between pb-4 border-b border-purple-100 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-purple-600 text-white flex items-center justify-center text-sm shadow">
            <i className="fa-solid fa-compass"></i>
          </div>
          <div>
            <h4 className="font-bold text-[#3B1C6B] text-base leading-tight">Emergent AI Insight</h4>
            <p className="text-[11px] text-slate-500 font-medium">Personalized AI Guide &bull; Actively Assessing</p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span> Live
        </span>
      </div>
      <div className="mb-5">
        <TipBox tip={tip} loading={loading} />
      </div>
      {chat ? (
        <div className="mb-5">
          <GuideChat
            chat={chat}
            tp="sa-guide"
            title="Self-Assessment Guide"
            greeting="Hi, I'm your Self-Assessment Guide. Ask me about any question, your results, or how to set a goal that fits you."
            suggestions={["What do my results mean?", "How do I pick a good goal?", "How can I grow in communication?"]}
          />
        </div>
      ) : (
        <FramingForm safetyFlag={safetyFlag} />
      )}
      <div className="space-y-2.5">
        <button
          type="button"
          data-testid="sa-ai-biff"
          onClick={onOpenBiffCoach}
          disabled={biffBusy}
          className="w-full py-3 px-4 disabled:opacity-60 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white text-xs font-bold rounded-xl shadow transition-colors flex items-center justify-center gap-2"
        >
          <i className="fa-solid fa-wand-magic-sparkles"></i>
          <span>Get suggested wording (AI)</span>
        </button>
        <button type="button" data-testid="sa-ai-examples" onClick={() => setLibrary("examples")} className={ghostBtn}>
          <i className="fa-regular fa-lightbulb text-purple-500"></i>
          <span>View AI Examples</span>
        </button>
        <button type="button" data-testid="sa-ai-templates" onClick={() => setLibrary("templates")} className={ghostBtn}>
          <i className="fa-regular fa-file-lines text-purple-500"></i>
          <span>Get Quick Templates</span>
        </button>
      </div>
      <div className="mt-5 pt-3 border-t border-purple-100 text-center">
        <span data-testid="sa-ai-footer-note" className="text-[10px] text-slate-500 font-medium">AI help comes from an outside AI service. Leave out names and sensitive details.</span>
      </div>
      <AiLibraryDialog
        tab={library}
        onClose={() => setLibrary(null)}
        grey={!!safetyFlag}
        onUse={onUseTemplate && ((text) => { setLibrary(null); onUseTemplate(text); })}
      />
    </div>
  );
}
