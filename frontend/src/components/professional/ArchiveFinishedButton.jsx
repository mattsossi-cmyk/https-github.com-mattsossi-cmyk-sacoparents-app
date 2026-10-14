import React, { useState } from "react";
import { Archive, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { api } from "../../lib/api";

const LABEL = {
  codes: "court codes that are finished, revoked or expired",
  cases: "joint cases that are complete, cancelled or expired",
};

// One-tap tidy-up with a confirm first and an Undo in the toast. Parents notice nothing.
export const ArchiveFinishedButton = ({ kind, count, onDone, testid }) => {
  const [busy, setBusy] = useState(false);
  if (!count) return null;
  const undo = async (refs) => {
    try {
      await api.put("/professional/archive/bulk", { refs, archived: false });
      toast.success("Restored.");
      onDone();
    } catch {
      toast.error("Couldn't undo right now. You can restore them one by one.");
    }
  };
  const run = async () => {
    if (!window.confirm(`Archive ${count} ${LABEL[kind]}? Parents won't notice, and you can restore them anytime.`)) return;
    setBusy(true);
    try {
      const { data } = await api.post("/professional/archive/finished", { kind });
      const refs = data.refs || [];
      onDone();
      toast.success(`Archived ${refs.length}.`, { action: refs.length ? { label: "Undo", onClick: () => undo(refs) } : undefined, duration: 8000 });
    } catch (err) {
      toast.error(String(err?.response?.data?.detail || "Couldn't archive right now."));
    } finally {
      setBusy(false);
    }
  };
  return (
    <button type="button" onClick={run} disabled={busy} data-testid={testid}
      className="inline-flex items-center gap-1.5 rounded-full border border-[#D6CFE8] bg-white text-[#4B4567] hover:border-[#3D1A78] hover:text-[#3D1A78] px-3 py-1.5 text-xs font-semibold transition-colors disabled:opacity-60">
      {busy ? <Loader2 size={12} className="animate-spin" /> : <Archive size={12} />} Archive finished ({count})
    </button>
  );
};
