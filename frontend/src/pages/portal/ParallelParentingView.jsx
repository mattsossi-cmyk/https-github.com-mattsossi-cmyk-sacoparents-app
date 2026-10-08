import React, { useState } from "react";
import { createPortal } from "react-dom";
import { toast } from "sonner";

import { api } from "../../lib/api";
import { PpChat } from "./parallel/PpChat";
import { PpHeader } from "./parallel/PpHeader";
import { PpStep } from "./parallel/PpStep";
import { PpSummary } from "./parallel/PpSummary";
import { PpWelcome } from "./parallel/PpWelcome";
import content from "./parallel/ppContent.json";
import { usePpChat, usePpPlan } from "./parallel/usePp";
import { SafetyBanner, useLockScroll } from "./selfAssessment/SaChrome";

const STEPS = content.steps;

async function downloadPlan() {
  const res = await api.post("/parallel-parenting/pdf", {}, { responseType: "blob" });
  const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "SA_CoParents_Parallel_Parenting_Plan.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}

// Full-page Parallel Parenting Option Builder (Self Journey). Screens: welcome, steps 0-5, summary.
export function ParallelParentingView({ onClose, onQuickExit, safetyFlag, hidden = false }) {
  const pp = usePpPlan();
  const [screen, setScreen] = useState("welcome");
  const [downloading, setDownloading] = useState(false);
  const stepIndex = typeof screen === "number" ? screen : null;
  const chat = usePpChat({ step: stepIndex != null ? STEPS[stepIndex].key : null, safetyFlag });
  useLockScroll(!hidden);

  const show = (next) => {
    setScreen(next);
    document.getElementById("pp-page")?.scrollTo({ top: 0, behavior: "smooth" });
  };
  const openStep = (i) => {
    show(i);
    pp.goStep(i);
  };
  const openSummary = () => {
    show("summary");
    pp.goStep(STEPS.length, { completed: true });
  };
  const next = (i) => {
    pp.requestTip(STEPS[i], safetyFlag);
    if (i + 1 < STEPS.length) openStep(i + 1);
    else openSummary();
  };
  const start = () => (pp.plan.step >= STEPS.length ? openSummary() : openStep(pp.plan.step));
  const download = async () => {
    setDownloading(true);
    try {
      await pp.save();
      await downloadPlan();
      toast.success("Your Parallel Parenting Plan PDF is ready.");
    } catch {
      toast.error("Couldn't build your plan PDF right now. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  const body = !pp.plan ? (
    <div data-testid="pp-loading" className="h-64 rounded-3xl bg-white border border-purple-100 animate-pulse" />
  ) : screen === "welcome" ? (
    <div className="max-w-5xl mx-auto space-y-6">
      <PpWelcome content={content} plan={pp.plan} onStart={start} onOpenStep={openStep} onSummary={openSummary} />
      <div className="max-w-3xl mx-auto">
        <PpChat chat={chat} />
      </div>
    </div>
  ) : (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      <div className="lg:col-span-8">
        {screen === "summary" ? (
          <PpSummary content={content} plan={pp.plan} tipBusy={pp.tipBusy} onEdit={openStep} onDownload={download} downloading={downloading} />
        ) : (
          <PpStep
            step={STEPS[stepIndex]}
            index={stepIndex}
            total={STEPS.length}
            plan={pp.plan}
            prevStep={STEPS[stepIndex - 1]}
            tipBusy={pp.tipBusy}
            tipError={pp.tipError}
            onPick={pp.setAnswer}
            onNote={pp.setNote}
            onBack={() => (stepIndex === 0 ? show("welcome") : openStep(stepIndex - 1))}
            onNext={() => next(stepIndex)}
          />
        )}
      </div>
      <aside className="lg:col-span-4 lg:sticky lg:top-24">
        <PpChat chat={chat} />
      </aside>
    </div>
  );

  return createPortal(
    <div id="pp-page" data-testid="pp-page" className={`fixed inset-0 z-50 overflow-y-auto bg-[#f8f6fc] text-gray-800 ${hidden ? "hidden" : ""}`}>
      <SafetyBanner tp="pp" />
      <PpHeader
        stepIndex={stepIndex}
        total={STEPS.length}
        title={stepIndex != null ? STEPS[stepIndex].title : ""}
        onBack={onClose}
        onHome={() => show("welcome")}
        onQuickExit={onQuickExit}
      />
      <main className="max-w-6xl mx-auto px-4 py-6 md:py-8">
        {pp.loadError && (
          <p data-testid="pp-save-error" className="mb-4 text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-xl px-3 py-2">
            We couldn't reach your saved plan. Please check your connection; your changes may not be saved.
          </p>
        )}
        {body}
      </main>
      <p className="pb-10 text-center text-xs text-slate-500 font-medium">
        &copy; SA CoParents &bull; Parallel Parenting Option Builder &bull; Powered by Emergent AI
      </p>
    </div>,
    document.body
  );
}

export default ParallelParentingView;
