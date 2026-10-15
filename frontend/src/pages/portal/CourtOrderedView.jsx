import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { toast } from "sonner";

import { CourtAcceptDialog } from "./court/CourtAcceptDialog";
import { CourtAgreeCard } from "./court/CourtAgreement";
import { CourtCelebration } from "./court/CourtCelebration";
import { CourtChatInline, CourtChatPanel } from "./court/CourtChatPanel";
import { MENU, PILLARS, STEPS } from "./court/courtContent";
import { CourtJourneyArt } from "./court/CourtJourneyArt";
import { AcceptCard } from "./court/CourtJourneyCards";
import { CourtMenu } from "./court/CourtMenu";
import { CourtCompleteCard } from "./court/CourtCompleteCard";
import { CourtMoreTools } from "./court/CourtMoreTools";
import { CourtPillarDialog } from "./court/CourtPillarDialog";
import { CourtReports } from "./court/CourtReports";
import { CourtStepDialog } from "./court/CourtStepDialog";
import { useCourtCase } from "./court/useCourtCase";
import { useCourtChecklist } from "./court/useCourtChecklist";
import { useCourtCompare } from "./court/useCourtCompare";
import { useCourtRequested } from "./court/useCourtRequested";
import { useCourtSummary } from "./court/useCourtSummary";
import { useGuideChat } from "./guide/useGuideChat";
import { Hero, PageHeader, SafetyBanner, useLockScroll } from "./selfAssessment/SaChrome";

const BIFF_BOOK_URL = process.env.REACT_APP_BIFF_BOOK_URL;
const AGREED_MARK = " (agreed): ";
const openTab = (url) => window.open(url, "_blank", "noopener,noreferrer");

