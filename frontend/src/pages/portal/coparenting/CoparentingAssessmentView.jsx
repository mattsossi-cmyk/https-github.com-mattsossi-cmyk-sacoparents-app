import React, { useEffect } from "react";

import { useGuideChat } from "../guide/useGuideChat";
import { JourneyPage } from "../selfJourney/JourneyPage";
import { ASSESS_ART } from "../selfJourney/selfJourneyArt";
import { CpIntro, CpResults, CpSection } from "./CpAssessmentParts";
import { useCoparentingAssessment } from "./useCoparentingAssessment";

const GREETING = "Hi, I'm your Co-Parenting Guide. Ask me about any question or section while you work through your assessment.";
const SUGGESTIONS = ["What is this section asking?", "How do I answer honestly?", "How can exchanges feel calmer?"];

function Nav({ step, count, answered, total, busy, onBack, onNext, onFinish }) {
  const last = step === count - 1;
  return (
    <div className="mt-6 pt-4 border-t border-purple-100 flex items-center gap-3">
      <button
        type="button"
        data-testid="cp-assess-back"
        onClick={onBack}
        disabled={step === 0}
        className="px-5 py-3 rounded-full border border-slate-300 text-slate-700 text-sm font-bold disabled:opacity-40 hover:bg-slate-50 transition-colors"
      >
        Back
      </button>
      <span data-testid="cp-assess-progress-label" className="hidden sm:block text-xs text-slate-500 mx-auto">
        Section {step + 1} of {count} · {answered}/{total} answered
      </span>
      <button
        type="button"
        data-testid={last ? "cp-assess-finish" : "cp-assess-next"}
        onClick={last ? onFinish : onNext}
        disabled={busy}
        className="flex-1 sm:flex-none sm:min-w-[200px] py-3 px-6 rounded-full bg-[#4c2889] hover:bg-[#371a68] text-white text-sm font-bold transition-colors disabled:opacity-60"
      >
        {busy ? <i className="fa-solid fa-spinner fa-spin"></i> : last ? "See my results" : "Next section →"}
      </button>
    </div>
  );
}

function heroFor(a, total, answered) {
  const pill =
    a.mode === "results" ? "Completed" : a.mode === "section" && a.schema ? `Section ${a.step + 1} of ${a.schema.sections.length}` : "Ready to begin";
  const pct = a.mode === "results" ? 100 : total ? Math.round((answered / total) * 100) : 0;
  return {
    title: "Understand Your Co-Parenting Relationship",
    subtitle: `Co-Parenting Assessment${total ? ` · ${total} questions` : ""}. Your answers are private and save as you go.`,
    pill,
    pct,
  };
}

// Full-screen Co-Parenting Relationship Assessment (Self Journey + Court card 2), questions on the left.
export function CoparentingAssessmentView({ userId, onClose, onQuickExit, onOpenSelfAssessment, safetyFlag }) {
  const a = useCoparentingAssessment({ open: true, userId });
  const section = a.schema?.sections[a.step];
  const chat = useGuideChat("/journey-guide/coparenting/chat", { section: a.mode === "section" ? section?.name : null, safety_flagged: !!safetyFlag });
  const total = a.schema?.total_questions || 0;
  const answered = Object.keys(a.answers).length;
  useEffect(() => {
    document.getElementById("cp-page")?.scrollTo({ top: 0, behavior: "smooth" });
  }, [a.step, a.mode]);
  const onArt = (k) =>
    k === "self" ? onOpenSelfAssessment() : document.getElementById("cp-work")?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <JourneyPage
      tp="cp"
      hero={heroFor(a, total, answered)}
      art={ASSESS_ART}
      onArt={onArt}
      artState={{ activeKey: "coparent" }}
      chat={chat}
      chatProps={{ title: "Co-Parenting Guide", greeting: GREETING, suggestions: SUGGESTIONS }}
      onBack={onClose}
      onQuickExit={onQuickExit}
      footer="Co-Parenting Assessment"
    >
      <section id="cp-work" data-testid="cp-assess-panel" data-mode={a.mode} className="bg-white rounded-3xl border border-purple-100 shadow-lg p-5 sm:p-7 scroll-mt-6">
        {a.mode === "loading" && <p className="text-sm text-slate-500">Loading…</p>}
        {a.mode === "error" && (
          <p data-testid="cp-assess-error" className="text-sm text-rose-700">
            We couldn't load the assessment. Please check your connection and try again.
          </p>
        )}
        {a.mode === "intro" && a.schema && !userId && (
          <p data-testid="cp-assess-signin" className="text-sm text-slate-700">
            Please <a href="/login" className="font-bold text-purple-800 underline">sign in</a> to take the Co-Parenting Assessment so your
            answers and report are saved to your account.
          </p>
        )}
        {a.mode === "intro" && a.schema && userId && <CpIntro schema={a.schema} onStart={() => a.goTo(0)} />}
        {a.mode === "section" && section && (
          <>
            <CpSection section={section} scale={a.schema.response_scale} answers={a.answers} onAnswer={a.setAnswer} />
            <Nav
              step={a.step}
              count={a.schema.sections.length}
              answered={answered}
              total={total}
              busy={a.busy}
              onBack={() => a.goTo(a.step - 1)}
              onNext={() => a.goTo(a.step + 1)}
              onFinish={a.finish}
            />
          </>
        )}
        {a.mode === "results" && a.scores && <CpResults scores={a.scores} onDownload={a.download} onRetake={a.retake} onClose={onClose} />}
      </section>
    </JourneyPage>
  );
}
