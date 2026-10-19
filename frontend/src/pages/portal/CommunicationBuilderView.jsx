import React, { useEffect, useState, useRef } from "react";
import { useDialogFocus } from "../../lib/useDialogFocus";
import { createPortal } from "react-dom";
import { toast } from "sonner";

import { BiffHistory, BiffMilestones } from "./BiffTab";
import { useAiGuard } from "../../components/aiNotice/AiGuard";
import { SharingNotice } from "../../components/privacy/SharingNotice";
import { BiffBookLink, BiffSnapshotCard } from "./JourneyDrawers";
import { BeforeAfterCard } from "./commBuilder/BeforeAfterCard";
import { DraftCard } from "./commBuilder/DraftCard";
import { ResponseCard } from "./commBuilder/ResponseCard";
import { AiInsightPanel } from "./selfAssessment/AiInsightPanel";
import { SaArtwork } from "./selfAssessment/SaArtwork";
import { BottomBanner, Hero, PageHeader, SafetyBanner } from "./selfAssessment/SaChrome";

const STEP_LABELS = { 1: "Write", 2: "Suggest", 3: "Copy or Save" };
const CB_ALT =
  "SA CoParents Communication Builder: child-focused templates, clear and respectful BIFF language, situations and solutions, plan and track. Less conflict. More clarity. A brighter future for your child.";

const tipFor = ({ status, riskLabel, flagList, greyRock }) => {
  if (status === "loading") return { label: "Reading your draft…", text: "" };
  if (status === "unavailable")
    return { label: "Suggested wording isn't available right now", text: "AI didn't check this draft, so there's no tone rating. Tap Try again, or use the fill-in template." };
  if (status !== "ai")
    return { label: "Welcome", text: "Write or paste your message, then tap Get suggested wording. AI will check the tone and suggest calmer, child-focused wording." };
  if (greyRock)
    return { label: "Grey-rock tip", text: "Keep it to logistics only: no feelings, no apologies. Shorter is safer." };
  if (riskLabel === "Escalation Flag")
    return {
      label: "AI noticed possible friction in your draft. Here's a tip:",
      text: `Focus on objective logistics to reduce emotional impact and keep your child at the center.${flagList.length ? ` Watch for: ${flagList.join(", ")}.` : ""}`,
    };
  return { label: "AI didn't find friction cues", text: "Keep it brief, and end with one clear next step or date." };
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

// Full-page Communication Builder, opened from the welcome page or the Self Journey card.
export function CommunicationBuilderView({ open, focus, onClose, onQuickExit, greyRock, biff, extras }) {
  const [transformed, setTransformed] = useState(false);
  const [acted, setActed] = useState(false);
  const [baMode, setBaMode] = useState("example");
  const guard = useAiGuard("communication_builder", biff.rawInput);
  useLockScroll(open);
  const pageRef = useRef(null);
  useDialogFocus(open, pageRef, onClose);
  useEffect(() => {
    if (!open) return;
    setTransformed(false);
    setActed(false);
    setBaMode("example");
    if (focus === "history") setTimeout(() => document.getElementById("cb-history")?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
    else document.getElementById("cb-page")?.scrollTo({ top: 0 });
  }, [open, focus]);
  if (!open) return null;

  const { rawInput, setRawInput, transform, applyPreset, riskLabel, flagList, biffOutput, biffLoading, biffStatus } = biff;
  const run = (fn) => {
    setTransformed(true);
    setActed(false);
    setBaMode("yours");
    fn();
  };
  // The AI notice and the browser check run before anything is sent (button, Try again and the template chips).
  const onTransform = async () => {
    if (!rawInput.trim() || !(await guard.confirmSend(rawInput))) return;
    run(() => transform(rawInput));
  };
  const onPreset = async (key) => (await guard.confirmSend("")) && run(() => applyPreset(key, 0));
  const edit = (text) => {
    setRawInput(text);
    setTransformed(false);
    setActed(false);
  };
  const applyTemplate = (text) => {
    edit(text);
    toast.success("Template added to your draft. Fill in the [brackets], then tap Get suggested wording.");
  };
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(biffOutput);
      setActed(true);
      toast.success("Suggested wording copied.");
    } catch {
      toast.error("Couldn't copy. Please select the text and copy it.");
    }
  };
  const stage = acted ? 4 : !transformed ? 1 : biffLoading ? 2 : 3;
  const pill = stage === 4 ? "Done · Copied or saved" : <>Step <span data-testid="cb-step-num">{stage}</span> of 3 · {STEP_LABELS[stage]}</>;
  const tip = tipFor({ status: biffStatus, riskLabel, flagList, greyRock });
  // Above the draft box until the first suggestion, then below the response card.
  const beforeAfter = (
    <BeforeAfterCard mode={baMode} onMode={setBaMode} canShowYours={transformed} original={rawInput} transformed={biffOutput} status={biffStatus} riskLabel={riskLabel} greyRock={greyRock} />
  );

  return createPortal(
    <div ref={pageRef} id="cb-page" role="dialog" aria-modal="true" aria-label="Communication Builder" tabIndex={-1} data-testid="comm-builder-page" className="fixed inset-0 z-50 overflow-y-auto overflow-x-hidden bg-gradient-to-b from-[#F3EFFE] to-[#EBE5FA] text-slate-800 pb-12 outline-none">
      <SafetyBanner tp="cb" />
      <div className="max-w-6xl mx-auto px-4 pt-6">
        <PageHeader tp="cb" onBack={onClose} onQuickExit={onQuickExit} backLabel="Back" />
        <SaArtwork testid="cb-artwork-mobile" name="comm-builder-art" alt={CB_ALT} className="lg:hidden max-w-md mx-auto mb-6" />
        <Hero
          tp="cb"
          title="Communication Builder"
          subtitle="Draft calm, child-centered messages. When you ask, AI suggests BIFF wording (Brief, Informative, Friendly, Firm). You copy it and send it yourself."
          textClassName="hidden lg:block"
          pill={pill}
          pct={stage === 4 ? 100 : Math.round((stage / 3) * 100)}
        />
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          <div className="lg:col-span-7 space-y-4">
            {!transformed && beforeAfter}
            <DraftCard value={rawInput} onChange={edit} onPreset={onPreset} onTransform={onTransform} busy={biffLoading} guard={guard} />
            <ResponseCard
              output={biffOutput}
              status={transformed ? biffStatus : "idle"}
              raw={rawInput}
              riskLabel={riskLabel}
              flagList={flagList}
              greyRock={greyRock}
              onCopy={copy}
              onRetry={onTransform}
              onUseTemplate={applyTemplate}
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
            <SharingNotice area="communication-builder" />
          </div>
          <div className="lg:col-span-5 space-y-6">
            <SaArtwork testid="cb-artwork-desktop" name="comm-builder-art" alt={CB_ALT} className="hidden lg:block" />
            <AiInsightPanel tip={tip} loading={biffLoading} safetyFlag={greyRock} onOpenBiffCoach={onTransform} biffBusy={biffLoading || !rawInput.trim()} onUseTemplate={applyTemplate} />
          </div>
        </div>
        <BottomBanner tp="cb" />
      </div>
    </div>,
    document.body
  );
}

export default CommunicationBuilderView;