// Full-page Court Ordered path (portal): interactive journey artwork, court tools, and a saved AI chat.
export function CourtOrderedView({ onBack, onQuickExit, courtKey, mediator, onVerify, modules, onOpenModule, onOpenCard, onOpenChildNeeds, assessDone = {}, ppDone = false, fb, onOpenParallel, onDownloadPdf, onOpenBiffHistory, alignUrl, safetyFlag, signedIn, hidden = false }) {
  const [hints, setHints] = useState(true);
  const [dialog, setDialog] = useState(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatDraft, setChatDraft] = useState("");
  const checklist = useCourtChecklist({ modules, courtKey, hidden });
  const summary = useCourtSummary(!hidden);
  const compare = useCourtCompare(!hidden);
  const requested = useCourtRequested(signedIn);
  const cc = useCourtCase({ courtKey, savedName: checklist.data?.parent_name, onVerify, signedIn, alignUrl, onDownloadPdf });
  const chat = useGuideChat("/court-path/ai/chat", { modules: Object.fromEntries(modules.map((m) => [m.topic, m.status])), safety_flagged: !!safetyFlag });
  useLockScroll(!hidden);
  const progress = compare.data?.state === "ready" ? compare.data.progress : null;
  const celebrate = !hidden && !!progress?.all_agreed && !progress.celebrated;
  useEffect(() => {
    if (celebrate) setDialog(null);
  }, [celebrate]);

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

  // "What we agreed" notes -> Foundation Statement "Agreed co-parenting principles & values"; lines already there are skipped.
  const lineOf = (r) => `${r.area}${AGREED_MARK}${r.note}`;
  const step4 = {
    has: (r) => (fb.fields.co_values || "").includes(lineOf(r)),
    add: async (rows) => {
      const current = (fb.fields.co_values || "").trim();
      const todo = rows.filter((r) => r.note && !current.includes(lineOf(r)));
      if (!todo.length) {
        toast.message("These agreements are already in your Foundation Statement.");
        return;
      }
      // An edited note replaces that area's earlier line instead of adding a second one.
      let lines = current ? current.split("\n") : [];
      todo.forEach((r) => {
        const at = lines.findIndex((l) => l.startsWith(`${r.area}${AGREED_MARK}`));
        if (at >= 0) lines[at] = lineOf(r);
        else lines = [...lines, lineOf(r)];
      });
      const merged = lines.join("\n");
      if (merged.length > 3000) {
        toast.error("Your Foundation Statement's principles & values box is full. Shorten it there, then try again.");
        return;
      }
      const ok = await fb.updateMany({ co_values: merged });
      toast.success(`Added ${todo.length} agreement${todo.length > 1 ? "s" : ""} to your Foundation Statement`, {
        description: ok ? "In 'Agreed co-parenting principles & values'." : "Saved on this device. Open your Foundation Statement and tap Save.",
        action: { label: "Open Foundation Statement", onClick: () => onOpenCard("card4", { builder: true }) },
      });
    },
  };

  const CARD_OF = { coparent: "card2", self: "card1", foundation: "card4" };
  const statusFor = (key) => (CARD_OF[key] ? statusOf(CARD_OF[key]) : (key === "parallel" ? ppDone : assessDone[key]) ? "done" : "todo");
  const openOption = (key) => {
    if (CARD_OF[key]) onOpenCard(CARD_OF[key]);
    else if (key === "parallel") onOpenParallel();
    else onOpenChildNeeds(key, null);
  };

  const confirmAccept = async () => {
    const caseId = await cc.accept();
    if (!caseId) return;
    checklist.load();
    compare.load();
    const asked = await requested.reload();
    close();
    const next = MENU.find((o) => asked.includes(o.key) && statusFor(o.key) !== "done");
    toast.success(`Court invite accepted for Case ${caseId}`, {
      description: next ? `Next: ${next.title}` : "Tick the assessments your professional asked for, then open them in any order.",
    });
    if (next) openOption(next.key);
    else document.querySelector('[data-testid="court-menu"]')?.scrollIntoView({ behavior: "smooth", block: "start" });
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

  const asked = MENU.filter((o) => requested.keys.includes(o.key));
  const counted = asked.length ? asked : MENU;
  const doneCount = counted.filter((o) => statusFor(o.key) === "done").length;
  const pill = (
    <span data-testid="court-progress-text">
      <span data-testid="court-progress-done">{doneCount}</span> of {counted.length} {asked.length ? "requested " : ""}done
    </span>
  );
  const openPillar = (pillar) => {
    compare.load();
    setDialog({ type: "pillar", pillar });
  };
  const openStep4 = () => onOpenCard("card4", { builder: true });

  return createPortal(
    <div id="court-page" data-testid="court-page" className={`fixed inset-0 z-50 overflow-y-auto ${hidden ? "hidden" : ""} bg-gradient-to-b from-[#F3EFFE] to-[#EBE5FA] text-slate-800 pb-28`}>
      <SafetyBanner tp="court" icon="fa-scale-balanced" label="Court Ordered Portal" />
      <div className="max-w-6xl mx-auto px-4 pt-6">
        <PageHeader tp="court" onBack={onBack} onQuickExit={onQuickExit} backLabel="Back" tagline="Start with Alignment • End with Agreement" />
        <Hero
          tp="court"
          title="Court-Ordered Path"
          subtitle="You have been directed to participate in the SA CoParents process. Organize your perspective, identify your child's needs, and prepare information that may assist the professionals involved with your family."
          textClassName="hidden lg:block"
          pill={pill}
          pct={Math.round((doneCount / counted.length) * 100)}
        />
        <div className="grid grid-cols-1 lg:grid-cols-12 lg:grid-rows-[auto_1fr] gap-8 items-start">
          {/* Phones: requested list, picture, the rest, then chat. Desktop: list + rest on the left, picture + chat on the right. */}
          <div data-testid="court-top" className="order-1 lg:order-none lg:col-start-1 lg:col-span-7 lg:row-start-1 space-y-6">
            {signedIn && asked.length > 0 && doneCount === asked.length && <CourtCompleteCard count={asked.length} />}
            <CourtMenu statusFor={statusFor} requested={requested.keys} proKeys={requested.proKeys} proName={requested.proName} onToggle={requested.toggle} onOpen={openOption} />
          </div>
          <div className="contents lg:block lg:col-start-8 lg:col-span-5 lg:row-start-1 lg:row-span-2 lg:space-y-6">
            <div className="order-2">
              <CourtJourneyArt
                hints={hints}
                onToggleHints={() => setHints((h) => !h)}
                statusOf={statusOf}
                onAccept={() => setDialog({ type: "accept" })}
                onStep={(step) => setDialog({ type: "step", step })}
                onPillar={openPillar}
              />
            </div>
            <div className="order-4">
              <CourtChatInline chat={chat} fb={fb} onOpenStep4={openStep4} />
            </div>
          </div>
          <div className="order-3 lg:order-none lg:col-start-1 lg:col-span-7 lg:row-start-2 space-y-6">
            <AcceptCard verified={cc.verified} courtKey={courtKey} onAccept={() => setDialog({ type: "accept" })} />
            <CourtAgreeCard compare={compare} onOpen={() => openPillar(PILLARS[1])} />
            <CourtReports cc={cc} checklist={checklist} compare={compare} complete={asked.length > 0 && doneCount === asked.length} signedIn={signedIn} />
            <CourtMoreTools
              cc={cc}
              courtKey={courtKey}
              onCase={() => setDialog({ type: "accept" })}
              onBiff={onOpenBiffHistory}
              onPillar={openPillar}
              modules={modules}
              onOpenModule={onOpenModule}
              checklist={checklist}
            />
          </div>
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
            step4={step4}
            onClose={close}
            onOpenStep={openStep}
            onEnterCase={() => setDialog({ type: "accept" })}
          />
          <CourtCelebration open={celebrate} notice={compare.data?.intent_notice} onClose={compare.markCelebrated} onPdf={compare.downloadPdf} />
          <CourtChatPanel chat={chat} open={chatOpen} onOpenChange={setChatOpen} draft={chatDraft} fb={fb} onOpenStep4={openStep4} />
        </>
      )}
    </div>,
    document.body
  );
}

export default CourtOrderedView;
