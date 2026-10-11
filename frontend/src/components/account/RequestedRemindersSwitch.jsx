import React, { useEffect, useState } from "react";
import { BellRing, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { api } from "../../lib/api";

// Weekly Monday reminder about requested-but-unfinished assessments: on/off both ways (also undoes email unsubscribe).
export default function RequestedRemindersSwitch() {
  const [on, setOn] = useState(null);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    api.get("/court-path/reminders").then((r) => setOn(!!r.data?.enabled)).catch(() => setOn(true));
  }, []);

  const toggle = async () => {
    const next = !on;
    setSaving(true);
    setOn(next);
    try {
      await api.put("/court-path/reminders", { enabled: next });
      toast.success(next ? "Weekly reminders are on." : "Weekly reminders are off.");
    } catch {
      setOn(!next);
      toast.error("Couldn't update your reminder setting right now.");
    } finally {
      setSaving(false);
    }
  };
  const busy = on === null || saving;
  return (
    <div className="rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5" data-testid="requested-reminders-panel">
      <div className="flex items-start gap-3">
        <div className="shrink-0 h-9 w-9 rounded-full grid place-items-center bg-[#F5F1FB] text-[#3D1A78]" aria-hidden>
          <BellRing size={15} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold text-[#1A1330] leading-tight">Weekly reminders for requested assessments</div>
          <p className="text-xs text-[#4B4567] mt-1 leading-relaxed">
            A short Monday email if something your professional asked for is still waiting. It never names the assessment.
          </p>
          <div className="text-[11px] font-semibold mt-1.5 text-[#857E9C]" data-testid="requested-reminders-state">
            {on === null ? "Checking…" : on ? "On" : "Off"}
          </div>
        </div>
        <button type="button" onClick={toggle} disabled={busy} role="switch" aria-checked={!!on}
          aria-label="Weekly reminders for requested assessments" data-testid="requested-reminders-toggle"
          className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#3D1A78] focus-visible:ring-offset-2 disabled:opacity-60 ${on ? "bg-[#3D1A78]" : "bg-[#D6CFE8]"}`}>
          <span className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${on ? "translate-x-[22px]" : "translate-x-[2px]"}`} aria-hidden />
          {busy && <Loader2 size={10} className="animate-spin absolute left-1/2 -translate-x-1/2 text-white" aria-hidden />}
        </button>
      </div>
    </div>
  );
}
