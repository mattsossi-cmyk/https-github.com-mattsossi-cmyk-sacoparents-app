import React from "react";

import { useCheckinLink } from "../../lib/useCheckinLink";

// Small Self Journey "Quick check-in" link: opens the same Family check-in on SACOparentsAlign.
export function SafetyScreenLink({ alignUrl }) {
  const href = useCheckinLink(alignUrl);
  return (
    <a
      href={href || undefined}
      aria-disabled={!href}
      target="_blank"
      rel="noopener noreferrer"
      data-testid="self-safety-screen-link"
      aria-label="Quick check-in (opens SACOparentsAlign in a new tab)"
      className={`inline-flex items-center gap-1.5 min-h-9 px-3 py-1.5 rounded-full border border-[#E5E0EE] bg-white text-[#3D1A78] text-xs font-semibold hover:bg-[#F5F1FB] transition-colors ${href ? "" : "opacity-60 pointer-events-none"}`}
    >
      <i className="fa-solid fa-clipboard-check" aria-hidden="true"></i>
      Quick check-in
      <i className="fa-solid fa-arrow-up-right-from-square text-[0.625rem]" aria-hidden="true"></i>
    </a>
  );
}
