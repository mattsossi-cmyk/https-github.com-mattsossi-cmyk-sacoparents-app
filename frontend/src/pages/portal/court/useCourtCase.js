import { useEffect, useState } from "react";
import { toast } from "sonner";

import { api } from "../../../lib/api";

const hostOf = (url) => {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
};

// Court case code + legal name, verification, and the case-related actions (save, sync, PDF).
export function useCourtCase({ courtKey, savedName, onVerify, signedIn, alignUrl, onDownloadPdf }) {
  const [code, setCodeRaw] = useState(courtKey || "");
  const [name, setName] = useState("");
  const [verifiedCode, setVerifiedCode] = useState("");
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(null);
  useEffect(() => {
    if (courtKey) setCodeRaw((c) => c || courtKey);
  }, [courtKey]);
  useEffect(() => {
    if (savedName) setName((n) => n || savedName);
  }, [savedName]);

  const alignHost = hostOf(alignUrl);
  const typed = code.trim();
  const verified = !!courtKey && (!typed || typed === verifiedCode || typed.toUpperCase() === courtKey.toUpperCase());
  const setCode = (v) => {
    setCodeRaw(v);
    setStatus(null);
  };
  const persist = (patch) => (signedIn ? api.put("/portal/state", patch).catch(() => {}) : Promise.resolve());

  const ensureVerified = async (kind) => {
    if (verified) return courtKey;
    if (!typed) {
      setStatus({ tone: "error", text: "Please enter your court reference number or invite code." });
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

  const accept = async () => {
    const legal = name.trim().replace(/\s+/g, " ");
    if (legal.length < 2) {
      setStatus({ tone: "error", text: "Please enter your full legal name." });
      return null;
    }
    const caseId = await ensureVerified("accept");
    if (!caseId) return null;
    setBusy("accept");
    await persist({ court_key: caseId, court_legal_name: legal });
    setBusy(null);
    return caseId;
  };

  const sync = async () => {
    const caseId = await ensureVerified("sync");
    if (!caseId) return false;
    setBusy("sync");
    await persist({ court_key: caseId });
    setBusy(null);
    toast.success(`Case ${caseId} saved. Opening ${alignHost}…`);
    window.open(alignUrl, "_blank", "noopener,noreferrer");
    return true;
  };

  const pdf = async () => {
    setBusy("pdf");
    await onDownloadPdf();
    setBusy(null);
  };

  return { code, setCode, name, setName, status, setStatus, busy, verified, alignHost, accept, sync, pdf };
}
