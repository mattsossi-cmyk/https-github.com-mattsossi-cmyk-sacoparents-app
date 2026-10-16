import React, { useState } from "react";
import { toast } from "sonner";

import { useGuideChat } from "./guide/useGuideChat";
import { useAiNotice } from "../../components/aiNotice/AiNoticeProvider";
import { SharingNotice } from "../../components/privacy/SharingNotice";
import { PpActionButton } from "./parallel/PpActionButton";
import { PpChecklist } from "./parallel/PpChecklist";
import { PpStep } from "./parallel/PpStep";
import { PpSummary } from "./parallel/PpSummary";
import { PpWelcome } from "./parallel/PpWelcome";
import content from "./parallel/ppContent.json";
import { downloadPdf, usePpPlan } from "./parallel/usePp";
import { JourneyPage } from "./selfJourney/JourneyPage";
import { PP_ART } from "./selfJourney/selfJourneyArt";

const STEPS = content.steps;
const CHECKS = content.checklists;
const TOTAL = STEPS.reduce((n, s) => n + s.questions.length, 0);
const SUGGESTIONS = ["What is parallel parenting?", "How do I keep exchanges calm?", "What if the other parent ignores the plan?"];
const GREETING = "Hi, I'm your Guide. Ask me anything about parallel parenting or the choices on this page.";
const SUBTITLE =
  "Create a child-focused parallel parenting plan that works for your family. Choose options, review safeguards, and check your plan against your own court order.";

function heroFor(screen, stepIndex, checkIndex, made) {
  if (stepIndex != null) return { pill: `Step ${stepIndex + 1} of ${STEPS.length}`, pct: Math.round(((stepIndex + 1) / STEPS.length) * 100) };
  if (checkIndex >= 0) return { pill: `Quick check ${checkIndex + 1} of ${CHECKS.length}`, pct: Math.round(((checkIndex + 1) / CHECKS.length) * 100) };
  if (screen === "summary") return { pill: "Your plan", pct: 100 };
  return { pill: `${made} of ${TOTAL} choices made`, pct: Math.round((made / TOTAL) * 100) };
}

const actionLabel = (plan) =>
  plan.step >= STEPS.length ? "VIEW MY PARALLEL PARENTING PLAN" : plan.step > 0 || Object.keys(plan.answers).length ? "CONTINUE MY PARALLEL PARENTING PLAN" : "START MY PARALLEL PARENTING PLAN";

