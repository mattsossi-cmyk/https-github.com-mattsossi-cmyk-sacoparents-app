import { Link } from "react-router-dom";
import { Sparkles, ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";

/**
 * DemoModeBanner
 *
 * Shown only to guest (demo-mode) users. Reassures them that their work is
 * being saved for the full 365-day demo window, and offers a one-click path
 * to convert into a permanent account.
 *
 * Calculates days remaining from the current user's `guest_expires_at` and
 * degrades gracefully if the field is missing.
 */
function daysRemaining(expiresAt) {
  if (!expiresAt) return null;
  try {
    const now = Date.now();
    const then = new Date(expiresAt).getTime();
    const diff = then - now;
    if (Number.isNaN(diff) || diff <= 0) return 0;
    return Math.max(1, Math.round(diff / (1000 * 60 * 60 * 24)));
  } catch {
    return null;
  }
}

export default function DemoModeBanner() {
  const { user } = useAuth();
  if (!user?.is_guest) return null;

  const days = daysRemaining(user.guest_expires_at);

  return (
    <section
      className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#3D1A78] via-[#5E2DB5] to-[#2DB5B5] text-white p-5 sm:p-6 shadow-lg mb-6"
      data-testid="demo-mode-banner"
    >
      <div className="absolute -top-16 -right-16 w-52 h-52 rounded-full bg-white/10" />
      <div className="relative flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="shrink-0 w-12 h-12 rounded-full bg-white/15 grid place-items-center">
          <Sparkles size={22} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[0.625rem] uppercase tracking-[0.22em] font-bold">
              You&apos;re in demo mode
            </span>
            <ShieldCheck size={12} className="opacity-80" aria-hidden />
          </div>
          <div
            className="font-serif text-xl sm:text-2xl leading-snug"
            data-testid="demo-mode-banner-headline"
          >
            Your work is saved for{" "}
            <span className="font-bold" data-testid="demo-mode-banner-days">
              {days ?? 365} days
            </span>
            .
          </div>
          <p className="text-sm text-white/90 mt-1 max-w-xl">
            Nothing you write is lost. Sign up anytime to keep your progress
            forever — same account, same data, no re-entry.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 sm:justify-end">
          <Link
            to="/login"
            className="px-5 py-2.5 rounded-full border border-white/50 text-white text-sm font-semibold hover:bg-white/10 whitespace-nowrap"
            data-testid="demo-mode-banner-signin-btn"
          >
            Sign in to my account
          </Link>
          <Link
            to="/claim"
            className="px-5 py-2.5 rounded-full bg-white text-[#3D1A78] text-sm font-semibold hover:bg-white/90 whitespace-nowrap"
            data-testid="demo-mode-banner-claim-btn"
          >
            Keep it forever →
          </Link>
        </div>
      </div>
    </section>
  );
}
