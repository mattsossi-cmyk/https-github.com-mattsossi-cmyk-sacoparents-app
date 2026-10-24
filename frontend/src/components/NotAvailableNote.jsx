import React from "react";
import { ExternalLink, Info } from "lucide-react";
import { toast } from "sonner";

import { useCheckinLink } from "../lib/useCheckinLink";

export const NOT_AVAILABLE = "This isn't available right now. Safety First on SACOparentsAlign is the next step.";
const ALIGN_URL = process.env.REACT_APP_ALIGN_SITE_URL;

// True for the server's neutral "not available" reply (plain text or {code, message}).
export const isNotAvailable = (detail) => detail === NOT_AVAILABLE || detail?.code === "not_available";

// The only thing a parent with an older saved concerning result sees when an invite or comparison is off.
export function NotAvailableNote({ testid = "not-available-note", className = "" }) {
  const href = useCheckinLink(ALIGN_URL);
  return (
    <div
      data-testid={testid}
      role="status"
      className={`rounded-2xl border border-[#E5E0EE] bg-[#F8F7FC] p-4 flex items-start gap-3 text-sm text-[#1A1330] leading-relaxed ${className}`}
    >
      <Info size={18} className="text-[#3D1A78] shrink-0 mt-0.5" aria-hidden="true" />
      <div>
        <p className="!m-0">{NOT_AVAILABLE}</p>
        <a
          href={href || undefined}
          aria-disabled={!href}
          target="_blank"
          rel="noopener noreferrer"
          data-testid={`${testid}-checkin-link`}
          className={`mt-2 inline-flex items-center gap-1.5 min-h-[44px] font-semibold text-[#3D1A78] underline underline-offset-2 ${href ? "" : "opacity-60 pointer-events-none"}`}
        >
          Open Safety First <ExternalLink size={13} aria-hidden="true" />
        </a>
      </div>
    </div>
  );
}

// Toast for the neutral reply (with the check-in link); returns false for any other error.
export function toastNotAvailable(detail) {
  if (!isNotAvailable(detail)) return false;
  toast(<NotAvailableNote testid="not-available-toast" className="border-0 bg-transparent p-0" />);
  return true;
}
