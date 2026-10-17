import React from "react";
import { ShieldCheck } from "lucide-react";

import { PrivacyLinks } from "./PrivacyLinks";

const POINTS = [
  "Your answers are private to your account. Nothing is shared unless you choose a person and tap Send.",
  "One exception: if you accept a professional's case invitation or court code, they see whether each step they asked for is done, with dates, never your answers.",
  "Emails never carry your documents. The person you send to opens them with a one-time code.",
  "No ad trackers and no session recordings.",
];

// Short "Your privacy" section under the sign-in card.
export function LoginPrivacyBox() {
  return (
    <section data-testid="login-privacy-box" className="mt-6 rounded-3xl border border-[#E5E0EE] bg-white/75 backdrop-blur-sm p-5 sm:p-6">
      <div className="flex items-center gap-2 mb-3">
        <ShieldCheck size={16} className="text-[#3D1A78]" />
        <h2 className="text-sm font-bold text-[#1A1330] tracking-tight">Your privacy</h2>
      </div>
      <ul className="space-y-2 mb-4">
        {POINTS.map((p, i) => (
          <li key={p} data-testid={`login-privacy-point-${i}`} className="flex items-start gap-2 text-[13px] text-[#4B4567] leading-relaxed">
            <i className="fa-solid fa-check text-[#0F7676] text-[11px] mt-1" aria-hidden="true"></i>
            <span>{p}</span>
          </li>
        ))}
      </ul>
      <PrivacyLinks tp="login-privacy" only={["notice", "pros"]} />
    </section>
  );
}
