import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../../context/AuthContext";
import { api } from "../../lib/api";
import { downloadPdf } from "../../lib/pdf";
import { useCalmMode } from "../../lib/useCalmMode";
import { useCheckinLink } from "../../lib/useCheckinLink";
import { ChildNeedsView } from "../portal/ChildNeedsView";
import { useChildNeeds } from "../portal/childNeeds/useChildNeeds";
import { CoparentingAssessmentView } from "../portal/coparenting/CoparentingAssessmentView";
import { ALIGN_SITE_URL, quickExitAction } from "../portal/JourneyShell";
import { SelfAssessmentView } from "../portal/SelfAssessmentView";
import { useCoparentingDone } from "../portal/selfJourney/useCoparentingDone";
import { useSelfAssessmentHistory } from "../portal/selfAssessment/useSelfAssessmentHistory";
import SelfJourney, { STEPS } from "./SelfJourney";

// Lets the step panels open the app's existing assessments without remounting on every render.
const Ctx = createContext(null);

function OpenButton({ onClick, testid, children }) {
  return (
    <button type="button" className="sj-open-btn" style={{ width: "100%" }} onClick={onClick} data-testid={testid}>
      {children}
    </button>
  );
}

function SelfAssessmentPanel() {
  const { sa, open } = useContext(Ctx);
  const last = sa.latest?.completed_at;
  return (
    <>
      {last && (
        <div className="sj-notice" data-testid="sj-sa-last">
          Your last Self-Assessment: {new Date(last).toLocaleDateString()}. Take it again anytime to see how you&apos;ve grown.
        </div>
      )}
      <section className="sj-card">
        <h2 className="sj-card-title">Your Self-Assessment</h2>
        <p className="sj-small" style={{ margin: "0 0 10px" }}>
          Reflect on your strengths, growth areas and goals as a parent. Only you see your answers.
        </p>
        <OpenButton onClick={() => open({ kind: "self" })} testid="sj-open-self-assessment">
          {last ? "Open my Self-Assessment" : "Start my Self-Assessment"}
        </OpenButton>
      </section>
      <p className="sj-small">This is a personal reflection, not a diagnosis.</p>
    </>
  );
}

// National lines plus San Antonio / Bexar County family violence resources (same as the Safety page).
const SAFETY_RESOURCES = [
  { label: "In immediate danger", detail: "Call 911", href: "tel:911" },
  { label: "National Domestic Violence Hotline", detail: "1-800-799-7233 or text START to 88788", href: "tel:18007997233" },
  { label: "Family Violence Prevention Services (San Antonio, 24/7)", detail: "210-733-8810", href: "tel:2107338810" },
  { label: "Bexar County Family Justice Center", detail: "210-631-0100", href: "tel:2106310100" },
  { label: "PEACE Initiative (San Antonio)", detail: "210-533-2729", href: "tel:2105332729" },
];

function CoParentingPanel({ concern }) {
  const { open } = useContext(Ctx);
  return (
    <>
      <h2 className="sj-card-title">Co-Parenting Assessment</h2>
      <p className="sj-small" style={{ margin: "0 0 10px" }}>
        Look at communication, decisions and boundaries between your two homes. Only you see your answers.
      </p>
      <OpenButton onClick={() => open({ kind: "coparenting", concern })} testid="sj-open-coparenting">
        Open the Co-Parenting Assessment
      </OpenButton>
    </>
  );
}

const needsPanel = (key, label) =>
  function NeedsPanel() {
    const { open } = useContext(Ctx);
    return <OpenButton onClick={() => open({ kind: "needs", key })} testid={`sj-open-needs-${key}`}>Open the {label} form</OpenButton>;
  };

function DevelopmentalPanel() {
  return (
    <Link to="/special-needs-v2" className="sj-open-btn" style={{ width: "100%" }} data-testid="sj-open-special-needs">
      Open Special Needs
    </Link>
  );
}

const CHILD_PANELS = {
  educational: needsPanel("educational", "educational"),
  medical: needsPanel("medical", "medical"),
  emotional: needsPanel("psychological", "emotional & psychological"),
  developmental: DevelopmentalPanel,
};

