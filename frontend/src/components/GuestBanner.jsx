import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles, X } from "lucide-react";
import { useAuth } from "../context/AuthContext";

function formatRemaining(target) {
  if (!target) return null;
  const diff = new Date(target).getTime() - Date.now();
  if (diff <= 0) return "less than a minute";
  const hrs = Math.floor(diff / 3_600_000);
  const mins = Math.floor((diff % 3_600_000) / 60_000);
  if (hrs >= 1) return `${hrs}h ${mins}m`;
  return `${mins}m`;
}

export default function GuestBanner() {
  const { user } = useAuth();
  const [remaining, setRemaining] = useState(() =>
    formatRemaining(user?.guest_expires_at)
  );
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (!user?.is_guest) return;
    setRemaining(formatRemaining(user.guest_expires_at));
    const id = setInterval(() => {
      setRemaining(formatRemaining(user.guest_expires_at));
    }, 60_000);
    return () => clearInterval(id);
  }, [user]);

  if (!user?.is_guest || dismissed) return null;

  return (
    <div
      className="bg-brand-gradient text-white px-4 py-2.5 flex items-center justify-center gap-3 text-[13px] sm:text-sm"
      data-testid="guest-banner"
    >
      <Sparkles size={14} className="shrink-0" />
      <span className="text-center">
        You're using a 24-hour demo — <strong>{remaining || "expires soon"}</strong> left.{" "}
        <Link
          to="/claim"
          className="underline font-bold ml-1"
          data-testid="guest-banner-save-link"
        >
          Save my work →
        </Link>
      </span>
      <button
        type="button"
        onClick={() => setDismissed(true)}
        className="ml-auto opacity-70 hover:opacity-100"
        aria-label="Dismiss"
        data-testid="guest-banner-dismiss"
      >
        <X size={14} />
      </button>
    </div>
  );
}
