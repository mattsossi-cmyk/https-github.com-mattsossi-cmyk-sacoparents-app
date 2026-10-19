import React from "react";
import { Check, Clock, X } from "lucide-react";

const TONES = {
  thanks: { box: "border-emerald-200 bg-emerald-50 text-emerald-900", btn: "text-emerald-800 hover:bg-emerald-100 focus-visible:outline-emerald-700", Icon: Check },
  reminder: { box: "border-[#e0d5ed] bg-[#f8f4fd] text-[#3b1566]", btn: "text-[#4a2574] hover:bg-[#efe6fa] focus-visible:outline-[#4a2574]", Icon: Clock },
};

function CardNote({ tone, testid, onClose, children }) {
  const t = TONES[tone];
  return (
    <div role="status" data-testid={testid} className={`mt-4 flex items-center gap-2.5 rounded-xl border pl-3.5 pr-1 py-1 text-sm animate-in fade-in duration-500 ${t.box}`}>
      <t.Icon size={16} className="shrink-0" aria-hidden="true" />
      <p className="flex-1 py-2">{children}</p>
      <button
        type="button"
        onClick={onClose}
        data-testid={`${testid}-close`}
        aria-label="Close message"
        className={`shrink-0 w-11 h-11 grid place-items-center rounded-full transition-colors focus-visible:outline focus-visible:outline-2 ${t.btn}`}
      >
        <X size={16} aria-hidden="true" />
      </button>
    </div>
  );
}

export const ThanksNote = ({ testid, onClose }) => (
  <CardNote tone="thanks" testid={`${testid}-thanks`} onClose={onClose}>
    Thanks, your check-in is done. There&apos;s nothing else you need to do for it.
  </CardNote>
);

export const ReminderNote = ({ testid, onClose }) => (
  <CardNote tone="reminder" testid={`${testid}-reminder`} onClose={onClose}>
    Your Family check-in is still open. It only takes a few minutes, whenever you&apos;re ready.
  </CardNote>
);
