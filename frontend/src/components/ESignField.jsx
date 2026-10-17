import React from "react";

// Optional typed e-signature for a printable PDF. Returns a name only once the parent ticks consent.
export const esignValue = (name, agreed) => (agreed && name.trim().length >= 2 ? name.trim() : null);

export function ESignField({ testid, name, onName, agreed, onAgree }) {
  return (
    <div data-testid={testid} className="rounded-xl border border-purple-200 bg-purple-50/60 p-3 space-y-2 text-left">
      <label className="block">
        <span className="text-[0.75rem] font-bold text-slate-700">
          E-signature <span className="font-normal text-slate-500">(optional)</span>
        </span>
        <input
          type="text"
          data-testid={`${testid}-name`}
          value={name}
          maxLength={120}
          onChange={(e) => onName(e.target.value)}
          placeholder="Type your full legal name"
          className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-purple-300"
        />
      </label>
      <label className="flex items-start gap-2 text-[0.6875rem] text-slate-600 leading-snug cursor-pointer">
        <input type="checkbox" data-testid={`${testid}-consent`} checked={agreed} onChange={(e) => onAgree(e.target.checked)} className="mt-0.5 accent-purple-700" />
        <span>
          I agree that my typed name is my electronic signature on this PDF. The other parent can sign in ink. A notary still needs to see
          you sign in person or through an online notary service.
        </span>
      </label>
    </div>
  );
}
