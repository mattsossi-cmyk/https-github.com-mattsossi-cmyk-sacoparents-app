import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { SafetyPlanBuilder } from "./SafetyPlanBuilder";

/**
 * SafetyScreen — first-visit safety triage before letting the parent
 * enter either Door. Three questions cover the core IPV / family-
 * violence signals (physical safety, coercion & control, device
 * privacy). Never blocks a parent from continuing — per clinical
 * guardrail rule — but re-routes flagged parents to the Safety Path
 * card with hotlines + deep-link to the full /safety-assessment, and
 * offers an optional private Safety Plan builder.
 *
 * Rendered in two modes:
 *   - `open` (modal) — used as a re-take chip from the Parent Journey
 *   - full-screen — used as the first-visit gate before either Door
 *
 * Props:
 *   - open          : bool                — render the modal wrapper
 *   - onClose       : () => void          — dismiss without submitting
 *   - onCleared     : () => void          — Safety Screen returned "no risk"
 *   - onContinueFlagged : () => void      — parent chose "Continue anyway"
 *   - safetyPlan    : object              — persisted Safety Plan (or null)
 *   - onSaveSafetyPlan : (plan) => void   — save the Safety Plan
 */
export function SafetyScreen({
  open,
  onClose,
  onCleared,
  onContinueFlagged,
  safetyPlan,
  onSaveSafetyPlan,
}) {
  const [phys, setPhys] = useState(null); // 'yes' | 'no' | 'prefer_not'
  const [coerce, setCoerce] = useState(null); // 'yes' | 'no' | 'prefer_not'
  const [device, setDevice] = useState(null); // 'yes' | 'no' | 'unsure' | 'prefer_not'
  const [showFlaggedCard, setShowFlaggedCard] = useState(false);

  // Reset the questionnaire whenever the modal re-opens so the parent
  // starts from a clean slate every time (crucial on re-take).
  useEffect(() => {
    if (open) {
      setPhys(null);
      setCoerce(null);
      setDevice(null);
      setShowFlaggedCard(false);
    }
  }, [open]);

  if (!open) return null;

  const answered = phys != null && coerce != null && device != null;

  // "I'd rather not answer" is a skip: it never flags anything.
  const isFlagged =
    phys === "no" ||
    coerce === "yes" ||
    device === "no" ||
    device === "unsure";

  const submit = () => {
    if (!answered) return;
    if (isFlagged) {
      setShowFlaggedCard(true);
    } else {
      onCleared({ phys, coerce, device });
    }
  };

  const resetAndClose = () => {
    setPhys(null);
    setCoerce(null);
    setDevice(null);
    setShowFlaggedCard(false);
    onClose();
  };

  return (
    <div
      className="fixed inset-0 bg-slate-900/70 backdrop-blur-sm z-50 flex items-start justify-center p-4 overflow-y-auto no-print"
      data-testid="modal-safety-screen"
    >
      <div className="bg-white w-full max-w-sm rounded-2xl shadow-xl space-y-3 p-5 my-4">
        <div className="flex justify-between items-start border-b border-slate-100 pb-3">
          <div>
            <span className="bg-rose-100 text-rose-900 text-[0.625rem] font-bold px-2 py-0.5 rounded uppercase tracking-wider">
              Safety First
            </span>
            <h3 className="font-bold text-slate-800 text-sm mt-1">
              Quick Safety Check
            </h3>
            <p className="text-[0.625rem] text-slate-500 mt-1 leading-snug">
              Three questions. Your answers stay on this device unless
              you're signed in and syncing. This is <strong>not</strong> a
              clinical screen — for that, tap "Full safety screen" below.
            </p>
          </div>
          <button
            data-testid="close-safety-screen"
            onClick={resetAndClose}
            className="text-slate-400 hover:text-slate-600"
            aria-label="Close safety screen"
          >
            <i className="fa-solid fa-xmark"></i>
          </button>
        </div>

        {!showFlaggedCard && (
          <div className="space-y-3 text-xs">
            {/* Q1 physical safety */}
            <div data-testid="safety-q-phys">
              <label className="font-semibold text-slate-700 block mb-1">
                1. Do you feel physically safe right now?
              </label>
              <div className="flex gap-2 flex-wrap">
                <button
                  type="button"
                  data-testid="safety-q-phys-yes"
                  onClick={() => setPhys("yes")}
                  className={
                    phys === "yes"
                      ? "flex-1 py-2 rounded-lg font-bold bg-emerald-700 text-white text-xs"
                      : "flex-1 py-2 rounded-lg font-bold bg-slate-100 text-slate-600 text-xs border border-slate-200"
                  }
                >
                  Yes
                </button>
                <button
                  type="button"
                  data-testid="safety-q-phys-no"
                  onClick={() => setPhys("no")}
                  className={
                    phys === "no"
                      ? "flex-1 py-2 rounded-lg font-bold bg-rose-700 text-white text-xs"
                      : "flex-1 py-2 rounded-lg font-bold bg-slate-100 text-slate-600 text-xs border border-slate-200"
                  }
                >
                  No
                </button>
                <PreferNotButton testid="safety-q-phys-prefer-not" value={phys} onPick={setPhys} />
              </div>
            </div>

            {/* Q2 coercion / control */}
            <div data-testid="safety-q-coerce">
              <label className="font-semibold text-slate-700 block mb-1">
                2. Has there been intimidation, coercion, control of
                money, or physical harm from your co-parent?
              </label>
              <div className="flex gap-2 flex-wrap">
                <button
                  type="button"
                  data-testid="safety-q-coerce-yes"
                  onClick={() => setCoerce("yes")}
                  className={
                    coerce === "yes"
                      ? "flex-1 py-2 rounded-lg font-bold bg-rose-700 text-white text-[0.6875rem]"
                      : "flex-1 py-2 rounded-lg font-bold bg-slate-100 text-slate-600 text-[0.6875rem] border border-slate-200"
                  }
                >
                  Yes
                </button>
                <button
                  type="button"
                  data-testid="safety-q-coerce-no"
                  onClick={() => setCoerce("no")}
                  className={
                    coerce === "no"
                      ? "flex-1 py-2 rounded-lg font-bold bg-emerald-700 text-white text-[0.6875rem]"
                      : "flex-1 py-2 rounded-lg font-bold bg-slate-100 text-slate-600 text-[0.6875rem] border border-slate-200"
                  }
                >
                  No
                </button>
                <PreferNotButton testid="safety-q-coerce-prefer-not" value={coerce} onPick={setCoerce} />
              </div>
            </div>

            {/* Q3 device privacy */}
            <div data-testid="safety-q-device">
              <label className="font-semibold text-slate-700 block mb-1">
                3. Is this device private — not shared or monitored?
              </label>
              <div className="flex gap-2 flex-wrap">
                <button
                  type="button"
                  data-testid="safety-q-device-yes"
                  onClick={() => setDevice("yes")}
                  className={
                    device === "yes"
                      ? "flex-1 py-2 rounded-lg font-bold bg-emerald-700 text-white text-[0.6875rem]"
                      : "flex-1 py-2 rounded-lg font-bold bg-slate-100 text-slate-600 text-[0.6875rem] border border-slate-200"
                  }
                >
                  Yes
                </button>
                <button
                  type="button"
                  data-testid="safety-q-device-no"
                  onClick={() => setDevice("no")}
                  className={
                    device === "no"
                      ? "flex-1 py-2 rounded-lg font-bold bg-rose-700 text-white text-[0.6875rem]"
                      : "flex-1 py-2 rounded-lg font-bold bg-slate-100 text-slate-600 text-[0.6875rem] border border-slate-200"
                  }
                >
                  No
                </button>
                <button
                  type="button"
                  data-testid="safety-q-device-unsure"
                  onClick={() => setDevice("unsure")}
                  className={
                    device === "unsure"
                      ? "w-full mt-1 py-2 rounded-lg font-bold bg-amber-600 text-white text-[0.6875rem]"
                      : "w-full mt-1 py-2 rounded-lg font-bold bg-slate-100 text-slate-600 text-[0.6875rem] border border-slate-200"
                  }
                >
                  Not sure
                </button>
                <PreferNotButton testid="safety-q-device-prefer-not" value={device} onPick={setDevice} />
              </div>
            </div>

            <div className="pt-2 flex justify-end gap-2">
              <button
                type="button"
                data-testid="submit-safety-screen-btn"
                onClick={submit}
                disabled={!answered}
                className="px-3 py-1.5 bg-purple-800 disabled:opacity-40 text-white rounded-lg font-semibold text-xs"
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {showFlaggedCard && (
          <div
            className="space-y-3 text-xs"
            data-testid="safety-flagged-card"
          >
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl">
              <div className="flex items-start gap-2">
                <i className="fa-solid fa-shield-heart text-rose-700 text-lg mt-0.5"></i>
                <div>
                  <div className="font-bold text-rose-900 text-sm">
                    Your safety comes first.
                  </div>
                  <p className="text-rose-800 text-[0.6875rem] mt-1 leading-snug">
                    BIFF messaging, Legal Reports, and joint tools all
                    assume both parents are safe. When there's
                    intimidation, coercion, or physical harm, these
                    tools can put you at more risk — not less.
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="font-semibold text-slate-700 text-[0.6875rem] uppercase tracking-wider">
                Immediate help
              </div>
              <div className="grid grid-cols-1 gap-1.5">
                <a
                  href="tel:911"
                  data-testid="safety-flagged-call-911"
                  className="p-2 bg-rose-700 text-white rounded-lg font-bold text-[0.6875rem] flex items-center justify-between"
                >
                  <span>
                    <i className="fa-solid fa-phone mr-2"></i>
                    In immediate danger
                  </span>
                  <span>Call 911</span>
                </a>
                <a
                  href="tel:18007997233"
                  data-testid="safety-flagged-dv-hotline"
                  className="p-2 bg-purple-800 text-white rounded-lg font-bold text-[0.6875rem] flex items-center justify-between"
                >
                  <span>
                    <i className="fa-solid fa-hand-holding-heart mr-2"></i>
                    Talk to an advocate
                  </span>
                  <span>1-800-799-7233</span>
                </a>
                <a
                  href="sms:88788?body=START"
                  data-testid="safety-flagged-text-start"
                  className="p-2 bg-purple-700 text-white rounded-lg font-bold text-[0.6875rem] flex items-center justify-between"
                >
                  <span>
                    <i className="fa-solid fa-message mr-2"></i>
                    Text if calling isn't safe
                  </span>
                  <span>START to 88788</span>
                </a>
              </div>
            </div>

            <Link
              to="/safety-assessment"
              data-testid="safety-flagged-full-screen-link"
              className="block w-full text-center p-2 bg-white border-2 border-purple-700 text-purple-800 rounded-lg font-bold text-[0.6875rem]"
            >
              Open the full clinical Safety Screen
            </Link>

            {/* Optional private Safety Plan builder — never surfaced to
                the co-parent. Sits between the hotline block and the
                "continue anyway" foot so the parent sees concrete
                next steps before deciding to press on. */}
            <SafetyPlanBuilder
              plan={safetyPlan}
              onSave={onSaveSafetyPlan}
            />

            <div className="pt-1 border-t border-slate-100">
              <p className="text-[0.625rem] text-slate-500 leading-snug mb-1.5">
                {coerce === "yes"
                  ? "Grey-rock mode is on — the Portal will quietly adapt its tools and language so nothing you do here can be used against you. You can turn it off from the Alignment & Tools page any time."
                  : "You can still enter the Portal — nothing here will lock you out. Just know these tools work best after the safety picture is clearer."}
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  data-testid="safety-flagged-continue-btn"
                  onClick={() => onContinueFlagged({ phys, coerce, device })}
                  className="flex-1 px-3 py-1.5 bg-slate-200 text-slate-700 rounded-lg font-semibold text-[0.6875rem]"
                >
                  {coerce === "yes"
                    ? "Enter the Portal in grey-rock mode"
                    : "Continue to the Portal anyway"}
                </button>
                {/* iter241 — Safety-First auto-route: when intimidation
                    is flagged (coerce === "yes") the Close button
                    no longer dumps the parent back onto the Gateway
                    unprotected. It routes into grey-rock mode too,
                    with a softer label so the control stays visible
                    but is no longer an unsafe exit. */}
                <button
                  type="button"
                  data-testid="safety-flagged-close-btn"
                  onClick={
                    coerce === "yes"
                      ? () => onContinueFlagged({ phys, coerce, device })
                      : resetAndClose
                  }
                  className="px-3 py-1.5 border border-slate-300 rounded-lg font-semibold text-slate-600 text-[0.6875rem]"
                >
                  {coerce === "yes" ? "Not now" : "Close"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * SafetyRetakeChip — small persistent chip that re-opens the safety
 * screen from the Parent Journey header. Shows a different colour if
 * the parent's last screening was flagged (so it stays visible +
 * inviting).
 */
export function SafetyRetakeChip({ onOpen, flagged }) {
  return (
    <button
      type="button"
      data-testid="safety-retake-chip"
      onClick={onOpen}
      className={
        flagged
          ? "no-print inline-flex items-center gap-1.5 bg-rose-50 border border-rose-300 text-rose-800 px-2.5 py-1 rounded-full text-[0.625rem] font-bold hover:bg-rose-100 transition"
          : "no-print inline-flex items-center gap-1.5 bg-purple-50 border border-purple-200 text-purple-800 px-2.5 py-1 rounded-full text-[0.625rem] font-bold hover:bg-purple-100 transition"
      }
    >
      <i className="fa-solid fa-shield-heart"></i>
      {flagged ? "Safety concerns flagged — tap to re-check" : "Safety concerns? Re-take"}
    </button>
  );
}

/**
 * SafetySoftBanner — soft warning shown INSIDE the AlignmentHub and
 * BiffTab when the parent's Safety Screen returned any risk flag.
 * Never blocks the tool — clinical guardrail — but names the mismatch
 * clearly so the parent knows what they're stepping into.
 */
export function SafetySoftBanner({ context }) {
  const contextLine =
    context === "biff"
      ? "BIFF assumes both parents want to lower the temperature. If your co-parent uses your reply to escalate or control, tone-safe copy alone won't fix that."
      : "Legal Reports and Foundation Statements assume both parents can safely sign and share. If that isn't true right now, use the Safety Path first.";

  return (
    <div
      data-testid={`safety-soft-banner-${context}`}
      className="bg-amber-50 border border-amber-200 rounded-xl p-3 space-y-1.5 text-xs no-print"
    >
      <div className="flex items-start gap-2">
        <i className="fa-solid fa-triangle-exclamation text-amber-700 mt-0.5" aria-hidden></i>
        <div className="flex-1">
          <div className="font-bold text-amber-900 text-[0.6875rem]">
            Safety concern flagged in your Quick Safety Check
          </div>
          <p className="text-amber-800 text-[0.6875rem] leading-snug mt-0.5">
            {contextLine}
          </p>
          <div className="mt-1.5 flex flex-wrap gap-2 text-[0.625rem] font-bold">
            <a
              href="tel:18007997233"
              className="text-purple-800 underline"
              data-testid={`safety-soft-banner-hotline-${context}`}
            >
              DV Hotline 1-800-799-7233
            </a>
            <Link
              to="/safety-assessment"
              className="text-purple-800 underline"
              data-testid={`safety-soft-banner-full-screen-${context}`}
            >
              Full clinical safety screen
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function PreferNotButton({ testid, value, onPick }) {
  const on = value === "prefer_not";
  return (
    <button
      type="button"
      data-testid={testid}
      aria-pressed={on}
      onClick={() => onPick("prefer_not")}
      className={
        on
          ? "w-full mt-1 py-2 rounded-lg font-bold bg-slate-600 text-white text-[0.6875rem]"
          : "w-full mt-1 py-2 rounded-lg font-bold bg-white text-slate-600 text-[0.6875rem] border border-dashed border-slate-300"
      }
    >
      I'd rather not answer
    </button>
  );
}
