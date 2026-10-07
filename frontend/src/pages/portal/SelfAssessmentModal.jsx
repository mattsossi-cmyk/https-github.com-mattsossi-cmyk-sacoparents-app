import React, { useEffect, useRef, useState } from "react";
import confetti from "canvas-confetti";
import { toast } from "sonner";

import { Dialog, DialogContent, DialogDescription, DialogTitle } from "../../components/ui/dialog";
import { CONTENT, QUESTION_COUNT, REFLECTIONS, STEPS, currentStepIndex } from "./selfAssessment/content";
import { GuideAvatar } from "./selfAssessment/ChatBubbles";
import { ScaleReply, StartReply, TextReply } from "./selfAssessment/ChatComposer";
import { ChatTranscript } from "./selfAssessment/ChatTranscript";
import { OverviewPanel } from "./selfAssessment/OverviewPanel";
import { useSelfAssessmentDraft } from "./selfAssessment/useSelfAssessmentDraft";

const STATUS_COPY = {
  idle: "Your answers save to your account automatically",
  pending: "Saving…",
  saving: "Saving…",
  saved: "Saved to your account",
  local: "Saved on this device",
  error: "Saved on this device — we'll retry your account on your next answer",
};

function progressLabel(step) {
  if (!step || step.type === "intro") return "Getting started";
  if (step.type === "rate") return `Question ${STEPS.indexOf(step)} of ${QUESTION_COUNT}`;
  if (step.type === "reflect") return `Reflection ${step.index + 1} of ${REFLECTIONS.length}`;
  return "Your next goal";
}

function Header({ step, pct, showProgress, onQuickExit }) {
  return (
    <div className="shrink-0 border-b border-purple-100 bg-white px-4 pt-3 pb-2.5 pr-12">
      <div className="flex items-center gap-2.5">
        <GuideAvatar />
        <div className="min-w-0 flex-1">
          <DialogTitle className="text-sm font-extrabold text-[#4c2889] leading-tight">{CONTENT.title}</DialogTitle>
          <DialogDescription className="text-[11px] text-slate-500">{CONTENT.guide_name}</DialogDescription>
        </div>
        <button
          type="button"
          data-testid="sa-quick-exit"
          onClick={onQuickExit}
          className="shrink-0 px-2.5 py-1 rounded-md text-[10px] font-bold bg-rose-600 hover:bg-rose-700 text-white shadow-sm transition-colors"
        >
          <i className="fa-solid fa-bolt mr-1"></i>Quick Exit
        </button>
      </div>
      {showProgress && (
        <div className="mt-2.5" data-testid="sa-chat-progress">
          <div className="flex justify-between text-[10px] font-semibold text-slate-500">
            <span data-testid="sa-chat-progress-label">{progressLabel(step)}</span>
            <span>{pct}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-purple-50 mt-1 overflow-hidden">
            <div className="h-full bg-purple-600 rounded-full transition-[width] duration-500" style={{ width: `${pct}%` }} />
          </div>
        </div>
      )}
    </div>
  );
}

function Composer({ step, draft, update, onFinish, busy, onBack }) {
  if (!step) return null;
  if (step.type === "intro") return <StartReply onStart={() => update((d) => ({ ...d, started: true }))} />;
  if (step.type === "rate") {
    return <ScaleReply onPick={(v) => update((d) => ({ ...d, answers: { ...d.answers, [step.id]: v } }))} onBack={onBack} />;
  }
  if (step.type === "reflect") {
    const save = (text) => update((d) => ({ ...d, reflections: { ...d.reflections, [step.id]: text } }));
    return (
      <TextReply
        testidPrefix="sa-chat-reflect"
        placeholder="Type your reflection…"
        sendLabel="Send"
        skipLabel="Skip"
        onSend={save}
        onSkip={() => save("")}
        onBack={onBack}
      />
    );
  }
  return (
    <TextReply
      testidPrefix="sa-chat-goal"
      initial={draft.reflections.goal_before_next || ""}
      placeholder="e.g. Pause and wait an hour before replying to a difficult message"
      sendLabel="Set my goal"
      skipLabel="Skip for now"
      busy={busy}
      onSend={(text) => onFinish(text)}
      onSkip={() => onFinish("")}
      onBack={onBack}
    />
  );
}

