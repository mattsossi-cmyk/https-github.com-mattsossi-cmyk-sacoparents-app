import React from "react";
import { Link } from "react-router-dom";
import { Clock, BookmarkPlus } from "lucide-react";
import { useAuth } from "../context/AuthContext";

/**
 * Demo (guest) session countdown banner. Shown only when the active session
 * is a guest. Pulls expiry from `user.guest_expires_at` (ISO string the
 * backend already exposes via UserPublic).
 *
 * Tone: friendly, not nagging. Gets progressively more visible the closer
 * the user gets to expiry.
 */
function daysLeft(iso) {
  if (!iso) return null;
  try {
    const ms = new Date(iso).getTime() - Date.now();
    if (Number.isNaN(ms)) return null;
    return Math.max(0, Math.ceil(ms / 86400000));
  } catch {
    return null;
  }
}

function bandStyle(days) {
  if (days == null) return "bg-[#EFE9F9] text-[#3D1A78] border-[#3D1A78]/15";
  if (days <= 7) return "bg-[#FCE3DC] text-[#9A3A23] border-[#9A3A23]/20";
  if (days <= 30) return "bg-[#FFF1D6] text-[#7A4A05] border-[#7A4A05]/15";
  return "bg-[#EFE9F9] text-[#3D1A78] border-[#3D1A78]/15";
}

export default function GuestBanner() {
  const { user } = useAuth();
  if (!user?.is_guest) return null;
  const remaining = daysLeft(user.guest_expires_at);
  const styles = bandStyle(remaining);

  const label =
    remaining == null
      ? "You're exploring in demo mode"
      : remaining <= 0
      ? "Your demo has expired"
      : remaining === 1
      ? "Demo expires tomorrow"
      : `Demo expires in ${remaining} days`;

  return (
    <div
      className={`border-b ${styles}`}
      data-testid="guest-banner"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2 flex items-center justify-between gap-3 text-xs sm:text-sm">
        <div className="flex items-center gap-2 min-w-0">
          <Clock size={14} className="shrink-0 opacity-80" />
          <span className="font-medium truncate" data-testid="guest-banner-countdown">
            {label}
          </span>
          <span className="hidden sm:inline opacity-75">
            · Save your work to keep it forever
          </span>
        </div>
        <Link
          to="/claim"
          data-testid="guest-banner-claim-link"
          className="shrink-0 inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/70 hover:bg-white font-semibold text-[0.6875rem] sm:text-xs transition-colors"
        >
          <BookmarkPlus size={12} />
          Save my work
        </Link>
      </div>
    </div>
  );
}
