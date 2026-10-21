import React, { useState } from "react";
import { Route } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "../../context/AuthContext";
import { NEW_HOME_ON } from "../../lib/previewGate";
import { PathChoiceList } from "../journeyPath/PathChoiceList";

// Account setting: change the path chosen at sign-up.
export function JourneyPathSetting() {
  const { user, setJourneyPath } = useAuth();
  const [saving, setSaving] = useState(false);
  if (!NEW_HOME_ON || !user || user.is_guest) return null;

  const choose = async (path) => {
    if (path === user.journey_path) return;
    setSaving(true);
    try {
      await setJourneyPath(path);
      toast.success("Your path is updated.");
    } catch {
      toast.error("Couldn't change your path. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="mt-4 rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5" data-testid="account-journey-path">
      <div className="flex items-start gap-3 mb-3">
        <div className="shrink-0 h-9 w-9 rounded-full grid place-items-center bg-[#F5F1FB] text-[#3D1A78]" aria-hidden>
          <Route size={15} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#3D1A78]">Your path</div>
          <p className="text-xs text-[#4B4567] mt-1 leading-relaxed">This sets up your home screen. Your saved work stays put when you switch.</p>
        </div>
      </div>
      <PathChoiceList value={user.journey_path} onChoose={choose} disabled={saving} testid="account-path-choice" />
    </section>
  );
}
