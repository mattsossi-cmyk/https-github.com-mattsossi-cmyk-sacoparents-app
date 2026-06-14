import React, { useEffect, useState } from "react";
import { ScrollText, Check } from "lucide-react";

const STORAGE_KEY = "sac_legal_ack_v1";
const VERSION = "v1";

/**
 * Returns true if this device has already acknowledged the current version
 * of the disclaimer. Tolerates the absence of localStorage (e.g., SSR / mobile WebView).
 */
export function hasAcknowledgedLegal() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return false;
    const parsed = JSON.parse(raw);
    return parsed?.version === VERSION;
  } catch (_e) {
    return false;
  }
}

function recordAck() {
  try {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ version: VERSION, at: new Date().toISOString() })
    );
  } catch (_e) {
    /* private mode — best-effort only */
  }
}

/**
 * Legal acknowledgment modal that appears on first visit.
 * Disclaims:
 *   1. No legal services / attorney-client relationship
 *   2. No mental health services
 *   3. Tool is for conflict management only
 *
 * Blocks the rest of the page until the box is checked AND
 * the user clicks "I acknowledge — continue".
 */
export default function LegalAcknowledgment() {
  const [open, setOpen] = useState(false);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (!hasAcknowledgedLegal()) {
      setOpen(true);
      // Lock body scroll while the modal is open.
      const prev = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = prev;
      };
    }
  }, []);

  if (!open) return null;

  const accept = () => {
    if (!checked) return;
    recordAck();
    setOpen(false);
    document.body.style.overflow = "";
  };

  return (
    <div
      className="fixed inset-0 z-[1000] bg-[#1A1330]/70 backdrop-blur-sm grid place-items-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="legal-ack-title"
      data-testid="legal-acknowledgment-modal"
    >
      <div className="w-full max-w-lg bg-white rounded-3xl shadow-2xl overflow-hidden fade-up">
        <div className="bg-brand-gradient text-white px-6 py-5 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-white/15 grid place-items-center shrink-0">
            <ScrollText size={18} />
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-[0.2em] opacity-80">
              A quick note before we start
            </div>
            <h2
              id="legal-ack-title"
              className="font-sans font-bold text-xl leading-tight"
            >
              Just so we're on the same page
            </h2>
          </div>
        </div>

        <div className="px-6 py-6 space-y-4 max-h-[60vh] overflow-y-auto">
          <p className="text-[15px] text-[#1A1330] leading-relaxed">
            I acknowledge that this site is not intended to provide legal services
            and does not establish an attorney-client relationship.
          </p>
          <p className="text-[15px] text-[#1A1330] leading-relaxed">
            I understand that this site likewise does not provide mental health
            services and is simply here to provide me with conflict management
            tools to resolve my co-parenting relationship with my child's other
            parent.
          </p>
        </div>

        <div className="px-6 pb-6 space-y-5 border-t border-[#E5E0EE] pt-5">
          <label className="flex items-start gap-3 cursor-pointer select-none">
            <button
              type="button"
              onClick={() => setChecked((c) => !c)}
              role="checkbox"
              aria-checked={checked}
              className={`mt-0.5 w-5 h-5 rounded border-2 shrink-0 grid place-items-center transition ${
                checked
                  ? "bg-[#3D1A78] border-[#3D1A78]"
                  : "bg-white border-[#857E9C] hover:border-[#3D1A78]"
              }`}
              data-testid="legal-ack-checkbox"
            >
              {checked && <Check size={12} className="text-white" />}
            </button>
            <span
              onClick={() => setChecked((c) => !c)}
              className="text-sm text-[#1A1330] leading-relaxed"
            >
              I acknowledge and agree to the statement above.
            </span>
          </label>

          <button
            type="button"
            onClick={accept}
            disabled={!checked}
            className="btn-gradient w-full disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="legal-ack-continue-button"
          >
            I acknowledge — continue
          </button>
        </div>
      </div>
    </div>
  );
}