function useChatEffects(currentIdx, mode) {
  const [typing, setTyping] = useState(false);
  const endRef = useRef(null);
  const bodyRef = useRef(null);
  useEffect(() => {
    if (mode !== "chat") return undefined;
    setTyping(true);
    const t = setTimeout(() => setTyping(false), 550);
    return () => clearTimeout(t);
  }, [currentIdx, mode]);
  useEffect(() => {
    if (mode === "chat") endRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
    else if (bodyRef.current) bodyRef.current.scrollTop = 0;
  }, [currentIdx, typing, mode]);
  return { typing, endRef, bodyRef };
}

export function SelfAssessmentModal({ open, onOpenChange, parentName, userId, history = [], onCompleted, onQuickExit }) {
  const { draft, update, status, flush, complete } = useSelfAssessmentDraft({ open, userId, parentName, onCompleted });
  const [view, setView] = useState("auto");
  const [busy, setBusy] = useState(false);
  const [resumeAt, setResumeAt] = useState(null);
  const currentIdx = currentStepIndex(draft);
  const mode = view !== "auto" ? view : draft.started || history.length === 0 ? "chat" : "overview";
  const { typing, endRef, bodyRef } = useChatEffects(currentIdx, mode);

  useEffect(() => {
    if (open) setView("auto");
  }, [open]);
  useEffect(() => {
    if (open && draft.started && resumeAt === null) setResumeAt(currentIdx);
    if (!open) setResumeAt(null);
  }, [open, draft.started, currentIdx, resumeAt]);

  const handleOpenChange = (next) => {
    if (!next) flush();
    onOpenChange(next);
  };

  const onBack = () => {
    const prev = STEPS[currentIdx - 1];
    if (!prev || prev.type === "intro") return;
    update((d) => {
      const answers = { ...d.answers };
      const reflections = { ...d.reflections };
      if (prev.type === "rate") delete answers[prev.id];
      if (prev.type === "reflect") delete reflections[prev.id];
      return { ...d, answers, reflections };
    });
  };

  const onFinish = async (goal) => {
    setBusy(true);
    try {
      await complete({ ...draft, goal });
      setView("results");
      confetti({ particleCount: 70, spread: 70, origin: { y: 0.7 }, colors: ["#4c2889", "#8b5cf6", "#40a040", "#0284c7"] });
    } catch {
      toast.error("We couldn't save your assessment. Please check your connection and try again.");
    } finally {
      setBusy(false);
    }
  };

  const step = STEPS[currentIdx];
  const pct = Math.round((Math.max(0, currentIdx - 1) / (STEPS.length - 1)) * 100);
  const canGoBack = currentIdx > 1;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        data-testid="self-assessment-modal"
        data-mode={mode}
        className="max-w-xl w-[calc(100%-1rem)] h-[92vh] p-0 gap-0 flex flex-col overflow-hidden rounded-2xl"
      >
        <Header step={step} pct={pct} showProgress={mode === "chat"} onQuickExit={onQuickExit} />
        <div ref={bodyRef} data-testid="sa-body" className="flex-1 overflow-y-auto px-3 sm:px-4 py-4 space-y-3 bg-gradient-to-b from-purple-50/70 to-white">
          {mode === "chat" ? (
            <ChatTranscript draft={draft} currentIdx={currentIdx} typing={typing} resumeAt={resumeAt} />
          ) : (
            <OverviewPanel
              history={history}
              celebrate={mode === "results"}
              onStartNew={() => setView("chat")}
              onClose={() => handleOpenChange(false)}
            />
          )}
          <div ref={endRef} />
        </div>
        {mode === "chat" && step && (
          <div className="shrink-0 border-t border-purple-100 bg-white px-3 sm:px-4 pt-3 pb-2 space-y-1.5">
            <div className={typing ? "opacity-50 pointer-events-none" : ""}>
              <Composer step={step} draft={draft} update={update} onFinish={onFinish} busy={busy} onBack={canGoBack ? onBack : null} />
            </div>
            <p data-testid="self-assessment-save-status" data-status={status} className="text-[10px] text-slate-400 text-center">
              {STATUS_COPY[status] || STATUS_COPY.idle}
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default SelfAssessmentModal;
