/**
 * AgreementShareLinkModal.jsx — extracted from JointAgreement.jsx on
 * 2026-03-05.  Two-mode share-link dialog: (a) configure expiry +
 * optional note, then mint; (b) show the resulting link with
 * copy/revoke controls.  All state is owned by the parent page so
 * the mint/revoke API calls stay together with the report data.
 */
import React from "react";
import { Loader2, Link2, Trash2, Copy, Check } from "lucide-react";

export default function AgreementShareLinkModal({
  open,
  onClose,
  shareLinkResult,
  shareLinkExpireDays,
  setShareLinkExpireDays,
  shareLinkMinting,
  shareLinkRevoking,
  shareLinkNote,
  setShareLinkNote,
  onMint,
  onRevoke,
  onCopy,
  shareLinkCopied,
  shareLinkInputRef,
}) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/45 backdrop-blur-sm px-4"
      data-testid="joint-agreement-share-link-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="joint-agreement-share-link-title"
      onClick={() => !shareLinkMinting && !shareLinkRevoking && onClose()}
    >
      <div
        className="w-full max-w-lg rounded-3xl bg-white shadow-2xl border border-[#E5E0EE] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 pt-6">
          <div className="text-[0.6875rem] uppercase tracking-[0.22em] text-[#3D1A78] font-bold mb-1">
            Shareable link
          </div>
          <h3
            id="joint-agreement-share-link-title"
            className="font-bold text-xl text-[#1A1330] leading-tight"
          >
            Give your mediator or attorney direct access
          </h3>
        </div>

        {!shareLinkResult && (
          <div className="px-6 py-5 space-y-4">
            <p className="text-sm text-[#4B4567] leading-relaxed">
              We&rsquo;ll generate a signed link they can open in any
              browser — no login required. The link renders the same
              joint draft you see here and lets them download the PDF.
              You can revoke it at any time.
            </p>
            <div>
              <label
                htmlFor="joint-agreement-share-link-expiry"
                className="block text-[0.625rem] uppercase tracking-[0.18em] text-[#3D1A78] font-semibold mb-1.5"
              >
                Link expires in
              </label>
              <select
                id="joint-agreement-share-link-expiry"
                value={shareLinkExpireDays}
                onChange={(e) => setShareLinkExpireDays(parseInt(e.target.value, 10))}
                disabled={shareLinkMinting}
                data-testid="joint-agreement-share-link-expiry-select"
                className="w-full rounded-xl border border-[#E5E0EE] bg-white px-3 py-2.5 text-sm text-[#1A1330] focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30 disabled:opacity-60"
              >
                <option value={1}>1 day</option>
                <option value={7}>7 days</option>
                <option value={14}>14 days</option>
                <option value={30}>30 days</option>
              </select>
            </div>
            <div>
              <label
                htmlFor="joint-agreement-share-link-note"
                className="block text-[0.625rem] uppercase tracking-[0.18em] text-[#3D1A78] font-semibold mb-1.5"
              >
                Optional note for the recipient
              </label>
              <textarea
                id="joint-agreement-share-link-note"
                value={shareLinkNote}
                onChange={(e) => setShareLinkNote(e.target.value.slice(0, 500))}
                disabled={shareLinkMinting}
                rows={3}
                maxLength={500}
                placeholder="e.g. Hi Sam — this is the joint draft I mentioned. Happy to walk through it on Tuesday."
                data-testid="joint-agreement-share-link-note-input"
                className="w-full rounded-xl border border-[#E5E0EE] bg-white px-3 py-2 text-sm text-[#1A1330] leading-relaxed focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30 disabled:opacity-60 resize-none"
              />
              <div className="mt-1 text-[0.6875rem] text-[#6E6787] text-right">
                {shareLinkNote.length}/500
              </div>
            </div>
          </div>
        )}

        {shareLinkResult && (
          <div className="px-6 py-5 space-y-4">
            <p className="text-sm text-[#4B4567] leading-relaxed">
              Copy the link below and send it however you like — email,
              secure message, or paste it into your case system. Anyone
              with the link can view and download until you revoke it or
              it expires.
            </p>
            <div className="rounded-xl border border-[#D6CFE8] bg-[#F5F1FB] p-3">
              <input
                ref={shareLinkInputRef}
                type="text"
                readOnly
                value={`${window.location.origin}${shareLinkResult.preview_path || shareLinkResult.path}`}
                onFocus={(e) => e.target.select()}
                data-testid="joint-agreement-share-link-url"
                className="w-full bg-transparent text-sm text-[#1A1330] font-mono outline-none"
              />
            </div>
            {shareLinkResult.expires_at && (
              <div
                className="text-xs text-[#4B4567]"
                data-testid="joint-agreement-share-link-expiry-info"
              >
                Expires{" "}
                {new Date(shareLinkResult.expires_at).toLocaleString(undefined, {
                  year: "numeric",
                  month: "short",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </div>
            )}
          </div>
        )}

        <div className="flex items-center justify-between gap-2 px-6 pb-6 pt-2 flex-wrap">
          <button
            type="button"
            onClick={onClose}
            disabled={shareLinkMinting || shareLinkRevoking}
            data-testid="joint-agreement-share-link-close"
            className="rounded-full bg-white border border-[#E5E0EE] text-[#1A1330] px-4 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC] disabled:opacity-60"
          >
            {shareLinkResult ? "Done" : "Cancel"}
          </button>
          {!shareLinkResult ? (
            <button
              type="button"
              onClick={onMint}
              disabled={shareLinkMinting}
              data-testid="joint-agreement-share-link-create-btn"
              className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-5 py-2.5 text-sm font-semibold disabled:opacity-60"
            >
              {shareLinkMinting ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Link2 size={14} />
              )}
              {shareLinkMinting ? "Creating…" : "Create link"}
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onRevoke}
                disabled={shareLinkRevoking}
                data-testid="joint-agreement-share-link-revoke-btn"
                className="inline-flex items-center gap-1.5 rounded-full bg-white border border-[#B02A2A] text-[#B02A2A] px-4 py-2.5 text-sm font-semibold hover:bg-[#FBEBEB] disabled:opacity-60"
              >
                {shareLinkRevoking ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Trash2 size={14} />
                )}
                Revoke
              </button>
              <button
                type="button"
                onClick={onCopy}
                data-testid="joint-agreement-share-link-copy-btn"
                className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-5 py-2.5 text-sm font-semibold"
              >
                {shareLinkCopied ? <Check size={14} /> : <Copy size={14} />}
                {shareLinkCopied ? "Copied" : "Copy link"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
