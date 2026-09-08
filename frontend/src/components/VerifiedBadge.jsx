import { BadgeCheck } from "lucide-react";

export function VerifiedBadge({ testId = "credentials-verified-badge", className = "" }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full bg-align-green/15 text-align-green text-[11px] font-semibold uppercase tracking-wider px-2.5 py-0.5 ${className}`} title="License / credentials verified by SA CoParents" data-testid={testId}>
      <BadgeCheck className="h-3.5 w-3.5" /> Credentials Verified
    </span>
  );
}
