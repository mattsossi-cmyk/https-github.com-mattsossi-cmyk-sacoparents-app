import React from "react";
import { KeyRound } from "lucide-react";

export const PASTE_GUARD_TEXT =
  "Secrets go only in each app's Secrets tab or a password manager such as Keeper. Never paste one into a chat, email, ticket or document. If one is ever pasted, treat it as burned and replace it.";

// Reminder shown to admins wherever webhook secrets come up.
export function SecretPasteGuard({ className = "", testid = "secret-paste-guard" }) {
  return (
    <p role="note" data-testid={testid} className={`flex items-start gap-2 rounded-xl border border-[#D9D3EA] bg-[#F8F7FC] px-3 py-2 text-xs text-[#3B3552] ${className}`}>
      <KeyRound size={14} className="mt-0.5 shrink-0 text-[#3D1A78]" aria-hidden="true" />
      <span>{PASTE_GUARD_TEXT}</span>
    </p>
  );
}
