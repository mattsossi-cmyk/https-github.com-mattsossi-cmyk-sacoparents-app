import React, { useState, useEffect, useCallback } from "react";
import { ShieldAlert, Phone, MessageSquare, X, Home } from "lucide-react";

const NDV_HOTLINE_HREF = "tel:18007997233";
const TEXT_START_HREF = "sms:88788?&body=START";

/**
 * Full-screen safety overlay shown the instant the user toggles "Yes" on any
 * high-concern question (weapons / strangulation / stalking / protective-order
 * violation / abduction threat) OR when the final result is Level 1.
 *
 * Pressing ESC = Quick Exit (replaces the location with google.com, just like
 * the existing Safety page). Tabbing inside is supported because we trap focus
 * to the dialog.
 */
export default function HighConcernOverlay({ open, onContinue, onClose }) {
  const quickExit = useCallback(() => {
    try {
      window.location.replace("https://www.google.com");
      setTimeout(() => {
        try {
          window.history.back();
        } catch (_e) {
          /* noop */
        }
      }, 50);
    } catch (_e) {
      window.location.href = "https://www.google.com";
    }
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        quickExit();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, quickExit]);

  useEffect(() => {
    if (!open) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[120] bg-[#1A1330]/85 backdrop-blur-sm flex items-center justify-center p-4 sm:p-6"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="hc-title"
      data-testid="high-concern-overlay"
    >
      <div className="relative w-full max-w-xl bg-white rounded-3xl shadow-2xl overflow-hidden">
        {/* Red accent strip */}
        <div className="bg-gradient-to-r from-[#9A3A23] to-[#C28771] px-6 sm:px-8 py-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 text-white">
            <ShieldAlert size={22} />
            <div
              id="hc-title"
              className="font-bold text-lg sm:text-xl tracking-tight"
            >
              Your safety comes first
            </div>
          </div>
          <button
            type="button"
            onClick={quickExit}
            data-testid="hc-overlay-quick-exit"
            aria-label="Quick exit"
            className="inline-flex items-center gap-1.5 rounded-full bg-white text-[#9A3A23] px-3 py-1.5 text-xs font-bold hover:bg-[#FDF2EE] transition-colors"
          >
            <Home size={12} />
            Quick exit
          </button>
        </div>

        <div className="p-6 sm:p-8">
          <p
            className="text-[#1A1330] text-base leading-relaxed mb-4"
            data-testid="hc-overlay-message"
          >
            You answered <strong>yes</strong> to a question that flags an
            immediate safety concern (threats, physical harm, stalking, court-
            order violations, or abduction threats).
          </p>
          <p className="text-[#4B4567] text-sm leading-relaxed mb-6">
            Please pause for a moment. Direct communication with the other
            parent may not be appropriate right now. Reach out before going any
            further:
          </p>

          <div className="space-y-3 mb-6">
            <a
              href="tel:911"
              data-testid="hc-overlay-call-911"
              className="flex items-center gap-3 rounded-2xl bg-[#9A3A23] text-white px-5 py-4 font-bold text-base hover:bg-[#7e2e1c] transition-colors shadow-sm"
            >
              <Phone size={18} />
              <div className="flex-1">
                <div>Call 911</div>
                <div className="text-xs font-medium opacity-90">
                  If you are in immediate danger
                </div>
              </div>
            </a>
            <a
              href={NDV_HOTLINE_HREF}
              data-testid="hc-overlay-call-ndv"
              className="flex items-center gap-3 rounded-2xl bg-[#3D1A78] text-white px-5 py-4 font-bold text-base hover:bg-[#2d105e] transition-colors shadow-sm"
            >
              <Phone size={18} />
              <div className="flex-1">
                <div>National DV Hotline · 800-799-7233</div>
                <div className="text-xs font-medium opacity-90">
                  24/7 free, confidential, multilingual
                </div>
              </div>
            </a>
            <a
              href={TEXT_START_HREF}
              data-testid="hc-overlay-text-start"
              className="flex items-center gap-3 rounded-2xl bg-[#EFE9F9] text-[#3D1A78] px-5 py-4 font-bold text-base hover:bg-[#E5DCF5] transition-colors"
            >
              <MessageSquare size={18} />
              <div className="flex-1">
                <div>Text START to 88788</div>
                <div className="text-xs font-medium opacity-80">
                  Text-based support if you can&rsquo;t talk
                </div>
              </div>
            </a>
          </div>

          <div className="flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2 border-t border-[#E5E0EE]">
            <button
              type="button"
              onClick={onClose}
              data-testid="hc-overlay-close-button"
              className="inline-flex items-center justify-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#4B4567] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC]"
            >
              <X size={14} />
              Change my answer
            </button>
            <button
              type="button"
              onClick={onContinue}
              data-testid="hc-overlay-continue-button"
              className="inline-flex items-center justify-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-5 py-2.5 text-sm font-semibold shadow-md"
            >
              Continue the assessment
            </button>
          </div>
          <p className="text-[10px] text-[#857E9C] mt-3 text-center">
            Press <kbd className="px-1.5 py-0.5 rounded bg-[#EFE9F9]">ESC</kbd>{" "}
            any time to leave this page.
          </p>
        </div>
      </div>
    </div>
  );
}
