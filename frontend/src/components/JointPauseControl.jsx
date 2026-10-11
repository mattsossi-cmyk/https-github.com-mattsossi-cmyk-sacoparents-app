import { useState } from "react";
import { toast } from "sonner";
import { PauseCircle, PlayCircle } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";

export const JointPauseControl = ({ rid, paused, onChange }) => {
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const go = async (next) => {
    setBusy(true);
    try {
      const { data } = await api.put(`/joint/reports/${rid}/joint-pause`, { paused: next, note });
      onChange(data.joint_paused);
      setOpen(false); setNote("");
      toast.success(next ? "Joint features paused for this case" : "Joint features resumed");
    } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  return (
    <div className="mb-6 rounded-lg border border-border bg-white p-4" data-testid="joint-pause-control">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm">
          <p className="font-semibold">Joint features: {paused ? <span className="text-amber-700">Paused</span> : <span className="text-green-700">Active</span>}</p>
          <p className="text-xs text-muted-foreground">{paused ? `Paused ${new Date(paused.at).toLocaleString()} by ${paused.by_name || "you"}${paused.note ? ` — ${paused.note}` : ""}. Parents see only a neutral "not available right now" message; no notification is sent.` : "Your decision only. Pausing blocks the joint assessment, joint report, shared PDF and joint invitations for this case; each parent can still work individually. Nothing is sent to either parent."}</p>
        </div>
        {!open && (paused
          ? <Button size="sm" variant="outline" onClick={() => setOpen(true)} data-testid="joint-resume-btn"><PlayCircle className="h-4 w-4" /> Resume joint features</Button>
          : <Button size="sm" variant="outline" onClick={() => setOpen(true)} data-testid="joint-pause-btn"><PauseCircle className="h-4 w-4" /> Pause joint features</Button>)}
      </div>
      {open && (
        <div className="mt-3 space-y-2" data-testid="joint-pause-confirm">
          <p className="text-sm">{paused ? "Resume joint features for this case?" : "Pause joint features for this case? This is recorded in the access log with your name and the time."}</p>
          <textarea value={note} onChange={(e) => setNote(e.target.value)} maxLength={2000} placeholder="Optional private note (professional-only, logged)" className="w-full rounded-md border border-border p-2 text-sm" data-testid="joint-pause-note" />
          <div className="flex gap-2">
            <Button size="sm" onClick={() => go(!paused)} disabled={busy} data-testid="joint-pause-confirm-btn">{paused ? "Confirm resume" : "Confirm pause"}</Button>
            <Button size="sm" variant="ghost" onClick={() => setOpen(false)} data-testid="joint-pause-cancel-btn">Cancel</Button>
          </div>
        </div>
      )}
    </div>
  );
};
