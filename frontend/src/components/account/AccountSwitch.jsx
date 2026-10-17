import React, { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import { api } from "../../lib/api";

// On/off setting card for the Account page. Hidden when the API says `eligible: false`.
export default function AccountSwitch({ url, Icon, title, body, onMsg, offMsg, testid }) {
  const [on, setOn] = useState(null);
  const [eligible, setEligible] = useState(true);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    api.get(url).then((r) => {
      setOn(!!r.data?.enabled);
      setEligible(r.data?.eligible !== false);
    }).catch(() => setOn(true));
  }, [url]);

  const toggle = async () => {
    const next = !on;
    setSaving(true);
    setOn(next);
    try {
      await api.put(url, { enabled: next });
      toast.success(next ? onMsg : offMsg);
    } catch {
      setOn(!next);
      toast.error("Couldn't update this setting right now.");
    } finally {
      setSaving(false);
    }
  };
  if (!eligible) return null;
  const busy = on === null || saving;
  return (
    <section className="mt-4">
      <div className="rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5" data-testid={`${testid}-panel`}>
        <div className="flex items-start gap-3">
          <div className="shrink-0 h-9 w-9 rounded-full grid place-items-center bg-[#F5F1FB] text-[#3D1A78]" aria-hidden>
            <Icon size={15} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-semibold text-[#1A1330] leading-tight">{title}</div>
            <p className="text-xs text-[#4B4567] mt-1 leading-relaxed">{body}</p>
            <div className="text-[11px] font-semibold mt-1.5 text-[#6E6787]" data-testid={`${testid}-state`}>
              {on === null ? "Checking…" : on ? "On" : "Off"}
            </div>
          </div>
          <button type="button" onClick={toggle} disabled={busy} role="switch" aria-checked={!!on} aria-label={title} data-testid={`${testid}-toggle`}
            className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#3D1A78] focus-visible:ring-offset-2 disabled:opacity-60 ${on ? "bg-[#3D1A78]" : "bg-[#D6CFE8]"}`}>
            <span className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${on ? "translate-x-[22px]" : "translate-x-[2px]"}`} aria-hidden />
            {busy && <Loader2 size={10} className="animate-spin absolute left-1/2 -translate-x-1/2 text-white" aria-hidden />}
          </button>
        </div>
      </div>
    </section>
  );
}
