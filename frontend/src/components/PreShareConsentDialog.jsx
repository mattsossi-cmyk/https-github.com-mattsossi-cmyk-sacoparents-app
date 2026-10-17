/**
 * PreShareConsentDialog — the "YOU CONTROL THIS REPORT" gate.
 *
 * Rendered once at the app root via `<PreShareConsentHost />`. Any share
 * flow that touches PHI or Safety-Lens data can request consent by
 * calling `requestPreShareConsent(shareLabel)` — the promise resolves
 * `true` when the parent ticks the checkbox and taps "I understand,
 * continue", `false` on Cancel or Esc.
 *
 * Deliberately NOT cached in localStorage: the whole point is to make
 * the parent read the six bullets *every* time they share. Two clicks
 * is not friction, it's a legal-strength consent gate.
 */
import { useEffect, useState } from "react";
import { X, ShieldAlert } from "lucide-react";

// -- promise-bridge -----------------------------------------------------
// The host component subscribes to `_show`, and callers invoke it via
// `requestPreShareConsent`. This decouples share-flow call sites from
// having to know anything about mounting or state.

let _show = null;

/**
 * Show the pre-share consent modal.
 * @param {string} shareLabel  Short human-readable label of what is about
 *                             to leave the platform ("Joint Report",
 *                             "Co-Sign QR link", …). Rendered near the
 *                             top of the modal.
 * @returns {Promise<boolean>} true = confirmed, false = cancelled.
 */
export function requestPreShareConsent(shareLabel = "this report") {
  if (typeof _show !== "function") {
    // Host not mounted (e.g. SSR or unit test). Fail closed so we never
    // silently skip the consent gate — treat it as a cancel.
    return Promise.resolve(false);
  }
  return _show(shareLabel);
}

const BULLETS = [
  { id: "answers-stay-private",   text: "Your underlying assessment answers remain private unless specifically included in this report." },
  { id: "only-selected-report",   text: "Only the report you selected will be shared." },
  { id: "no-account-wide-access", text: "Sharing this report does not automatically share your other assessments, journal entries, AI conversations, or raw answers." },
  { id: "recipient-controls",     text: "Anyone receiving a report may save, print, or forward it." },
  { id: "revoke-limit",           text: "Revoking a link prevents future access through that link, but cannot retrieve copies already downloaded." },
  { id: "no-privilege-guarantee", text: "SA CoParents cannot guarantee that information voluntarily shared with an attorney, mediator, therapist, co-parent, or other person will remain legally confidential or privileged." },
];

export function PreShareConsentHost() {
  const [state, setState] = useState({ open: false, label: "this report" });
  const [checked, setChecked] = useState(false);
  const [resolver, setResolver] = useState(() => () => {});

  const close = (ok) => {
    setState((prev) => ({ open: false, label: prev.label }));
    resolver(ok);
  };

  useEffect(() => {
    _show = (label) => {
      setChecked(false);
      setState({ open: true, label });
      return new Promise((resolve) => {
        setResolver(() => resolve);
      });
    };
    return () => { _show = null; };
  }, []);

  useEffect(() => {
    if (!state.open) return;
    const onKey = (e) => {
      if (e.key === "Escape") close(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [state.open]);

  if (!state.open) return null;

  return (
    <div
      className="fixed inset-0 z-[70] grid place-items-center bg-black/55 backdrop-blur-sm px-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="preshare-consent-title"
      data-testid="preshare-consent-dialog"
      onClick={() => close(false)}
    >
      <div
        className="w-full max-w-lg rounded-3xl bg-white shadow-2xl border border-[#E5E0EE] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 px-6 sm:px-7 pt-6">
          <div className="flex-1">
            <div className="text-[0.6875rem] uppercase tracking-[0.22em] text-[#B02A2A] font-bold mb-1 flex items-center gap-1.5">
              <ShieldAlert size={14} /> You control this report
            </div>
            <h3
              id="preshare-consent-title"
              className="font-serif text-2xl text-[#1A1330] leading-tight"
            >
              Before you share {state.label}, please read this.
            </h3>
          </div>
          <button
            type="button"
            onClick={() => close(false)}
            data-testid="preshare-consent-close"
            aria-label="Cancel"
            className="w-9 h-9 rounded-full grid place-items-center bg-[#F8F7FC] hover:bg-[#EFE9F9] text-[#4B4567]"
          >
            <X size={16} />
          </button>
        </div>

        <div className="px-6 sm:px-7 py-5 space-y-4">
          <div
            className="rounded-2xl border border-[#E5E0EE] bg-gradient-to-br from-[#F1EAFF] to-[#F8F7FC] p-4 space-y-3"
            data-testid="preshare-consent-headline"
          >
            <p className="text-[0.8125rem] leading-relaxed text-[#1A1330] !m-0">
              <strong>Your information is private by default.</strong>{" "}
              SA CoParents does not share your assessment or reports with your co-parent or a professional unless you choose to share them, except where disclosure is required by law.
            </p>
            <p className="text-[0.8125rem] leading-relaxed text-[#1A1330] !m-0">
              <strong>Use of SA CoParents does not by itself create an attorney-client, therapist-patient, mediator-client, or other privileged relationship.</strong>
            </p>
          </div>

          <ul
            className="space-y-2.5 text-[13.5px] text-[#1A1330] leading-relaxed list-disc pl-5 marker:text-[#B02A2A]"
            data-testid="preshare-consent-bullets"
          >
            {BULLETS.map((b) => (
              <li key={b.id}>{b.text}</li>
            ))}
          </ul>

          <label
            className="flex items-start gap-3 rounded-2xl border border-[#E5E0EE] bg-[#F8F7FC] p-3 cursor-pointer hover:border-[#3D1A78] transition"
            data-testid="preshare-consent-ack-label"
          >
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              data-testid="preshare-consent-ack-checkbox"
              className="mt-1 h-4 w-4 accent-[#3D1A78] shrink-0"
            />
            <span className="text-[0.8125rem] text-[#1A1330] leading-relaxed">
              <strong>I understand.</strong> I&apos;ve read the six points above and I want to share {state.label} anyway.
            </span>
          </label>
        </div>

        <div className="flex items-center justify-end gap-2 px-6 sm:px-7 pb-6 pt-2">
          <button
            type="button"
            onClick={() => close(false)}
            data-testid="preshare-consent-cancel"
            className="rounded-full bg-white border border-[#E5E0EE] text-[#1A1330] px-4 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC]"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => close(true)}
            disabled={!checked}
            data-testid="preshare-consent-continue"
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-5 py-2.5 text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
          >
            I understand, continue
          </button>
        </div>
      </div>
    </div>
  );
}
