/**
 * ReviewerSendDialog — Operator-only modal to email the Reviewer Packet
 * directly to a candidate reviewer (DV advocate / forensic psychologist /
 * family-law attorney / clinician / other).
 *
 * Consumes `POST /api/reviewer-panel/send`. The backend gates on the
 * OPERATOR_EMAIL configured in the environment; the dialog itself is
 * only rendered by ReviewerPanelCard when `/reviewer-panel/is-operator`
 * returns true.
 */
import { useState } from "react";
import { X, Send, Loader2 } from "lucide-react";

const ROLES = [
  { key: "dv_advocate",           label: "Domestic-violence advocate" },
  { key: "forensic_psychologist", label: "Forensic psychologist" },
  { key: "family_law_attorney",   label: "Texas family-law attorney" },
  { key: "clinician",             label: "Licensed clinician" },
  { key: "other",                 label: "Other" },
];

export default function ReviewerSendDialog({ open, onClose, onSend, sending }) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("dv_advocate");
  const [note, setNote] = useState("");

  if (!open) return null;
  const emailOk = /\S+@\S+\.\S+/.test(email.trim());

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/45 backdrop-blur-sm px-4"
      data-testid="reviewer-send-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="reviewer-send-dialog-title"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-3xl bg-white shadow-2xl border border-[#E5E0EE] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-3 px-6 sm:px-7 pt-6">
          <div>
            <div className="text-[0.6875rem] uppercase tracking-[0.22em] text-[#3D1A78] font-bold mb-1">
              Operator only · Send reviewer packet
            </div>
            <h3
              id="reviewer-send-dialog-title"
              className="font-bold text-xl text-[#1A1330] leading-tight"
            >
              Invite a reviewer
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="reviewer-send-close"
            aria-label="Close"
            className="w-9 h-9 rounded-full grid place-items-center bg-[#F8F7FC] hover:bg-[#EFE9F9] text-[#4B4567]"
          >
            <X size={16} />
          </button>
        </div>

        <div className="px-6 sm:px-7 py-5 space-y-4">
          <p className="text-sm text-[#4B4567] leading-relaxed">
            We&rsquo;ll email the reviewer packet PDF with a branded cover
            letter. Reply-to is set to your operator email so the reviewer
            can respond directly.
          </p>

          <div>
            <label className="block text-[0.6875rem] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Reviewer role
            </label>
            <div className="flex flex-wrap gap-1.5">
              {ROLES.map((r) => (
                <button
                  key={r.key}
                  type="button"
                  onClick={() => setRole(r.key)}
                  data-testid={`reviewer-send-role-${r.key}`}
                  className={`text-[0.75rem] px-3 py-1.5 rounded-full border transition ${
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
            <label className="block text-[0.6875rem] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Reviewer email <span className="text-[#9A3A23]">*</span>
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="reviewer@example.com"
              data-testid="reviewer-send-email-input"
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
              autoComplete="email"
              required
            />
          </div>

          <div>
            <label className="block text-[0.6875rem] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Reviewer name{" "}
              <span className="text-[#6E6787] font-normal normal-case tracking-normal">· optional</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Dr. Jane Rivera"
              data-testid="reviewer-send-name-input"
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
            />
          </div>

          <div>
            <label className="block text-[0.6875rem] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Personal note{" "}
              <span className="text-[#6E6787] font-normal normal-case tracking-normal">· optional</span>
            </label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Anything you want to say to this reviewer directly…"
              rows={3}
              maxLength={1200}
              data-testid="reviewer-send-note-input"
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30 resize-none"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 px-6 sm:px-7 pb-6 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={sending}
            data-testid="reviewer-send-cancel"
            className="rounded-full bg-white border border-[#E5E0EE] text-[#1A1330] px-4 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC] disabled:opacity-60"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => onSend({
              recipient_email: email.trim(),
              recipient_name:  name.trim() || "",
              recipient_role:  role,
              personal_note:   note.trim() || "",
            })}
            disabled={!emailOk || sending}
            data-testid="reviewer-send-submit"
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-5 py-2.5 text-sm font-semibold disabled:opacity-60"
          >
            {sending ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
            {sending ? "Sending…" : "Send packet"}
          </button>
        </div>
      </div>
    </div>
  );
}
