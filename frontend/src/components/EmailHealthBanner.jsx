import React from "react";
import { AlertTriangle } from "lucide-react";

import { useAuth } from "../context/AuthContext";

/**
 * Shows a one-line alert if Resend told us the user's email bounced
 * or they marked us as spam. These flags are set by the webhook handler.
 */
export default function EmailHealthBanner() {
  const { user } = useAuth();
  if (!user) return null;
  if (user.is_guest) return null;
  if (!user.email_bounced && !user.email_complained) return null;

  const isBounced = !!user.email_bounced;
  const headline = isBounced
    ? "We couldn't deliver to your email address"
    : "This email was reported as spam";
  const body = isBounced
    ? "Please double-check it's correct in your profile, or use a different email — otherwise password resets and reminders won't reach you."
    : "We've stopped sending to this address. If this was a mistake, contact support to clear the flag.";

  return (
    <div
      className="card-soft p-4 sm:p-5 border-l-4 border-[#9A3A23] bg-[#FCE3DC]/40 flex flex-col sm:flex-row sm:items-center gap-3"
      data-testid="email-health-banner"
    >
      <div className="w-10 h-10 rounded-full bg-white grid place-items-center text-[#9A3A23] shrink-0">
        <AlertTriangle size={18} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-medium text-[#1A1330] text-sm">{headline}</div>
        <div className="text-xs text-[#4B4567] mt-0.5">{body}</div>
      </div>
    </div>
  );
}
