import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import confetti from "canvas-confetti";
import { toast } from "sonner";

import { PAGE_STEP_COUNT, STEPS, currentStepIndex, pageStepOf } from "./selfAssessment/content";
import { AiInsightPanel, TipBox } from "./selfAssessment/AiInsightPanel";
import { JourneySteps } from "./selfAssessment/JourneySteps";
import { OverviewPanel } from "./selfAssessment/OverviewPanel";
import { ProgressOverTime } from "./selfAssessment/ProgressOverTime";
import { SaTabs } from "./selfAssessment/SaTabs";
import { SharingNotice } from "../../components/privacy/SharingNotice";
import { QuestionPanel } from "./selfAssessment/QuestionPanel";
import { useGuideChat } from "./guide/useGuideChat";
import { ArtPicture } from "./selfJourney/ArtPicture";
import { SA_ART } from "./selfJourney/selfJourneyArt";
import { BottomBanner, Hero, PageHeader, SafetyBanner } from "./selfAssessment/SaChrome";
import { useSaInsight } from "./selfAssessment/useSaInsight";
import { useSelfAssessmentDraft } from "./selfAssessment/useSelfAssessmentDraft";

const STAGE = { intro: 0, rate: 0, reflect: 1, goal: 2 };
const JUMP = { strengths: "sa-strengths", growth: "sa-growth-areas", goals: "sa-current-goal", progress: "sa-progress-over-time" };
const chatSection = (mode, step) =>
  mode !== "assess" || !step ? "their Self-Assessment results" : step.type === "rate" ? step.section.title : step.type === "reflect" ? "the reflection questions" : step.type === "goal" ? "setting a personal goal" : null;
const ORDER = ["reflect", "identify", "goals", "track"];

const statusesFor = (mode, step) => {
  const at = mode === "loading" ? -1 : mode === "assess" ? STAGE[step?.type ?? "intro"] : 3;
  return Object.fromEntries(ORDER.map((k, i) => [k, i < at ? "done" : i === at ? "current" : "upcoming"]));
};

function useLockScroll() {
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);
}

