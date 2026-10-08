import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { toast } from "sonner";

import { api } from "../../lib/api";
import { CourtAiPanel } from "./court/CourtAiPanel";
import { CourtChecklistCard } from "./court/CourtChecklistCard";
import { CourtCodeCard } from "./court/CourtCodeCard";
import { CourtHero } from "./court/CourtHero";
import { CourtPathCards } from "./court/CourtPathCards";
import { PageHeader, SafetyBanner, useLockScroll } from "./selfAssessment/SaChrome";

const hostOf = (url) => {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
};

// Full-page Court Ordered path. Rendered in a portal; hides while another overlay is open.
export function CourtOrderedView({ onBack, onQuickExit, courtKey, mediator, onVerify, modules, onOpenModule, onDownloadPdf, onOpenBiffHistory, onSupportChild, alignUrl, safetyFlag, signedIn, hidden = false }) {
  const [code, setCode] = useState(courtKey || "");
  const [verifiedCode, setVerifiedCode] = useState("");
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(null);
  useLockScroll(!hidden);
  useEffect(() => {
    if (courtKey) setCode((c) => c || courtKey);
  }, [courtKey]);

  const alignHost = hostOf(alignUrl);
  const doneCount = modules.filter((m) => m.status === "completed").length;
  const typed = code.trim();
  const verified = !!courtKey && (!typed || typed === verifiedCode || typed.toUpperCase() === courtKey.toUpperCase());

  const ensureVerified = async (kind) => {
    if (verified) return courtKey;
    if (!typed) {
      setStatus({ tone: "error", text: "Please enter your case number or invite code." });
      return null;
    }
    setBusy(kind);
    const res = await onVerify(typed);
    setBusy(null);
    if (res.error) {
      setStatus({ tone: "error", text: res.error });
      return null;
    }
    setVerifiedCode(typed);
    setStatus({ tone: "ok", text: `Verified. Case ${res.caseId} is linked to your portal.` });
    return res.caseId;
  };

  const verify = () =>
    verified ? setStatus({ tone: "ok", text: `Case ${courtKey} is verified and linked to your portal.` }) : ensureVerified("verify");

  const accept = async () => {
    const caseId = await ensureVerified("accept");
    if (!caseId) return;
    const next = modules.find((m) => m.status !== "completed");
    toast.success(`Court invite accepted for Case ${caseId}`, {
      description: next ? `Next step: ${next.letter}. ${next.title}` : "All three modules are complete. Your court-ready PDF is ready.",
    });
    if (next) onOpenModule(next);
  };

  const sync = async () => {
    const caseId = await ensureVerified("sync");
    if (!caseId) return;
    if (signedIn) {
      setBusy("sync");
      await api.put("/portal/state", { court_key: caseId }).catch(() => {});
      setBusy(null);
    }
    toast.success(`Case ${caseId} saved. Opening ${alignHost}…`);
    window.open(alignUrl, "_blank", "noopener,noreferrer");
  };

  const pdf = async () => {
    setBusy("pdf");
    await onDownloadPdf();
    setBusy(null);
  };

  return createPortal(
    <div id="court-page" data-testid="court-page" className={`fixed inset-0 z-50 overflow-y-auto ${hidden ? "hidden" : ""} bg-gradient-to-b from-[#F3EFFE] to-[#EBE5FA] text-slate-800 pb-12`}>
      <SafetyBanner tp="court" icon="fa-scale-balanced" label="Court Ordered Portal" />
      <div className="max-w-6xl mx-auto px-4 pt-6">
        <PageHeader tp="court" onBack={onBack} onQuickExit={onQuickExit} backLabel="Back to dashboard" tagline="Start with Alignment • End with Agreement" badgeLabel="Court Pathway Guide" tm />
        <CourtHero courtKey={courtKey} mediator={mediator} alignHost={alignHost} />
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          <div className="lg:col-span-7 space-y-4">
            <CourtPathCards modules={modules} doneCount={doneCount} onOpenModule={onOpenModule} onReports={pdf} onSupportChild={onSupportChild} pdfBusy={busy === "pdf"} />
            <CourtCodeCard
              code={code}
              onChange={(v) => {
                setCode(v);
                setStatus(null);
              }}
              onVerify={verify}
              onAccept={accept}
              status={status}
              busy={busy}
              verified={verified}
            />
            <CourtChecklistCard modules={modules} courtKey={courtKey} hidden={hidden} />
          </div>
          <div className="lg:col-span-5">
            <CourtAiPanel
              safetyFlag={safetyFlag}
              verified={!!courtKey}
              doneCount={doneCount}
              total={modules.length}
              busy={busy}
              onPdf={pdf}
              onBiff={onOpenBiffHistory}
              onSync={sync}
              alignHost={alignHost}
            />
          </div>
        </div>
        <p data-testid="court-footer" className="mt-12 text-center text-xs text-slate-500 font-medium">
          &copy; SA CoParents &bull; Court Ordered Pathway &bull; Powered by Emergent AI
        </p>
      </div>
    </div>,
    document.body
  );
}

export default CourtOrderedView;
