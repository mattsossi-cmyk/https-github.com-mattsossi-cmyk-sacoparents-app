/**
 * ActivitiesShareCodeCard.jsx — extracted from `ActivitiesAlignment.jsx`
 * (2026-03-06).
 *
 * The "Send this to your mediator or attorney" card at the bottom of
 * the ready state. Owns three render branches:
 *   1. `shareError`  — safety-gate block (family-violence screen
 *                      required OR direct outreach blocked) with the
 *                      correct escape CTAs.
 *   2. `shareCode`   — success state showing the SA-XXXXXX code + a
 *                      Copy button + 15-minute expiry note.
 *   3. default       — a "Get a share code" mint button.
 *
 * Stateless — the parent page manages minting via the passed
 * `onMint` callback and passes down the resolved shareCode/shareError.
 */
import React from "react";
import { Link } from "react-router-dom";
import {
  Copy,
  Link as LinkIcon,
  Loader2,
  Send,
  ShieldAlert,
} from "lucide-react";

export default function ActivitiesShareCodeCard({
  shareError,
  shareCode,
  minting,
  onMint,
  onCopy,
}) {
  return (
    <div className="rounded-3xl border border-[#C7E5D3] bg-white p-6 sm:p-7">
      <div className="flex items-start gap-3 mb-3">
        <LinkIcon size={20} className="text-[#1E7A55] shrink-0 mt-1" />
        <div>
          <h2 className="font-serif text-xl text-[#1A1330] leading-tight">
            Send this to your mediator or attorney
          </h2>
          <p className="text-sm text-[#4B4567] mt-1 leading-relaxed">
            Get a short one-time code they can enter on{" "}
            <strong className="text-[#1A1330]">sacoparentsalign.com</strong>{" "}
            to pull up your Alignment Report.
          </p>
        </div>
      </div>

      {shareError ? (
        <div
          className="rounded-2xl border-2 border-[#F1B7B7] bg-[#FDECEC] p-4 flex items-start gap-3"
          data-testid="activities-alignment-share-error"
        >
          <ShieldAlert size={18} className="text-[#9A3A23] shrink-0 mt-0.5" />
          <div className="text-sm text-[#5B1F1F] leading-relaxed">
            <div className="font-semibold">
              {shareError.code === "safety_screen_required"
                ? "Complete the family-violence safety screen first"
                : "Direct outreach isn't recommended right now"}
            </div>
            <p className="mt-1">{shareError.message}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Link
                to="/safety"
                className="inline-flex items-center gap-2 rounded-full bg-[#9A3A23] text-white px-4 py-2 text-xs font-semibold hover:brightness-110"
              >
                {shareError.code === "safety_screen_required"
                  ? "Take the safety screen"
                  : "Review my safety plan"}
              </Link>
              {shareError.code === "safety_screen_blocked" && (
                <Link
                  to="/professionals"
                  className="inline-flex items-center gap-2 rounded-full border border-[#9A3A23] text-[#9A3A23] px-4 py-2 text-xs font-semibold hover:bg-[#FDECEC]"
                >
                  Send my case to a mediator instead
                </Link>
              )}
            </div>
          </div>
        </div>
      ) : shareCode ? (
        <div
          className="rounded-2xl bg-[#F1F9F4] border border-[#C7E5D3] p-5"
          data-testid="activities-alignment-share-success"
        >
          <div className="text-[0.625rem] uppercase tracking-[0.18em] font-bold text-[#1E7A55] mb-1">
            Share code
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <code className="font-mono text-2xl tracking-widest text-[#1A1330] px-4 py-2 rounded-xl bg-white border border-[#C7E5D3]">
              {shareCode.code}
            </code>
            <button
              type="button"
              onClick={() => onCopy(shareCode.code)}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-full text-xs font-semibold border border-[#1E7A55] text-[#1E7A55] hover:bg-[#DEF5E0]"
              data-testid="activities-alignment-copy-code"
            >
              <Copy size={12} /> Copy
            </button>
          </div>
          <p className="text-xs text-[#1E7A55] mt-3 leading-relaxed">
            Valid for 15 minutes. Send this code to your mediator or
            attorney — they enter it on the sibling app to view the
            report.
          </p>
        </div>
      ) : (
        <button
          type="button"
          onClick={onMint}
          disabled={minting}
          data-testid="activities-alignment-mint-code"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#1E7A55] text-white text-sm font-semibold hover:brightness-110 disabled:opacity-60"
        >
          {minting ? <Loader2 className="animate-spin" size={14} /> : <Send size={14} />}
          Get a share code
        </button>
      )}
    </div>
  );
}