function Overlays({ overlay, close, setOverlay, sa, childNeeds, user, parentName }) {
  const navigate = useNavigate();
  if (overlay?.kind === "self") {
    return (
      <SelfAssessmentView
        onClose={close}
        parentName={parentName}
        userId={user.user_id}
        history={sa.history}
        startNew={!!overlay.retake}
        compareWithLast={!!overlay.retake}
        onCompleted={sa.addEntry}
        onEntryUpdate={sa.updateEntry}
        onGoalReached={sa.markReached}
        onQuickExit={quickExitAction}
        onOpenBiffCoach={() => navigate("/dashboard?open=comm-builder")}
        safetyFlag={false}
      />
    );
  }
  if (overlay?.kind === "coparenting") {
    return (
      <CoparentingAssessmentView
        userId={user.user_id}
        onClose={close}
        onQuickExit={quickExitAction}
        onOpenSelfAssessment={() => setOverlay({ kind: "self" })}
        safetyFlag={!!overlay.concern}
      />
    );
  }
  if (overlay?.kind === "needs") {
    // ChildNeedsView (JourneyPage) portals itself as a fixed full-screen page; wrapping it in another
    // fixed z-50 overlay hid it behind a blank screen.
    return (
      <div data-testid="sj-needs-overlay">
        <ChildNeedsView onBack={close} onQuickExit={quickExitAction} safetyFlag={false} needs={childNeeds}
          userId={user.user_id} parentName={parentName} initialOpenKey={overlay.key} />
      </div>
    );
  }
  return null;
}

async function approveFoundation(draft) {
  const { data } = await api.get("/foundation-builder/me");
  await api.put("/foundation-builder/me", { fields: { ...(data?.fields || {}), statement: draft } });
}

// /self-journey and /self-journey/:step — the guided Self Journey (Step 1 of the Journey page).
export default function SelfJourneyPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const sa = useSelfAssessmentHistory(user?.user_id);
  const childNeeds = useChildNeeds(user?.user_id);
  const checkinHref = useCheckinLink(ALIGN_SITE_URL);
  const { calm } = useCalmMode();
  const [progress, setProgress] = useState(undefined);
  const [overlay, setOverlay] = useState(null);
  const coparentingDone = useCoparentingDone(user?.user_id, overlay?.kind === "coparenting");
  const sessionRef = useRef(null);
  const parentName = user?.name ? user.name.split(" ")[0] : null;

  useEffect(() => {
    api.get("/self-journey/me").then((r) => setProgress(r.data?.progress || null), () => setProgress(null));
  }, []);

  // The parent's own safety pick goes along so the guide never encourages direct contact on "concern".
  const ask = async (slug, message, _history, safetyStatus = "none") => {
    const section = STEPS.find((s) => s.slug === slug)?.short;
    const { data } = await api.post("/journey-guide/self-journey/chat", {
      message, session_id: sessionRef.current, section,
      safety_status: safetyStatus, safety_flagged: safetyStatus === "concern",
    });
    sessionRef.current = data.session_id;
    return data.reply;
  };

  // Save the latest answers first so the PDF matches the screen.
  const downloadJourneyPdf = async (p) => {
    await api.put("/self-journey/me", p);
    await downloadPdf("/self-journey/pdf", { filename: "SA_CoParents_Self_Journey.pdf", testid: "sj-download-pdf" });
  };

  if (progress === undefined) {
    return <div className="sj" data-testid="self-journey-loading" style={{ padding: 24 }}>Loading your Self Journey…</div>;
  }

  return (
    <Ctx.Provider value={{ sa, open: setOverlay }}>
      <SelfJourney
        initialProgress={progress}
        onSave={(p) => api.put("/self-journey/me", p)}
        checkinHref={checkinHref}
        SelfAssessmentPanel={SelfAssessmentPanel}
        selfAssessmentCount={sa.history.length}
        CoParentingPanel={CoParentingPanel}
        ChildNeedsPanels={CHILD_PANELS}
        onApproveFoundation={approveFoundation}
        onAskAssistant={ask}
        safetyResources={SAFETY_RESOURCES}
        onDownloadPdf={downloadJourneyPdf}
        onShare={() => navigate("/summary")}
        onQuickExit={quickExitAction}
        logoSrc="/images/guide-avatar.webp"
        calm={calm}
        coparentingDone={coparentingDone}
        lastSelfAssessmentAt={sa.latest?.completed_at || null}
        awardsPaused={!!overlay}
        awardLogoSrc="/images/award-logo.webp"
        onDownloadCertificate={() =>
          downloadPdf("/self-journey/certificate", { filename: "SA_CoParents_Self_Journey_Certificate.pdf", testid: "sj-certificate" })
        }
        onRetakeSelfAssessment={() => setOverlay({ kind: "self", retake: true })}
        checkInDays={0}
      />
      <Overlays overlay={overlay} close={() => setOverlay(null)} setOverlay={setOverlay} sa={sa}
        childNeeds={childNeeds} user={user} parentName={parentName} />
    </Ctx.Provider>
  );
}