// Full-page Parallel Parenting Option Builder. Screens: welcome, steps 0-5, quick checks ("check:<key>"), summary.
export function ParallelParentingView({ onClose, onQuickExit, safetyFlag, hidden = false, initialScreen = "welcome" }) {
  const pp = usePpPlan();
  const { acked: aiAcked } = useAiNotice();
  const [screen, setScreen] = useState(initialScreen);
  const [downloading, setDownloading] = useState(false);
  const [historyTick, setHistoryTick] = useState(0);
  const [notesBusy, setNotesBusy] = useState(false);
  const stepIndex = typeof screen === "number" ? screen : null;
  const checkIndex = CHECKS.findIndex((c) => `check:${c.key}` === screen);
  const chat = useGuideChat("/parallel-parenting/ai/chat", { step: stepIndex != null ? STEPS[stepIndex].key : null, safety_flagged: !!safetyFlag });
  const refreshHistory = () => setHistoryTick((t) => t + 1);

  const show = (next) => {
    setScreen(next);
    document.getElementById("pp-page")?.scrollTo({ top: 0, behavior: "smooth" });
  };
  const openStep = (i) => {
    show(i);
    pp.goStep(i);
  };
  const openCheck = (i) => show(`check:${CHECKS[i].key}`);
  const openSummary = () => {
    show("summary");
    pp.goStep(STEPS.length, { completed: true }).then(refreshHistory);
  };
  const next = (i) => {
    // The step tip is AI-written, so it's only asked for once the AI notice is accepted.
    if (aiAcked) pp.requestTip(STEPS[i], safetyFlag);
    if (i + 1 < STEPS.length) openStep(i + 1);
    else openCheck(0);
  };
  const start = () => (pp.plan.step >= STEPS.length ? openSummary() : openStep(pp.plan.step));
  const openArt = (k) => {
    const s = PP_ART.items.find((it) => it.key === k).screen;
    if (typeof s === "number") openStep(s);
    else show(s);
  };
  const download = async () => {
    setDownloading(true);
    try {
      await pp.save();
      await downloadPdf("/parallel-parenting/pdf", "SA_CoParents_Parallel_Parenting_Plan.pdf");
      refreshHistory();
      toast.success("Your Parallel Parenting Plan PDF is ready.");
    } catch {
      toast.error("Couldn't build your plan PDF right now. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  const courtNotes = async () => {
    setNotesBusy(true);
    try {
      await pp.save();
      await downloadPdf("/parallel-parenting/court-notes/pdf", "SA_CoParents_Court_Order_Notes.pdf");
      toast.success("Your Court-Order Notes are downloading.");
    } catch {
      toast.error("Couldn't build your Court-Order Notes right now. Please try again.");
    } finally {
      setNotesBusy(false);
    }
  };

  const made = pp.plan ? Object.keys(pp.plan.answers).length : 0;
  let body;
  if (!pp.plan) body = <div data-testid="pp-loading" className="h-64 rounded-3xl bg-white border border-purple-100 animate-pulse" />;
  else if (screen === "welcome") body = <PpWelcome content={content} plan={pp.plan} onStart={start} onOpenStep={openStep} onOpenCheck={openCheck} onSummary={openSummary} />;
  else if (screen === "summary")
    body = (
      <PpSummary
        content={content}
        plan={pp.plan}
        tipBusy={pp.tipBusy}
        onEdit={openStep}
        onEditCheck={openCheck}
        onDownload={download}
        downloading={downloading}
        historyTick={historyTick}
        onCourtNotes={courtNotes}
        notesBusy={notesBusy}
      />
    );
  else if (checkIndex >= 0)
    body = (
      <PpChecklist
        list={CHECKS[checkIndex]}
        index={checkIndex}
        total={CHECKS.length}
        plan={pp.plan}
        onToggle={pp.toggleCheck}
        onNote={pp.setNote}
        onBack={() => (checkIndex === 0 ? show("welcome") : openCheck(checkIndex - 1))}
        onNext={() => (checkIndex + 1 < CHECKS.length ? openCheck(checkIndex + 1) : openSummary())}
        onCourtNotes={courtNotes}
        notesBusy={notesBusy}
      />
    );
  else
    body = (
      <PpStep
        step={STEPS[stepIndex]}
        index={stepIndex}
        total={STEPS.length}
        plan={pp.plan}
        prevStep={STEPS[stepIndex - 1]}
        tipBusy={pp.tipBusy}
        tipError={pp.tipError}
        aiNeeded={!aiAcked}
        onPick={pp.setAnswer}
        onNote={pp.setNote}
        onBack={() => (stepIndex === 0 ? show("welcome") : openStep(stepIndex - 1))}
        onNext={() => next(stepIndex)}
      />
    );

  return (
    <JourneyPage
      tp="pp"
      hero={{ title: "Parallel Parenting Option Builder", subtitle: SUBTITLE, ...heroFor(screen, stepIndex, checkIndex, made) }}
      art={PP_ART}
      onArt={openArt}
      artState={{ activeKey: PP_ART.items.find((it) => it.screen === screen)?.key }}
      chat={chat}
      chatProps={{ title: "Parallel Parenting Guide", greeting: GREETING, suggestions: SUGGESTIONS }}
      onBack={onClose}
      onQuickExit={onQuickExit}
      hidden={hidden}
      footer="Parallel Parenting Option Builder"
      banner
    >
      {pp.loadError && (
        <p data-testid="pp-save-error" className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-xl px-3 py-2">
          We couldn't reach your saved plan. Please check your connection; your changes may not be saved.
        </p>
      )}
      {body}
      {pp.plan && (screen === "welcome" || screen === "summary") && <SharingNotice area="parallel-parenting" />}
      {pp.plan &&
        (screen === "welcome" ? (
          <PpActionButton label={actionLabel(pp.plan)} onClick={start} />
        ) : (
          <PpActionButton label="SEE ALL STEPS AND QUICK CHECKS" onClick={() => show("welcome")} />
        ))}
    </JourneyPage>
  );
}

export default ParallelParentingView;
