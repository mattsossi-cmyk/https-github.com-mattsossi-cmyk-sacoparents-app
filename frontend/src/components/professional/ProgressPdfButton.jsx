import React, { useState } from "react";
import { BarChart3, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { api } from "../../lib/api";

// Status-only progress PDF (Done / In progress / Not started) for the professional's case file.
// `hasNotes` adds an off-by-default "Include my private case notes" tick box (joint cases).
export const ProgressPdfButton = ({ path, caseId, testid, hasNotes = false }) => {
  const [busy, setBusy] = useState(false);
  const [withNotes, setWithNotes] = useState(false);
  const download = async () => {
    setBusy(true);
    try {
      const res = await api.get(path, { responseType: "blob", params: hasNotes && withNotes ? { include_notes: true } : undefined });
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `SA_CoParents_Progress_${caseId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      toast.success("Progress PDF ready.");
    } catch {
      toast.error("Couldn't build the progress PDF. Please try again.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <span className="inline-flex items-center gap-2 flex-wrap">
      <button type="button" onClick={download} disabled={busy} data-testid={testid}
        className="inline-flex items-center gap-1.5 rounded-full border border-[#D6CFE8] text-[#3D1A78] hover:bg-[#F5F1FB] px-3 py-1.5 text-xs font-semibold transition-colors disabled:opacity-60">
        {busy ? <Loader2 size={12} className="animate-spin" /> : <BarChart3 size={12} />} Progress PDF
      </button>
      {hasNotes && (
        <label className="inline-flex items-center gap-1.5 text-[11px] text-[#4B4567] cursor-pointer">
          <input type="checkbox" checked={withNotes} onChange={(e) => setWithNotes(e.target.checked)} className="accent-[#3D1A78]" data-testid={`${testid}-include-notes`} />
          Include my private case notes
        </label>
      )}
    </span>
  );
};
