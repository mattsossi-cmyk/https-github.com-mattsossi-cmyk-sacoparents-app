/**
 * JointReportEmailDialog — Modal to send the Joint Co-Parenting Summary
 * for Professional Review PDF directly to a mediator, attorney, court,
 * therapist, or parent facilitator ad litem.
 *
 * Mirrors PathwayEmailDialog's field set and visual language so the flow
 * feels familiar. Adds a prominent "This is not a custody evaluation"
 * strip to the top of the dialog so both the sender and (through the
 * cover letter) the recipient are reminded of the report's scope.
 *
 * Parent controls open/close via `open` + `onClose` and provides an
 * `onSend(payload)` handler. `sending` shows a spinner.
 */
import { useState } from "react";
import { X, Send, Loader2, ShieldAlert, ShieldCheck } from "lucide-react";
import { requestPreShareConsent } from "@/components/PreShareConsentDialog";

const ROLES = [
  { key: "mediator",                    label: "Mediator" },
  { key: "parent_facilitator_ad_litem", label: "Parent Facilitator Ad Litem" },
  { key: "trial_court",                 label: "Trial Court" },
  { key: "attorney",                    label: "Family Law Attorney" },
  { key: "therapist",                   label: "Therapist / Counsellor" },
  { key: "other",                       label: "Other" },
];

// Variant-specific framing text. Kept in one place so the strings stay
// coherent and legally accurate across both surfaces.
const VARIANTS = {
  report: {
    eyebrow:            "Send Joint Report",
    disclaimerTone:     "danger",
    disclaimerTitle:    "This is not a custody evaluation.",
    disclaimerBody:
      "The PDF and covering email both make clear this is a preparation " +
      "resource compiled from both parents\u2019 self-reported answers.",
    scopeTitle:         "Joint report scope",
    scopeSubtitle:
      "Both parents consented via an active Compare share \u2014 this " +
      "report aggregates both perspectives without evaluating either.",
    intro:
      "We\u2019ll email your recipient the Joint Co-Parenting Summary PDF. " +
      "They can reply directly to your email.",
  },
  agreement: {
    eyebrow:            "Send Joint Agreement Draft",
    disclaimerTone:     "warn",
    disclaimerTitle:    "This is a draft for discussion.",
    disclaimerBody:
      "The PDF and covering email both make clear this is a draft \u2014 " +
      "not a signed agreement, court order, or custody recommendation.",
    scopeTitle:         "Joint agreement scope",
    scopeSubtitle:
      "Merged deterministically from both parents\u2019 individual " +
      "agreement drafts, unlocked by the active Compare share you both " +
      "consented to.",
    intro:
      "We\u2019ll email your recipient the Co-Parenting Agreement " +
      "Draft PDF. They can reply directly to your email.",
  },
};

