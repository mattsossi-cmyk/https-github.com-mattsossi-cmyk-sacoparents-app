/**
 * DeviceSafetyBanner — Warns the parent about device-monitoring risks
 * before they engage with a family-violence screen, plus a one-click
 * "quick exit" that redirects to a neutral URL and wipes the current
 * history entry so a Back tap does not return to the screen.
 *
 * This is a survivor-protection guardrail per DV-advocate best practice.
 * It appears at the very top of the safety screen intro (step 0).
 */
import { useState } from "react";
import { AlertCircle, X, ExternalLink } from "lucide-react";

const QUICK_EXIT_URL = "https://weather.com";

function quickExit() {
  try {
    // Replace history so a Back tap can't return here.
    window.history.replaceState({}, "", QUICK_EXIT_URL);
  } catch { /* private mode / non-browser */ }
  // Redirect. `replace` prevents this page from remaining in history.
  window.location.replace(QUICK_EXIT_URL);
}

export default function DeviceSafetyBanner({ testId = "device-safety-banner" }) {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;
  return (
    <div
      className="rounded-2xl border-2 border-[#9A3A23] bg-[#FFF4EE] p-4 sm:p-5 mb-5"
      data-testid={testId}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2">
          <AlertCircle size={16} className="shrink-0 mt-0.5 text-[#9A3A23]" />
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-[#9A3A23] mb-1">
              Before you begin · your safety on this device
            </div>
            <p className="text-sm text-[#1A1330] leading-relaxed">
              If the other parent has access to this device, your browser,
              a shared email account, or a shared cloud drive, they may be
              able to see anything you enter here. Consider using a private
              browser window, a device they cannot access, or a trusted
              friend's device. Never leave downloaded PDFs on a shared
              drive or in a shared email inbox.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setDismissed(true)}
          data-testid={`${testId}-dismiss`}
          aria-label="Dismiss safety notice"
          className="shrink-0 w-8 h-8 rounded-full grid place-items-center bg-white/70 hover:bg-white text-[#9A3A23]"
        >
          <X size={14} />
        </button>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={quickExit}
          data-testid={`${testId}-quick-exit`}
          className="inline-flex items-center gap-2 rounded-full bg-[#9A3A23] text-white px-4 py-2 text-xs font-bold hover:bg-[#7e2e1c]"
        >
          <ExternalLink size={12} /> Quick exit
        </button>
        <span className="inline-flex items-center text-[11px] text-[#4B4567] italic">
          Redirects to weather.com and removes this page from history.
        </span>
      </div>
    </div>
  );
}
