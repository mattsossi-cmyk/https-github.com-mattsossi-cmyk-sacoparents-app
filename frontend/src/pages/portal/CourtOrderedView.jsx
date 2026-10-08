import React, { useState } from "react";
import { createPortal } from "react-dom";
import { toast } from "sonner";

import { CourtAcceptDialog } from "./court/CourtAcceptDialog";
import { CourtChatPanel } from "./court/CourtChatPanel";
import { CourtChecklistCard } from "./court/CourtChecklistCard";
import { STEPS } from "./court/courtContent";
import { CourtHeader } from "./court/CourtHeader";
import { CourtJourneyArt } from "./court/CourtJourneyArt";
import { CourtPillarDialog } from "./court/CourtPillarDialog";
import { CourtStepDialog } from "./court/CourtStepDialog";
import { CourtModulesCard, CourtTools } from "./court/CourtTools";
import { useCourtCase } from "./court/useCourtCase";
import { useCourtChecklist } from "./court/useCourtChecklist";
import { useCourtCompare } from "./court/useCourtCompare";
import { useCourtSummary } from "./court/useCourtSummary";
import { useGuideChat } from "./guide/useGuideChat";
import { SafetyBanner, useLockScroll } from "./selfAssessment/SaChrome";

const BIFF_BOOK_URL = process.env.REACT_APP_BIFF_BOOK_URL;
const openTab = (url) => window.open(url, "_blank", "noopener,noreferrer");

// Full-page Court Ordered path (portal): interactive journey artwork, court tools, and a saved AI chat.
export function CourtOrderedView({ onBack, onQuickExit, courtKey, mediator, onVerify, modules, onOpenModule, onOpenCard, fb, onOpenParallel, onDownloadPdf, onOpenBiffHistory, alignUrl, safetyFlag, signedIn, hidden = false }) {
  const [hints, setHints] = useState(true);
  const [dialog, setDialog] = useState(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatDraft, setChatDraft] = useState("");
  const checklist = useCourtChecklist({ modules, courtKey, hidden });
  const summary = useCourtSummary(!hidden);
  const compare = useCourtCompare(!hidden);
  const cc = useCourtCase({ courtKey, savedName: checklist.data?.parent_name, onVerify, signedIn, alignUrl, onDownloadPdf });
  const chat = useGuideChat("/court-path/ai/chat", { modules: Object.fromEntries(modules.map((m) => [m.topic, m.status])), safety_flagged: !!safetyFlag });
  useLockScroll(!hidden);

  const items = Object.fromEntries((checklist.data?.items || []).map((i) => [i.key, i]));
  const statusOf = (card) => items[card]?.status || "loading";
  const close = () => setDialog(null);
  const openStep = (n) => {
    close();
    onOpenCard(STEPS[n - 1].card);
  };
  const askAi = (prompt) => {
    close();
    setChatDraft(prompt);
    setChatOpen(true);
  };

  const confirmAccept = async () => {
    const caseId = await cc.accept();
    if (!caseId) return;
    checklist.load();
    compare.load();
    close();
    const nextStep = STEPS.find((s) => statusOf(s.card) !== "done");
    const nextModule = modules.find((m) => m.status !== "completed");
    toast.success(`Court invite accepted for Case ${caseId}`, {
      description: nextStep ? `Next: ${nextStep.title}` : nextModule ? `Next: Module ${nextModule.letter}. ${nextModule.title}` : "Everything is complete. Your court-ready PDF is ready.",
    });
    if (nextStep) onOpenCard(nextStep.card);
    else if (nextModule) onOpenModule(nextModule);
  };

  const resources = [
    { key: "biff", icon: "fa-wand-magic-sparkles", title: "BIFF Communication Builder", sub: "Rewrite messages to be brief, informative, friendly, firm", onClick: () => { close(); onOpenBiffHistory(); } },
    { key: "parallel", icon: "fa-people-arrows", title: "Parallel Parenting Option Builder", sub: "Plan exchanges and communication with less contact", onClick: () => { close(); onOpenParallel(); } },
    { key: "pdf", icon: "fa-file-pdf", title: "Court-Ready Summary PDF", sub: "Download your summary report", onClick: () => { close(); cc.pdf(); } },
    { key: "checklist", icon: "fa-list-check", title: "Court Checklist PDF", sub: "What's done and what's left", onClick: () => { close(); checklist.download(); } },
    { key: "professional", icon: "fa-user-tie", title: "Your Professional's Site", sub: cc.alignHost, onClick: () => openTab(alignUrl) },
    { key: "book", icon: "fa-book-open", title: "BIFF for CoParent Communication", sub: "Book by Bill Eddy", onClick: () => openTab(BIFF_BOOK_URL) },
    { key: "hotline", icon: "fa-phone", title: "National DV Hotline: 1-800-799-7233", sub: "Free, confidential, 24/7. In danger? Call 911.", onClick: () => (window.location.href = "tel:18007997233") },
  ];

  return createPortal(
    <div id="court-page" data-testid="court-page" className={`fixed inset-0 z-50 overflow-y-auto ${hidden ? "hidden" : ""} bg-[#f3eff9] text-[#202124] pb-28`}>
      <SafetyBanner tp="court" icon="fa-scale-balanced" label="Court Ordered Portal" />
      <div className="max-w-[900px] mx-auto px-[15px] pt-4">
        <CourtHeader onBack={onBack} onQuickExit={onQuickExit} hints={hints} onToggleHints={() => setHints((h) => !h)} />
        <CourtJourneyArt
          hints={hints}
          statusOf={statusOf}
          onAccept={() => setDialog({ type: "accept" })}
          onStep={(step) => setDialog({ type: "step", step })}
          onPillar={(pillar) => {
            compare.load();
            setDialog({ type: "pillar", pillar });
          }}
        />
        <CourtTools cc={cc} courtKey={courtKey} compare={compare} onCase={() => setDialog({ type: "accept" })} onBiff={onOpenBiffHistory} />
        <div className="grid md:grid-cols-2 gap-6 items-start">
          <CourtModulesCard modules={modules} onOpenModule={onOpenModule} />
          <CourtChecklistCard checklist={checklist} />
        </div>
        <p data-testid="court-footer" className="mt-12 text-center text-xs text-[#5f6368] font-medium">
          &copy; SA CoParents &bull; Court Ordered Pathway &bull; Powered by Emergent AI &bull; General guidance, not legal advice
        </p>
      </div>
      {!hidden && (
        <>
          <CourtAcceptDialog open={dialog?.type === "accept"} onClose={close} cc={cc} mediator={mediator} courtKey={courtKey} onConfirm={confirmAccept} />
          <CourtStepDialog
            step={dialog?.type === "step" ? dialog.step : null}
            item={dialog?.step && items[dialog.step.card]}
            onClose={close}
            onOpen={() => openStep(dialog.step.n)}
            onAskAi={() => askAi(`Help me get started with ${dialog.step.title}.`)}
          />
          <CourtPillarDialog
            pillar={dialog?.type === "pillar" ? dialog.pillar : null}
            summary={summary}
            resources={resources}
            compare={compare}
            onClose={close}
            onOpenStep={openStep}
            onEnterCase={() => setDialog({ type: "accept" })}
          />
          <CourtChatPanel chat={chat} open={chatOpen} onOpenChange={setChatOpen} draft={chatDraft} fb={fb} onOpenStep4={() => onOpenCard("card4", { builder: true })} />
        </>
      )}
    </div>,
    document.body
  );
}

export default CourtOrderedView;
