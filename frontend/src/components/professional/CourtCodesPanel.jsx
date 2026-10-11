import React, { useEffect, useState } from "react";
import { KeyRound, Loader2, Plus, Trash2, X } from "lucide-react";
import { toast } from "sonner";

import { api } from "../../lib/api";
import { logError } from "../../lib/logger";
import { CourtCodeForm } from "./CourtCodeForm";
import { ProgressPdfButton } from "./ProgressPdfButton";
import { RequestedProgress, fmtDay } from "./RequestedProgress";

// "My cases": court codes this professional created, with status-only progress per parent who entered the code.
export const CourtCodesPanel = () => {
  const [codes, setCodes] = useState(null);
  const [open, setOpen] = useState(false);
  const load = () =>
    api.get("/professional/court-codes").then((r) => setCodes(r.data?.codes || [])).catch((err) => {
      logError("court codes load failed:", err);
      setCodes([]);
    });
  useEffect(() => { load(); }, []);

  return (
    <section className="rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5 mb-4" data-testid="court-codes-panel">
      <div className="flex items-start justify-between gap-3 flex-wrap mb-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] inline-flex items-center gap-2">
            <KeyRound size={12} /> Court codes
          </div>
          <p className="text-sm text-[#4B4567] mt-1 max-w-xl leading-relaxed">
            Give a parent a code and the assessments you pick are ticked for them on their Court page.
            You&rsquo;ll see only Done, In progress or Not started, never their answers.
          </p>
        </div>
        <button type="button" onClick={() => setOpen((o) => !o)} data-testid="court-code-toggle"
          className="inline-flex items-center gap-1.5 rounded-full border border-[#3D1A78] text-[#3D1A78] hover:bg-[#F5F1FB] px-3 py-1.5 text-xs font-semibold transition-colors">
          {open ? <X size={12} /> : <Plus size={12} />} {open ? "Close" : "Create a court code"}
        </button>
      </div>
      {open && <div className="mb-3"><CourtCodeForm onCreated={load} /></div>}
      {codes === null ? (
        <p className="text-xs text-[#857E9C]" data-testid="court-codes-loading"><Loader2 size={12} className="animate-spin inline mr-1" /> Loading codes…</p>
      ) : codes.length === 0 ? (
        <p className="text-xs text-[#857E9C]" data-testid="court-codes-empty">No court codes yet.</p>
      ) : (
        <ul className="space-y-2.5" data-testid="court-codes-list">
          {codes.map((c) => <CourtCodeItem key={c.case_id} c={c} onChanged={load} />)}
        </ul>
      )}
    </section>
  );
};

const stateOf = (c) => (c.revoked_at ? "Revoked" : c.expires_at && new Date(c.expires_at) < new Date() ? "Expired" : "Active");

const CourtCodeItem = ({ c, onChanged }) => {
  const [busy, setBusy] = useState(false);
  const state = stateOf(c);
  const revoke = async () => {
    if (!window.confirm(`Revoke ${c.case_id}? Parents who haven't entered the code yet won't be able to use it.`)) return;
    setBusy(true);
    try {
      await api.post(`/professional/court-codes/${c.case_id}/revoke`);
      toast.success(`${c.case_id} revoked`);
      onChanged();
    } catch (err) {
      toast.error(String(err?.response?.data?.detail || "Revoke failed"));
    } finally {
      setBusy(false);
    }
  };
  return (
    <li className="rounded-xl border border-[#E5E0EE] bg-[#FAF8FD] p-3" data-testid={`court-code-row-${c.case_id}`}>
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <div className="min-w-0 text-xs text-[#4B4567]">
          <span className="font-mono text-sm font-semibold text-[#1A1330] mr-2">{c.case_id}</span>
          <span className={`font-bold ${state === "Active" ? "text-[#1F5C3B]" : "text-[#B02A2A]"}`} data-testid={`court-code-state-${c.case_id}`}>{state}</span>
          {c.label ? ` · ${c.label}` : ""}
          {c.expires_at && state === "Active" ? ` · until ${fmtDay(c.expires_at)}` : ""}
        </div>
        <div className="flex items-center gap-3">
          <ProgressPdfButton path={`/professional/court-codes/${c.case_id}/progress.pdf`} caseId={c.case_id} testid={`court-code-progress-pdf-${c.case_id}`} />
          {state === "Active" && (
            <button type="button" onClick={revoke} disabled={busy} data-testid={`court-code-revoke-${c.case_id}`}
              className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#B02A2A] hover:underline disabled:opacity-60">
              {busy ? <Loader2 size={11} className="animate-spin" /> : <Trash2 size={11} />} Revoke
            </button>
          )}
        </div>
      </div>
      {c.parents.length === 0 ? (
        <p className="text-[11px] text-[#857E9C] mt-2" data-testid={`court-code-waiting-${c.case_id}`}>No parent has entered this code yet.</p>
      ) : (
        <div className="mt-1 grid gap-2 sm:grid-cols-2">
          {c.parents.map((p, i) => (
            <div key={i} className="rounded-lg border border-[#E5E0EE] bg-white p-2.5" data-testid={`court-code-parent-${c.case_id}-${i}`}>
              <div className="text-sm text-[#1A1330] truncate">{p.name}</div>
              <RequestedProgress rows={p.assessments} testid={`court-code-progress-${c.case_id}-${i}`} />
            </div>
          ))}
        </div>
      )}
    </li>
  );
};
