import React, { useEffect, useRef } from "react";

import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../../../components/ui/dialog";
import { CpIntro, CpResults, CpSection } from "./CpAssessmentParts";
import { useCoparentingAssessment } from "./useCoparentingAssessment";

function Header({ schema, answers, mode, step, onQuickExit }) {
  const total = schema?.total_questions || 0;
  const answered = Object.keys(answers).length;
  const pct = total ? Math.round((answered / total) * 100) : 0;
  return (
    <div className="shrink-0 border-b border-purple-100 bg-white px-4 pt-3 pb-2.5 pr-12">
      <div className="flex items-center gap-2.5">
        <div className="shrink-0 w-8 h-8 rounded-full bg-[#4c2889] text-white flex items-center justify-center">
          <i className="fa-solid fa-users text-[13px]"></i>
        </div>
        <div className="min-w-0 flex-1">
          <DialogTitle className="text-sm font-extrabold text-[#4c2889] leading-tight">Understand Your Co-Parenting Relationship</DialogTitle>
          <DialogDescription className="text-[11px] text-slate-500">
            Co-Parenting Assessment{total ? ` · ${total} questions` : ""}
          </DialogDescription>
        </div>
        <button
          type="button"
          data-testid="cp-assess-quick-exit"
          onClick={onQuickExit}
          className="shrink-0 px-2.5 py-1 rounded-md text-[10px] font-bold bg-rose-600 hover:bg-rose-700 text-white shadow-sm transition-colors"
        >
          <i className="fa-solid fa-bolt mr-1"></i>Quick Exit
        </button>
      </div>
      {mode === "section" && schema && (
        <div className="mt-2.5" data-testid="cp-assess-progress">
          <div className="flex justify-between text-[10px] font-semibold text-slate-500">
            <span data-testid="cp-assess-progress-label">
              Section {step + 1} of {schema.sections.length}
            </span>
            <span>
              {answered}/{total} · {pct}%
            </span>
          </div>
          <div className="h-1.5 rounded-full bg-purple-50 mt-1 overflow-hidden">
            <div className="h-full bg-purple-600 rounded-full transition-[width] duration-500" style={{ width: `${pct}%` }} />
          </div>
        </div>
      )}
    </div>
  );
}

function Footer({ step, count, busy, onBack, onNext, onFinish }) {
  const last = step === count - 1;
  return (
    <div className="shrink-0 border-t border-purple-100 bg-white px-4 py-3 flex gap-2">
      <button
        type="button"
        data-testid="cp-assess-back"
        onClick={onBack}
        disabled={step === 0}
        className="px-4 py-2.5 rounded-full border border-slate-300 text-slate-700 text-xs font-bold disabled:opacity-40"
      >
        Back
      </button>
      <button
        type="button"
        data-testid={last ? "cp-assess-finish" : "cp-assess-next"}
        onClick={last ? onFinish : onNext}
        disabled={busy}
        className="flex-1 py-2.5 rounded-full bg-[#4c2889] hover:bg-[#371a68] text-white text-xs font-bold transition-colors disabled:opacity-60"
      >
        {busy ? <i className="fa-solid fa-spinner fa-spin"></i> : last ? "See my results" : "Next section →"}
      </button>
    </div>
  );
}

export function CoparentingAssessmentModal({ open, onOpenChange, userId, onQuickExit }) {
  const a = useCoparentingAssessment({ open, userId });
  const bodyRef = useRef(null);
  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = 0;
  }, [a.step, a.mode]);
  const section = a.schema?.sections[a.step];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        data-testid="cp-assess-modal"
        data-mode={a.mode}
        className="max-w-xl w-[calc(100%-1rem)] h-[92vh] p-0 gap-0 flex flex-col overflow-hidden rounded-2xl"
      >
        <Header schema={a.schema} answers={a.answers} mode={a.mode} step={a.step} onQuickExit={onQuickExit} />
        <div ref={bodyRef} className="flex-1 overflow-y-auto px-4 py-4 bg-gradient-to-b from-purple-50/70 to-white">
          {a.mode === "loading" && <p className="text-sm text-slate-500">Loading…</p>}
          {a.mode === "error" && (
            <p data-testid="cp-assess-error" className="text-sm text-rose-700">
              We couldn't load the assessment. Please check your connection and try again.
            </p>
          )}
          {a.mode === "intro" && a.schema && !userId && (
            <p data-testid="cp-assess-signin" className="text-sm text-slate-700">
              Please <a href="/login" className="font-bold text-purple-800 underline">sign in</a> to take the
              Co-Parenting Assessment so your answers and report are saved to your account.
            </p>
          )}
          {a.mode === "intro" && a.schema && userId && <CpIntro schema={a.schema} onStart={() => a.goTo(0)} />}
          {a.mode === "section" && section && (
            <CpSection section={section} scale={a.schema.response_scale} answers={a.answers} onAnswer={a.setAnswer} />
          )}
          {a.mode === "results" && a.scores && (
            <CpResults scores={a.scores} onDownload={a.download} onRetake={a.retake} onClose={() => onOpenChange(false)} />
          )}
        </div>
        {a.mode === "section" && (
          <Footer
            step={a.step}
            count={a.schema.sections.length}
            busy={a.busy}
            onBack={() => a.goTo(a.step - 1)}
            onNext={() => a.goTo(a.step + 1)}
            onFinish={a.finish}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

export default CoparentingAssessmentModal;