export default function JointReportEmailDialog({
  open, onClose, onSend, sending,
  parentAName = "", parentBName = "",
  variant = "report",
  testIdPrefix = "joint-report-email",
}) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("mediator");
  const [message, setMessage] = useState("");

  if (!open) return null;
  const v = VARIANTS[variant] || VARIANTS.report;
  const isWarn = v.disclaimerTone === "warn";
  const emailOk = /\S+@\S+\.\S+/.test(email.trim());
  const submit = async () => {
    if (!emailOk || sending) return;
    // HB 300 + Privacy Policy consent gate — the six "YOU CONTROL THIS
    // REPORT" bullets. Skip if the parent cancels.
    const label = variant === "agreement"
      ? "the Co-Parenting Agreement"
      : "the Joint Co-Parenting Summary for Professional Review";
    const ok = await requestPreShareConsent(label);
    if (!ok) return;
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
      data-testid={`${testIdPrefix}-dialog`}
      role="dialog"
      aria-modal="true"
      aria-labelledby={`${testIdPrefix}-title`}
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-3xl bg-white shadow-2xl border border-[#E5E0EE] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-3 px-6 sm:px-7 pt-6">
          <div>
            <div className="text-[11px] uppercase tracking-[0.22em] text-[#3D1A78] font-bold mb-1">
              {v.eyebrow}
            </div>
            <h3
              id={`${testIdPrefix}-title`}
              className="font-bold text-xl text-[#1A1330] leading-tight"
            >
              Email directly to the recipient
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid={`${testIdPrefix}-close`}
            aria-label="Close"
            className="w-9 h-9 rounded-full grid place-items-center bg-[#F8F7FC] hover:bg-[#EFE9F9] text-[#4B4567]"
          >
            <X size={16} />
          </button>
        </div>

        <div className="px-6 sm:px-7 py-5 space-y-4">
          {/* Tone-appropriate disclaimer strip — matches the language used
              in the covering email itself. */}
          <div
            className={`rounded-2xl border p-3 flex gap-2 items-start ${
              isWarn
                ? "border-[#E4D8B8] bg-[#FFF6D8]"
                : "border-[#EFB4B4] bg-[#FCEDEB]"
            }`}
          >
            {isWarn
              ? <ShieldCheck size={16} className="text-[#8A6B12] mt-0.5 shrink-0" />
              : <ShieldAlert size={16} className="text-[#B02A2A] mt-0.5 shrink-0" />}
            <div className="text-[12px] text-[#1A1330] leading-relaxed">
              <strong className={isWarn ? "text-[#8A6B12]" : "text-[#B02A2A]"}>
                {v.disclaimerTitle}
              </strong>{" "}
              {v.disclaimerBody}
            </div>
          </div>

          <div className="rounded-2xl border border-[#E5E0EE] bg-[#F8F7FC] p-3">
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
              {v.scopeTitle}
            </div>
            <div
              className="text-sm text-[#1A1330] font-semibold leading-tight"
              data-testid={`${testIdPrefix}-parents`}
            >
              {parentAName || "Parent A"} <span className="text-[#6E6787] mx-1">·</span> {parentBName || "Parent B"}
            </div>
            <div className="text-[11px] text-[#4B4567] mt-1">
              {v.scopeSubtitle}
            </div>
          </div>

          <p className="text-sm text-[#4B4567] leading-relaxed">
            {v.intro}
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
                  data-testid={`${testIdPrefix}-role-${r.key}`}
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
              data-testid={`${testIdPrefix}-input`}
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
              autoComplete="email"
              required
            />
          </div>

          <div>
            <label className="block text-[11px] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Recipient name <span className="text-[#6E6787] font-normal normal-case tracking-normal">· optional</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Jamie Rivera"
              data-testid={`${testIdPrefix}-name-input`}
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
            />
          </div>

          <div>
            <label className="block text-[11px] uppercase tracking-[0.18em] text-[#3D1A78] font-bold mb-1">
              Short message <span className="text-[#6E6787] font-normal normal-case tracking-normal">· optional</span>
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder={
                variant === "agreement"
                  ? "Anything you want them to know before reading the joint draft…"
                  : "Anything you want them to know before reading the joint report…"
              }
              rows={3}
              maxLength={1200}
              data-testid={`${testIdPrefix}-message-input`}
              className="w-full rounded-xl border border-[#E5E0EE] bg-white px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30 resize-none"
            />
          </div>

          <p className="text-[11px] text-[#6A5799] italic">
            Reply-to is set to your email so the recipient can respond
            directly.{" "}
            {variant === "agreement"
              ? "Every clause appears verbatim under the parent who proposed it — this is a draft for discussion, never a signed agreement."
              : "Every row of the joint report is phrased in neutral, non-adjudicative language — informational only, not a custody evaluation."}
          </p>
        </div>

        <div className="flex items-center justify-end gap-2 px-6 sm:px-7 pb-6 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={sending}
            data-testid={`${testIdPrefix}-cancel`}
            className="rounded-full bg-white border border-[#E5E0EE] text-[#1A1330] px-4 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC] disabled:opacity-60"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={!emailOk || sending}
            data-testid={`${testIdPrefix}-send`}
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white px-5 py-2.5 text-sm font-semibold disabled:opacity-60"
          >
            {sending ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
            {sending
              ? "Sending…"
              : variant === "agreement" ? "Send draft" : "Send report"}
          </button>
        </div>
      </div>
    </div>
  );
}
