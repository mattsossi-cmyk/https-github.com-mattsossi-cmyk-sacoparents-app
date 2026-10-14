import React, { useState } from "react";
import { HandHeart, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { api } from "../../lib/api";
import { fmtDay } from "./RequestedProgress";

// One-tap neutral reminder to one parent. Shown only while something requested is unfinished; once per 7 days.
export const NudgeButton = ({ caseRef, pid, nextAt, rows, testid }) => {
  const [busy, setBusy] = useState(false);
  const [next, setNext] = useState(nextAt);
  if (!pid || !rows || rows.every((r) => r.status === "done")) return null;
  if (next && new Date(next) > new Date()) {
    return <p className="text-[11px] text-[#857E9C] mt-2" data-testid={`${testid}-wait`}>Nudged · you can nudge again {fmtDay(next)}</p>;
  }
  const send = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/professional/nudges", { ref: caseRef, pid });
      setNext(data.next_at);
      toast.success("Gentle nudge sent.");
    } catch (err) {
      toast.error(String(err?.response?.data?.detail || "Couldn't send the nudge right now."));
    } finally {
      setBusy(false);
    }
  };
  return (
    <button type="button" onClick={send} disabled={busy} data-testid={testid}
      className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-[#D6CFE8] bg-white text-[#3D1A78] hover:bg-[#F5F1FB] px-3 py-1 text-[11px] font-semibold transition-colors disabled:opacity-60">
      {busy ? <Loader2 size={11} className="animate-spin" /> : <HandHeart size={11} />} Send a gentle nudge
    </button>
  );
};
