/**
 * MediatorEmailDialog.jsx — extracted from SafetyAssessment.jsx on
 * 2026-03-05.  A warm-handoff dialog that lets a parent email their
 * TISFL pathway (with the full PDF attached) to their mediator or
 * DV advocate. The parent stays anonymous unless they choose to fill
 * in their own name and message.
 */
import React, { useState } from "react";
import { Send, X } from "lucide-react";

export default function MediatorEmailDialog({ open, onClose, onSend, sending }) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");

  if (!open) return null;

  const emailOk = /\S+@\S+\.\S+/.test(email.trim());

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/45 backdrop-blur-sm px-4"
      data-testid="mediator-email-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="mediator-dialog-title"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-3xl bg-white shadow-2xl border border-[#E5E0EE] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-3 px-6 sm:px-7 pt-6">
          <div>
            <div className="text-[11px] uppercase tracking-[0.22em] text-[#3D1A78] font-bold mb-1">
              Send to your mediator
            </div>
            <h3
              id="mediator-dialog-title"
              className="font-bold text-xl text-[#1A1330] leading-tight"
            >
              Email your safety pathway
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="mediator-email-close"
            aria-label="Close"
            className="w-9 h-9 rounded-full grid place-items-center bg-[#F8F7FC] hover:bg-[#EFE9F9] text-[#4B4567]"
          >
            <X size={16} />
          </button>
        </div>
        <div className="px-6 sm:px-7 py-5 space-y-4">
          <p className="text-sm text-[#4B4567] leading-relaxed">
            We&rsquo;ll email your mediator a private link to your recommended
            pathway. The PDF isn&rsquo;t attached; they open it with a one-time
            code. They can reply directly to your email address.
          </p>
          <div>
            <label className="block text-[11px] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Mediator email <span aria-hidden="true" className="text-[#9A3A23]">*</span>
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="mediator@example.com"
              data-testid="mediator-email-input"
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
              autoComplete="email"
              required
            />
          </div>
          <div>
            <label className="block text-[11px] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Mediator name <span className="text-[#857E9C] font-normal normal-case tracking-normal">· optional</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Jamie Rivera"
              data-testid="mediator-name-input"
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
            />
          </div>
          <div>
            <label className="block text-[11px] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Message to your mediator <span className="text-[#857E9C] font-normal normal-case tracking-normal">· optional</span>
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Anything you want your mediator to know before our session…"
              rows={3}
              data-testid="mediator-message-input"
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30 resize-none"
            />
          </div>
        </div>
        <div className="px-6 sm:px-7 pb-6 flex flex-wrap gap-3 justify-end">
          <button
            type="button"
            onClick={onClose}
            data-testid="mediator-email-cancel"
            className="inline-flex items-center gap-2 rounded-full bg-white border border-[#E5E0EE] text-[#4B4567] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC]"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() =>
              onSend({
                mediator_email: email.trim(),
                mediator_name: name.trim(),
                parent_message: message.trim(),
              })
            }
            disabled={!emailOk || sending}
            data-testid="mediator-email-send"
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-5 py-2.5 text-sm font-semibold shadow-md disabled:opacity-50"
          >
            <Send size={14} />
            {sending ? "Sending…" : "Send to my mediator"}
          </button>
        </div>
      </div>
    </div>
  );
}
