import React, { useState } from "react";
import { Leaf } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "../../context/AuthContext";
import { useCalmMode } from "../../lib/useCalmMode";
import { Switch } from "../ui/switch";

// Account: Calm Mode turns off confetti and moving effects on the home screen.
export function CalmModeSetting() {
  const { user, setCalmMode } = useAuth();
  const { calm, phone } = useCalmMode();
  const [saving, setSaving] = useState(false);
  if (!user) return null;

  const toggle = async (on) => {
    setSaving(true);
    try {
      await setCalmMode(on);
      toast.success(on ? "Calm Mode is on." : "Calm Mode is off.");
    } catch {
      toast.error("Couldn't change Calm Mode. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="mt-4 rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5" data-testid="account-calm-mode">
      <div className="flex items-start gap-3">
        <div className="shrink-0 h-9 w-9 rounded-full grid place-items-center bg-[#F5F1FB] text-[#3D1A78]" aria-hidden>
          <Leaf size={15} />
        </div>
        <div className="min-w-0 flex-1">
          <label htmlFor="calm-mode-switch" className="text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">
            Calm Mode
          </label>
          <p className="text-xs text-[#4B4567] mt-1 leading-relaxed">
            A quieter home screen: no confetti, pulsing glows, slide-ins or fades.
          </p>
          {phone && (
            <p data-testid="calm-mode-device-note" className="text-xs text-[#4B4567] mt-1 leading-relaxed">
              On because your device is set to reduce motion. You can change that in your device settings.
            </p>
          )}
        </div>
        <Switch id="calm-mode-switch" data-testid="calm-mode-switch" checked={calm} disabled={saving || phone}
                onCheckedChange={toggle} className="mt-0.5 shrink-0" />
      </div>
    </section>
  );
}
