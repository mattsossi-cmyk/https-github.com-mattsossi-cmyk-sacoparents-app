import React, { useState } from "react";
import { toast } from "sonner";

import { useAuth } from "../../context/AuthContext";
import { quickExitAction } from "../../pages/portal/JourneyShell";
import { PathChoiceList } from "./PathChoiceList";

// One-time path question for signed-in parents who haven't picked one yet.
export function PathPicker() {
  const { user, setJourneyPath } = useAuth();
  const [saving, setSaving] = useState(false);
  if (!user || user.is_guest || !user.consent_current || user.journey_path) return null;

  const choose = async (path) => {
    setSaving(true);
    try {
      await setJourneyPath(path);
    } catch {
      toast.error("Couldn't save your path. Please try again.");
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[900] bg-[#1A1330]/70 backdrop-blur-sm grid place-items-center p-4" data-testid="path-picker">
      <section role="dialog" aria-modal="true" aria-labelledby="path-picker-title" className="w-full max-w-md rounded-3xl bg-white p-5 shadow-2xl">
        <div className="flex justify-end">
          <button type="button" onClick={quickExitAction} data-testid="path-picker-quick-exit"
                  className="min-h-[40px] px-4 rounded-full text-xs font-bold bg-rose-600 hover:bg-rose-700 text-white transition-colors">
            <i className="fa-solid fa-bolt mr-1" aria-hidden="true"></i>Quick Exit
          </button>
        </div>
        <h2 id="path-picker-title" className="text-xl font-bold text-slate-900 mt-2">Which path fits you?</h2>
        <p className="text-xs text-slate-600 mt-1 mb-4">Pick one to set up your home screen. You can change it any time in Account.</p>
        <PathChoiceList value={null} onChoose={choose} disabled={saving} testid="path-picker-choice" />
      </section>
    </div>
  );
}
