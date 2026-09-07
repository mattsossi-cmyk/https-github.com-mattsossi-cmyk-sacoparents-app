/**
 * WeeklyDigestToggle.jsx — one-tap on/off switch for the Monday
 * analytics email. Reads/writes
 * `/api/professional/joint-alignment/digest-pref` with an
 * optimistic UI update.
 *
 * Rendered on the top-right actions row of
 * `/professional/joint-alignment/mine` beside "Refresh" and
 * "New case" so it's immediately available where mediators see
 * their analytics.
 */
import React, { useEffect, useState } from "react";
import { Mail, MailX, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { api } from "../../lib/api";
import { logError } from "../../lib/logger";

export default function WeeklyDigestToggle() {
  const [optedIn, setOptedIn] = useState(null); // null = unknown until loaded
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/professional/joint-alignment/digest-pref")
      .then((r) => setOptedIn(!!r.data?.opted_in))
      .catch((err) => {
        logError("digest pref load failed", err);
        // Default to true so the caller isn't confused by a
        // silent unset toggle — this is a soft-safe default.
        setOptedIn(true);
      });
  }, []);

  const toggle = async () => {
    if (optedIn === null) return;
    const next = !optedIn;
    setBusy(true);
    setOptedIn(next); // optimistic
    try {
      await api.post("/professional/joint-alignment/digest-pref", {
        opted_in: next,
      });
      toast.success(
        next
          ? "Weekly digest re-enabled — you'll receive a Monday snapshot."
          : "Weekly digest paused — you won't receive Monday snapshots.",
      );
    } catch (err) {
      logError("digest pref update failed", err);
      setOptedIn(!next); // rollback
      toast.error("Could not update your preference. Try again.");
    } finally {
      setBusy(false);
    }
  };

  if (optedIn === null) {
    // Skeleton — matches the height of the sibling refresh button
    // so the header layout doesn't jump when the pref loads.
    return (
      <div
        className="w-[132px] h-[28px] rounded-full bg-[#F5F1FB] animate-pulse"
        data-testid="pj-digest-toggle-skeleton"
      />
    );
  }

  const Icon = optedIn ? Mail : MailX;
  const label = optedIn ? "Weekly digest: On" : "Weekly digest: Off";
  return (
    <button
      type="button"
      onClick={toggle}
      disabled={busy}
      aria-pressed={optedIn}
      title={
        optedIn
          ? "Click to pause the Monday analytics email."
          : "Click to receive the Monday analytics email again."
      }
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors disabled:opacity-60 ${
        optedIn
          ? "border-[#B5DFC5] text-[#1F5C3B] hover:bg-[#EAF6EE]"
          : "border-[#E5E0EE] text-[#4B4567] hover:bg-[#F5F1FB]"
      }`}
      data-testid="pj-digest-toggle"
      data-opted-in={optedIn ? "true" : "false"}
    >
      {busy ? <Loader2 size={12} className="animate-spin" /> : <Icon size={12} />}
      {label}
    </button>
  );
}
