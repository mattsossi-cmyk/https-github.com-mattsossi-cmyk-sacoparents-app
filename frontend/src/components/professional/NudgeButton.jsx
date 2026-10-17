import React, { useState } from "react";
import { HandHeart, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { api } from "../../lib/api";
import { fmtDay } from "./RequestedProgress";

// One-tap neutral reminder to one parent (while something requested is unfinished; once per 7 days) + nudge history.
export const NudgeButton = ({ caseRef, pid, nextAt, lastAt, count = 0, rows, testid }) => {
  const [busy, setBusy] = useState(false);
  const [hist, setHist] = useState({ next: nextAt, last: lastAt, count });
  if (!pid || !rows) return null;
  const history = hist.count > 0 && (
    <p className="text-[11px] text-[#6E6787]" data-testid={`${testid}-history`}>
      Last nudged {fmtDay(hist.last)} · {hist.count} {hist.count === 1 ? "nudge" : "nudges"} total
    </p>
  );
  const waiting = rows.some((r) => r.status !== "done");
  const send = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/professional/nudges", { ref: caseRef, pid });
      setHist((h) => ({ next: data.next_at, last: new Date().toISOString(), count: h.count + 1 }));
      toast.success("Gentle nudge sent.");
    } catch (err) {
      toast.error(String(err?.response?.data?.detail || "Couldn't send the nudge right now."));
    } finally {
      setBusy(false);
    }
  };
  let action = null;
  if (waiting && hist.next && new Date(hist.next) > new Date()) {
    action = <p className="text-[11px] text-[#6E6787]" data-testid={`${testid}-wait`}>You can nudge again {fmtDay(hist.next)}</p>;
  } else if (waiting) {
    action = (
      <button type="button" onClick={send} disabled={busy} data-testid={testid}
        className="inline-flex items-center gap-1.5 rounded-full border border-[#D6CFE8] bg-white text-[#3D1A78] hover:bg-[#F5F1FB] px-3 py-1 text-[11px] font-semibold transition-colors disabled:opacity-60">
        {busy ? <Loader2 size={11} className="animate-spin" /> : <HandHeart size={11} />} Send a gentle nudge
      </button>
    );
  }
  if (!action && !history) return null;
  return <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">{action}{history}</div>;
};