// Full-page Self-Assessment (Card 1). Rendered in a portal over Self Journey.
export function SelfAssessmentView({ onClose, onQuickExit, onOpenBiffCoach, parentName, userId, history = [], startNew = false, compareWithLast = false, onCompleted, onEntryUpdate, onGoalReached, safetyFlag, hidden = false }) {
  const { draft, update, status, flush, complete, ready } = useSelfAssessmentDraft({ open: true, userId, parentName, onCompleted });
  const [view, setView] = useState(startNew ? "assess" : "auto");
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState("results");
  useLockScroll();
  const currentIdx = currentStepIndex(draft);
  const mode = !ready ? "loading" : view !== "auto" ? view : draft.started || history.length === 0 ? "assess" : "overview";
  const step = STEPS[currentIdx];
  const latest = history[history.length - 1] || null;
  const { tip, loading } = useSaInsight({
    draft,
    mode,
    latest,
    safetyFlag,
    onSectionTip: (key, text) => update((d) => ({ ...d, tips: { ...(d.tips || {}), [key]: text } })),
    onOverallTip: (entry, text) => onEntryUpdate?.(entry.id, { tips: { ...(entry.tips || {}), overall: text } }),
  });

  const chat = useGuideChat("/journey-guide/self-assessment/chat", { section: chatSection(mode, step), safety_flagged: !!safetyFlag });
  const [jump, setJump] = useState(null);

  useEffect(() => {
    document.getElementById("sa-page")?.scrollTo({ top: 0 });
  }, [mode]);

  // Picture taps scroll to that part of the latest results (after any mode switch has rendered).
  useEffect(() => {
    if (!jump) return undefined;
    const t = setTimeout(() => {
      const el = document.querySelector(`[data-testid="${jump}"]`) || document.querySelector('[data-testid="sa-overview"]');
      el?.scrollIntoView({ behavior: "smooth", block: "start" });
      el?.classList.add("journey-jump-flash");
      setTimeout(() => el?.classList.remove("journey-jump-flash"), 1600);
      setJump(null);
    }, 150);
    return () => clearTimeout(t);
  }, [jump, mode]);

  const close = () => {
    flush();
    onClose();
  };
  const start = () => {
    setView("assess");
    update((d) => ({ ...d, started: true }));
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

  const onArt = (k) => {
    if (!history.length) {
      if (!draft.started) start();
      setJump("sa-work");
      return;
    }
    if (mode === "assess") setView("overview");
    setTab(k === "progress" ? "progress" : "results");
    setJump(JUMP[k]);
  };

  const assessing = mode === "assess";
  const finished = mode === "overview" || mode === "results";
  const stepNum = assessing ? pageStepOf(step) : 1;
  const showStart = finished || (assessing && step?.type === "intro");
  return createPortal(
    <div id="sa-page" data-testid="self-assessment-page" data-mode={mode} className={`fixed inset-0 z-50 overflow-y-auto ${hidden ? "hidden" : ""} bg-gradient-to-b from-[#F3EFFE] to-[#EBE5FA] text-slate-800 pb-12`}>
      <SafetyBanner />
      <div className="max-w-6xl mx-auto px-4 pt-6">
        <PageHeader onBack={close} onQuickExit={onQuickExit} />
        <div data-testid="sa-artwork-mobile" className="lg:hidden max-w-md mx-auto mb-6">
          <ArtPicture tp="sa-art-mobile" art={SA_ART} onAction={onArt} />
        </div>
        <Hero
          title="Self Assessment"
          subtitle="Take a moment to reflect, understand yourself better, and track your progress as a co-parent."
          textClassName="hidden lg:block"
          pill={finished ? "Complete" : <>Step <span data-testid="sa-step-num">{stepNum}</span> of {PAGE_STEP_COUNT}</>}
          pct={finished ? 100 : Math.round((stepNum / PAGE_STEP_COUNT) * 100)}
        />
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          <div id="sa-work" data-testid="sa-work" className="lg:col-span-7 space-y-4 scroll-mt-4">
            <JourneySteps statuses={statusesFor(mode, step)} />
            {mode === "loading" ? (
              <div data-testid="sa-loading" className="bg-white rounded-2xl p-6 shadow-md border border-purple-100 mt-6 animate-pulse space-y-3">
                <div className="h-4 w-2/3 rounded bg-purple-100" />
                <div className="h-3 w-full rounded bg-slate-100" />
                <div className="h-10 w-full rounded-xl bg-slate-100" />
                <div className="h-10 w-full rounded-xl bg-slate-100" />
              </div>
            ) : assessing ? (
              <QuestionPanel
                step={step}
                draft={draft}
                update={update}
                onFinish={onFinish}
                onBack={currentIdx > 1 ? onBack : null}
                busy={busy}
                status={step?.type === "intro" ? null : status}
                previous={compareWithLast ? latest?.answers : null}
              />
            ) : (
              <div className="bg-white rounded-2xl p-5 shadow-md border border-purple-100 mt-6">
                <SaTabs tab={tab} onTab={setTab} />
                {tab === "progress" ? (
                  <ProgressOverTime history={history} onReached={onGoalReached} />
                ) : (
                  <OverviewPanel history={history} celebrate={mode === "results"} onStartNew={start} onClose={close} />
                )}
              </div>
            )}
            {tip.text && (
              <div className="lg:hidden">
                <TipBox tip={tip} loading={loading} testid="sa-ai-tip-inline" />
              </div>
            )}
            {showStart && <SharingNotice area="self-assessment" />}
            {showStart && (
              <div className="pt-4">
                <button
                  type="button"
                  data-testid="sa-start"
                  onClick={start}
                  className="w-full py-4 px-6 bg-purple-950 hover:bg-purple-900 text-white font-extrabold rounded-2xl shadow-xl hover:shadow-2xl transition-[transform,box-shadow,background-color] hover:-translate-y-0.5 flex items-center justify-center gap-3 text-lg border-2 border-purple-700/50 tracking-wider"
                >
                  <span>{history.length ? "START MY NEXT SELF-ASSESSMENT" : "START SELF-ASSESSMENT"}</span>
                  <i className="fa-solid fa-arrow-right"></i>
                </button>
              </div>
            )}
          </div>
          <div className="lg:col-span-5 space-y-6">
            <div data-testid="sa-artwork-desktop" className="hidden lg:block">
              <ArtPicture tp="sa-art" art={SA_ART} onAction={onArt} />
            </div>
            <AiInsightPanel tip={tip} loading={loading} safetyFlag={safetyFlag} onOpenBiffCoach={onOpenBiffCoach} chat={chat} />
          </div>
        </div>
        <BottomBanner />
      </div>
    </div>,
    document.body
  );
}

export default SelfAssessmentView;
