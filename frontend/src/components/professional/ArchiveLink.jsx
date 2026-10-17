import React, { useState } from "react";
import { Archive, ArchiveRestore, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { api } from "../../lib/api";

// Tidies My cases only: parents, reminders, completion emails and PDFs carry on as before.
export const ArchiveLink = ({ caseRef, archived, onChanged, testid }) => {
  const [busy, setBusy] = useState(false);
  const flip = async () => {
    setBusy(true);
    try {
      const { data } = await api.put("/professional/archive", { ref: caseRef, archived: !archived });
      toast.success(archived ? `${caseRef} restored.` : `${caseRef} archived. Parents won't notice a thing.`);
      onChanged(data.archived_at);
    } catch (err) {
      toast.error(String(err?.response?.data?.detail || "Couldn't update this right now."));
    } finally {
      setBusy(false);
    }
  };
  const Icon = busy ? Loader2 : archived ? ArchiveRestore : Archive;
  return (
    <button type="button" onClick={flip} disabled={busy} data-testid={testid}
      className="inline-flex items-center gap-1 text-[0.6875rem] font-semibold text-[#4B4567] hover:text-[#3D1A78] hover:underline disabled:opacity-60">
      <Icon size={11} className={busy ? "animate-spin" : ""} /> {archived ? "Restore" : "Archive"}
    </button>
  );
};
