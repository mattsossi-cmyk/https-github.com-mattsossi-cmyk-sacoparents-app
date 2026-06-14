import React, { useState } from "react";
import { MailCheck, X, Send } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const DISMISS_KEY = "sac_verify_banner_dismissed_at";
const DISMISS_HOURS = 24;

export default function VerificationBanner() {
  const { user, checkAuth } = useAuth();
  const [sending, setSending] = useState(false);
  const [dismissed, setDismissed] = useState(() => {
    try {
      const raw = window.localStorage.getItem(DISMISS_KEY);
      if (!raw) return false;
      const at = Number(raw);
      if (!Number.isFinite(at)) return false;
      return Date.now() - at < DISMISS_HOURS * 60 * 60 * 1000;
    } catch (_e) {
      return false;
    }
  });

  if (!user) return null;
  if (user.is_guest) return null;
  if (user.email_verified) return null;
  if (dismissed) return null;

  const dismiss = () => {
    try {
      window.localStorage.setItem(DISMISS_KEY, String(Date.now()));
    } catch (_e) {
      /* private mode — best-effort only */
    }
    setDismissed(true);
  };

  const resend = async () => {
    setSending(true);
    try {
      const { data } = await api.post("/auth/verify-email/send");
      if (data?.already_verified) {
        toast.success("Email already verified.");
        await checkAuth?.();
      } else if (data?.sent) {
        toast.success("Verification email sent. Check your inbox.");
      } else {
        toast.message("Verification link generated", {
          description:
            "Email isn't configured in this environment. Check the backend logs for the link.",
          duration: 8000,
        });
      }
    } catch (err) {
      logError("verify resend failed", err);
      toast.error(
        err?.response?.data?.detail || "Could not send verification email."
      );
    } finally {
      setSending(false);
    }
  };

  return (
    <div
      className="card-soft p-4 sm:p-5 border-l-4 border-[#3D1A78] bg-gradient-to-r from-[#EFE9F9] to-white flex flex-col sm:flex-row sm:items-center gap-3"
      data-testid="verification-banner"
    >
      <div className="w-10 h-10 rounded-full bg-white grid place-items-center text-[#3D1A78] shrink-0">
        <MailCheck size={18} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-medium text-[#1A1330] text-sm">
          Confirm your email to keep your account secure
        </div>
        <div className="text-xs text-[#4B4567] mt-0.5">
          We sent a confirmation link to{" "}
          <span className="text-[#1A1330] font-medium">{user.email}</span>. The
          link expires in 24 hours.
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <button
          onClick={resend}
          disabled={sending}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#3D1A78] text-white text-xs font-semibold hover:bg-[#2C1259] disabled:opacity-60"
          data-testid="verification-resend-button"
        >
          <Send size={12} />
          {sending ? "Sending…" : "Resend email"}
        </button>
        <button
          onClick={dismiss}
          className="w-8 h-8 grid place-items-center rounded-full text-[#857E9C] hover:bg-[#F0EDF7]"
          aria-label="Dismiss"
          data-testid="verification-dismiss-button"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}
