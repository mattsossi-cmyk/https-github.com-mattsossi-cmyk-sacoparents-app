/**
 * RefreshDraftModal.jsx — extracted from JointAgreement.jsx on
 * 2026-03-05.  Prompts the parent to confirm before rebuilding
 * their individual Co-Parenting Agreement Draft with anchored
 * clauses moved to the top of each section.
 */
import React from "react";
import { Loader2, RefreshCw } from "lucide-react";

export default function RefreshDraftModal({
  open,
  onCancel,
  onConfirm,
  regenerating,
  parentB,
  bothProposedCount = 0,
}) {
  if (!open) return null;
  const otherFirst = (parentB || "your co-parent").split(" ")[0] || "your co-parent";
  const count = bothProposedCount || 0;

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/45 backdrop-blur-sm px-4"
      data-testid="joint-agreement-regenerate-confirm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="joint-agreement-regen-title"
      onClick={() => !regenerating && onCancel()}
    >
      <div
        className="w-full max-w-md rounded-3xl bg-white shadow-2xl border border-[#E5E0EE] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 pt-6">
          <div className="text-[0.6875rem] uppercase tracking-[0.22em] text-[#1F5C3B] font-bold mb-1">
            Refresh my draft
          </div>
          <h3
            id="joint-agreement-regen-title"
            className="font-bold text-xl text-[#1A1330] leading-tight"
          >
            Anchor your individual draft to what you both already proposed?
          </h3>
        </div>
        <div className="px-6 py-5 space-y-3">
          <p className="text-sm text-[#4B4567] leading-relaxed">
            We&rsquo;ll create a fresh version of <strong>your</strong>{" "}
            individual Co-Parenting Agreement Draft. Clauses that both you
            and {otherFirst} already proposed will move to the top of each
            section and be marked as anchored.
          </p>
          <p className="text-sm text-[#4B4567] leading-relaxed">
            Your previous draft is kept — nothing is deleted. {count} clause
            {count === 1 ? "" : "s"} will be anchored.
          </p>
        </div>
        <div className="flex items-center justify-end gap-2 px-6 pb-6 pt-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={regenerating}
            data-testid="joint-agreement-regenerate-cancel"
            className="rounded-full bg-white border border-[#E5E0EE] text-[#1A1330] px-4 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC] disabled:opacity-60"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={regenerating}
            data-testid="joint-agreement-regenerate-confirm-btn"
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#1F5C3B] to-[#2DB5B5] text-white px-5 py-2.5 text-sm font-semibold disabled:opacity-60"
          >
            {regenerating ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <RefreshCw size={14} />
            )}
            {regenerating ? "Refreshing…" : "Refresh my draft"}
          </button>
        </div>
      </div>
    </div>
  );
}
