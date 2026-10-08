import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { toast } from "sonner";

import { BiffHistory, BiffMilestones } from "./BiffTab";
import { BiffBookLink, BiffSnapshotCard } from "./JourneyDrawers";
import { BeforeAfterCard } from "./commBuilder/BeforeAfterCard";
import { DraftCard } from "./commBuilder/DraftCard";
import { ResponseCard } from "./commBuilder/ResponseCard";
import { AiInsightPanel } from "./selfAssessment/AiInsightPanel";
import { JourneySteps } from "./selfAssessment/JourneySteps";
import { SaArtwork } from "./selfAssessment/SaArtwork";
import { BottomBanner, Hero, PageHeader, SafetyBanner } from "./selfAssessment/SaChrome";
import { useSelfAssessmentHistory } from "./selfAssessment/useSelfAssessmentHistory";

const STEP_LABELS = { 1: "Write", 2: "Transform", 3: "Copy or Save" };
const CB_ALT =
  "SA CoParents Communication Builder: child-focused templates, clear and respectful BIFF language, situations and solutions, plan and track. Less conflict. More clarity. A brighter future for your child.";

// The 4 journey cards mirror the parent's real Self-Assessment progress.
const saStatuses = (history) => {
  if (!history.length) return { reflect: "current", identify: "upcoming", goals: "upcoming", track: "upcoming" };
  const latest = history[history.length - 1];
  return { reflect: "done", identify: "done", goals: latest.goal ? "done" : "current", track: history.length > 1 ? "done" : "current" };
};

const tipFor = ({ transformed, loading, riskLabel, flagList, greyRock }) => {
  if (loading) return { label: "Reading your draft…", text: "" };
  if (!transformed)
    return { label: "Welcome", text: "Write or paste your message, then tap Transform. I'll check the tone and suggest a calmer, child-focused version." };
  if (greyRock)
    return { label: "Grey-rock tip", text: "Keep it to logistics only: no feelings, no apologies, no open questions. Shorter is safer." };
  if (riskLabel === "Escalation Flag")
    return {
      label: "Based on your draft, I'm noting potential communication friction. Here's a tip:",
      text: `Focus on objective logistics to reduce emotional impact and keep your child at the center.${flagList.length ? ` Watch for: ${flagList.join(", ")}.` : ""}`,
    };
  return { label: "Your draft looks calm and factual", text: "Nice work keeping it factual. Keep it brief, and end with one clear next step or date." };
};

