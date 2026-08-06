/**
 * BriefingEmailDialog — Modal to send the 4-Dimension Briefing PDF
 * directly to a mediator, parent facilitator ad litem, or trial court.
 *
 * The dialog collects: recipient email (required), name (optional),
 * recipient role (radio group — mediator / PFAL / trial court / attorney
 * / therapist), and an optional short message. It calls the provided
 * `onSend(payload)` and shows a `sending` spinner while the API is in
 * flight; the parent controls open/close via `open` + `onClose`.
 */
import { useState } from "react";
import { X, Send, Loader2 } from "lucide-react";

const ROLES = [
  { key: "mediator",                    label: "Mediator" },
  { key: "parent_facilitator_ad_litem", label: "Parent Facilitator Ad Litem" },
  { key: "trial_court",                 label: "Trial Court" },
  { key: "attorney",                    label: "Family Law Attorney" },
  { key: "therapist",                   label: "Therapist / Counsellor" },
  { key: "other",                       label: "Other" },
];

export default function BriefingEmailDialog({ open, onClose, onSend, sending }) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("mediator");
  const [message, setMessage] = useState("");

  if (!open) return null;
  const emailOk = /\S+@\S+\.\S+/.test(email.trim());
  const submit = () => {
    if (!emailOk || sending) return;
    onSend({
      recipient_email: email.trim(),
      recipient_name:  name.trim() || null,
      recipient_role:  role,
      parent_message:  message.trim() || null,
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/45 backdrop-blur-sm px-4"
      data-testid="briefing-email-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="briefing-dialog-title"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-3xl bg-white shadow-2xl border border-[#E5E0EE] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-3 px-6 sm:px-7 pt-6">
          <div>
            <div className="text-[11px] uppercase tracking-[0.22em] text-[#3D1A78] font-bold mb-1">
              Send 4-Dimension Briefing
            </div>
            <h3
              id="briefing-dialog-title"
              className="font-bold text-xl text-[#1A1330] leading-tight"
            >
              Email directly to the recipient
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="briefing-email-close"
            aria-label="Close"
            className="w-9 h-9 rounded-full grid place-items-center bg-[#F8F7FC] hover:bg-[#EFE9F9] text-[#4B4567]"
          >
            <X size={16} />
          </button>
        </div>

        <div className="px-6 sm:px-7 py-5 space-y-4">
          <p className="text-sm text-[#4B4567] leading-relaxed">
            We&rsquo;ll email your recipient the combined 4-Dimension Briefing
            PDF (Safety + Dim 2/3/4). They can reply directly to your email.
          </p>

          <div>
            <label className="block text-[11px] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Recipient role
            </label>
            <div className="flex flex-wrap gap-1.5">
              {ROLES.map((r) => (
                <button
                  key={r.key}
                  type="button"
                  onClick={() => setRole(r.key)}
                  data-testid={`briefing-role-${r.key}`}
                  className={`text-[12px] px-3 py-1.5 rounded-full border transition ${
                    role === r.key
                      ? "bg-[#3D1A78] text-white border-[#3D1A78] font-semibold"
                      : "bg-white text-[#4B4567] border-[#E5E0EE] hover:border-[#3D1A78]"
                  }`}
                  aria-pressed={role === r.key}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-[11px] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Recipient email <span aria-hidden="true" className="text-[#9A3A23]">*</span>
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="recipient@example.com"
              data-testid="briefing-email-input"
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
              autoComplete="email"
              required
            />
          </div>

          <div>
            <label className="block text-[11px] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Recipient name <span className="text-[#857E9C] font-normal normal-case tracking-normal">· optional</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Jamie Rivera"
              data-testid="briefing-name-input"
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
            />
          </div>

          <div>
            <label className="block text-[11px] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Short message <span className="text-[#857E9C] font-normal normal-case tracking-normal">· optional</span>
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Anything you want them to know before reading the briefing…"
              rows={3}
              maxLength={1200}
              data-testid="briefing-message-input"
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30 resize-none"
            />
          </div>

          <p className="text-[11px] text-[#8471B3] italic">
            Reply-to is set to your email so the recipient can respond directly. The
            briefing is informational preparation support only — not legal advice.
          </p>
        </div>

        <div className="flex items-center justify-end gap-2 px-6 sm:px-7 pb-6 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={sending}
            data-testid="briefing-email-cancel"
            className="rounded-full bg-white border border-[#E5E0EE] text-[#1A1330] px-4 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC] disabled:opacity-60"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={!emailOk || sending}
            data-testid="briefing-email-send"
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-5 py-2.5 text-sm font-semibold disabled:opacity-60"
          >
            {sending ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
            {sending ? "Sending…" : "Send briefing"}
          </button>
        </div>
      </div>
    </div>
  );
}
