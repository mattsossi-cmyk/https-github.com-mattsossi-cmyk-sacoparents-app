import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Compass, X, ArrowRight, ShieldCheck, Baby, Scale } from "lucide-react";

const STORAGE_KEY = "sac_recommended_focus_v1";

/**
 * PickerChoicePill — the small "you chose X" reminder pill that appears on
 * the dashboard header for users who came in through the landing situation
 * picker. Reads the localStorage focus written by `enterWithFocus` on the
 * landing page (mediation / safety / special-needs).
 *
 * Purpose: close the loop between the visitor's marketing-side choice and
 * the returning user's in-app experience. On re-visit, they see "You said
 * X was your situation — start [the relevant assessment]" instead of a
 * generic dashboard that has no memory of why they came.
 *
 * Renders nothing if the storage key is absent (returning users who never
 * used the picker) or if the user has dismissed it.
 */
const FOCUS_META = {
  mediation: {
    label: "Preparing for mediation",
    icon: <Scale size={14} />,
    href: "/prep",
    ctaLabel: "Continue your Readiness Assessment",
    accent: "text-[#3D1A78]",
    ring: "ring-[#3D1A78]/20",
    chip: "bg-[#EFE9F9]",
  },
  safety: {
    label: "Safety-first path",
    icon: <ShieldCheck size={14} />,
    href: "/safety-assessment",
    ctaLabel: "Continue the Safety Assessment",
    accent: "text-[#B85B00]",
    ring: "ring-[#B85B00]/20",
    chip: "bg-[#FFEDDE]",
  },
};

function readFocus() {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function clearFocus() {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* best-effort */
  }
}

export default function PickerChoicePill() {
  const [focus, setFocus] = useState(readFocus);

  const meta = focus ? FOCUS_META[focus] : null;
  if (!meta) return null;

  const dismiss = () => {
    clearFocus();
    setFocus(null);
  };

  return (
    <div
      className={`mb-4 rounded-2xl bg-white ring-1 ${meta.ring} border border-[#E5E0EE] p-3 sm:p-4 flex items-center gap-3`}
      data-testid="picker-choice-pill"
    >
      <div
        className={`shrink-0 w-9 h-9 rounded-full flex items-center justify-center ${meta.chip} ${meta.accent}`}
      >
        {meta.icon}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[11px] uppercase tracking-[0.14em] font-bold text-[#857E9C] flex items-center gap-1">
          <Compass size={11} /> Your chosen path
        </div>
        <div className={`text-sm font-semibold ${meta.accent} truncate`} data-testid="picker-choice-pill-label">
          {meta.label}
        </div>
      </div>
      <Link
        to={meta.href}
        className={`shrink-0 inline-flex items-center gap-1.5 text-xs sm:text-sm font-semibold ${meta.accent} hover:underline underline-offset-2`}
        data-testid="picker-choice-pill-cta"
      >
        {meta.ctaLabel}
        <ArrowRight size={13} />
      </Link>
      <button
        type="button"
        onClick={dismiss}
        aria-label="Dismiss"
        className="shrink-0 text-[#857E9C] hover:text-[#3D1A78] p-1 rounded-full hover:bg-[#F5F2FA]"
        data-testid="picker-choice-pill-dismiss"
      >
        <X size={14} />
      </button>
    </div>
  );
}