function useLockScroll(active) {
  useEffect(() => {
    if (!active) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [active]);
}

// Full-page Communication Builder, opened from the welcome artwork's Communication Builder card.
export function CommunicationBuilderView({ open, focus, onClose, onQuickExit, onStartSelfAssessment, userId, greyRock, biff, extras }) {
  const { history } = useSelfAssessmentHistory(userId);
  const [transformed, setTransformed] = useState(false);
  const [acted, setActed] = useState(false);
  const [baMode, setBaMode] = useState("example");
  useLockScroll(open);
  useEffect(() => {
    if (!open) return;
    setTransformed(false);
    setActed(false);
    setBaMode("example");
    if (focus === "history") setTimeout(() => document.getElementById("cb-history")?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
    else document.getElementById("cb-page")?.scrollTo({ top: 0 });
  }, [open, focus]);
  if (!open) return null;

  const { rawInput, setRawInput, transform, applyPreset, riskLabel, flagList, biffOutput, biffLoading, biffError } = biff;
  const run = (fn) => {
    setTransformed(true);
    setActed(false);
    setBaMode("yours");
    fn();
  };
  const onTransform = () => rawInput.trim() && run(() => transform(rawInput));
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(biffOutput);
      setActed(true);
      toast.success("Peaceful response copied.");
    } catch {
      toast.error("Couldn't copy. Please select the text and copy it.");
    }
  };
  const stage = acted ? 4 : !transformed ? 1 : biffLoading ? 2 : 3;
  const pill = stage === 4 ? "Done · Copied or saved" : <>Step <span data-testid="cb-step-num">{stage}</span> of 3 · {STEP_LABELS[stage]}</>;
  const tip = tipFor({ transformed, loading: biffLoading, riskLabel, flagList, greyRock });
  // Above the draft box until the first Transform, then below the response card.
  const beforeAfter = (
    <BeforeAfterCard
      mode={baMode}
      onMode={setBaMode}
      canShowYours={transformed}
      original={rawInput}
      transformed={biffOutput}
      loading={biffLoading}
      riskLabel={riskLabel}
      greyRock={greyRock}
    />
  );

  return createPortal(
    <div id="cb-page" data-testid="comm-builder-page" className="fixed inset-0 z-50 overflow-y-auto bg-gradient-to-b from-[#F3EFFE] to-[#EBE5FA] text-slate-800 pb-12">
      <SafetyBanner tp="cb" />
      <div className="max-w-6xl mx-auto px-4 pt-6">
        <PageHeader tp="cb" onBack={onClose} onQuickExit={onQuickExit} backLabel="Back" />
        <SaArtwork testid="cb-artwork-mobile" name="comm-builder-art" alt={CB_ALT} className="lg:hidden max-w-md mx-auto mb-6" />
        <Hero
          tp="cb"
          title="Communication Builder"
          subtitle="Draft calm, child-centered messages with real-time AI BIFF framing (Brief, Informative, Friendly, Firm)."
          textClassName="hidden lg:block"
          pill={pill}
          pct={stage === 4 ? 100 : Math.round((stage / 3) * 100)}
        />
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          <div className="lg:col-span-7 space-y-4">
            <p className="text-[11px] font-bold uppercase tracking-wider text-purple-700">Your Self-Assessment progress</p>
            <JourneySteps statuses={saStatuses(history)} />
            {!transformed && beforeAfter}
            <DraftCard
              value={rawInput}
              onChange={setRawInput}
              onPreset={(key) => run(() => applyPreset(key, 0))}
              onTransform={onTransform}
              busy={biffLoading}
            />
            <ResponseCard
              output={biffOutput}
              loading={biffLoading}
              error={biffError}
              riskLabel={riskLabel}
              flagList={flagList}
              transformed={transformed}
              greyRock={greyRock}
              onCopy={copy}
              onToneSafe={() => {
                biff.copyToneSafe();
                setActed(true);
              }}
              onArchive={() => {
                biff.logCommunication();
                setActed(true);
              }}
            />
            {transformed && beforeAfter}
            <div data-testid="cb-more-tools" className="space-y-4 pt-2">
              <BiffSnapshotCard rawInput={rawInput} biffOutput={biffOutput} onSaveBiffSnapshot={biff.onSaveBiffSnapshot} onSaved={() => setActed(true)} />
              <div id="cb-history" data-testid="cb-history" className="scroll-mt-6">
                <BiffHistory biffLogs={extras.biffLogs} />
              </div>
              <BiffMilestones safetyFlagged={greyRock} {...extras} />
              <BiffBookLink />
            </div>
            <div className="pt-4">
              <button
                type="button"
                data-testid="cb-start-self-assessment"
                onClick={onStartSelfAssessment}
                className="w-full py-4 px-6 bg-purple-950 hover:bg-purple-900 text-white font-extrabold rounded-2xl shadow-xl hover:shadow-2xl transition-[transform,box-shadow,background-color] hover:-translate-y-0.5 flex items-center justify-center gap-3 text-lg border-2 border-purple-700/50 tracking-wider"
              >
                <span>START SELF-ASSESSMENT</span>
                <i className="fa-solid fa-arrow-right"></i>
              </button>
            </div>
          </div>
          <div className="lg:col-span-5 space-y-6">
            <SaArtwork testid="cb-artwork-desktop" name="comm-builder-art" alt={CB_ALT} className="hidden lg:block" />
            <AiInsightPanel
              tip={tip}
              loading={biffLoading}
              safetyFlag={greyRock}
              onOpenBiffCoach={onTransform}
              biffBusy={biffLoading || !rawInput.trim()}
              onUseTemplate={(text) => {
                setRawInput(text);
                setTransformed(false);
                toast.success("Template added to your draft. Fill in the [brackets], then tap Transform.");
              }}
            />
          </div>
        </div>
        <BottomBanner tp="cb" />
      </div>
    </div>,
    document.body
  );
}

export default CommunicationBuilderView;
