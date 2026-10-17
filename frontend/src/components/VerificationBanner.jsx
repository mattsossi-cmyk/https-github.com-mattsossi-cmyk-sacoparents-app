import React, { useState } from "react";
import { MailCheck, X, Send, KeyRound, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { logError } from "../lib/logger";
import CodeInput from "./CodeInput";

const DISMISS_KEY = "sac_verify_banner_dismissed_at";
const DISMISS_HOURS = 24;

export default function VerificationBanner() {
  const { user, checkAuth } = useAuth();
  const [sending, setSending] = useState(false);
  const [mode, setMode] = useState("idle"); // idle | code
  const [codeSending, setCodeSending] = useState(false);
  const [codeConfirming, setCodeConfirming] = useState(false);
  const [code, setCode] = useState("");
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
        err?.response?.data?.detail || "Could not send verification email.",
      );
    } finally {
      setSending(false);
    }
  };

  const openCodeMode = async () => {
    // Kick off code delivery, then flip the banner into code-entry state.
    setCodeSending(true);
    try {
      const { data } = await api.post("/auth/verify-email/send-code", {
        email: user.email,
      });
      if (data?.already_verified) {
        toast.success("Email already verified.");
        await checkAuth?.();
        return;
      }
      if (data?.sent) {
        toast.success("6-digit code sent. Check your inbox.");
      } else {
        toast.message("Code generated (email not configured)", {
          description:
            "Check the backend magic_links collection to retrieve the code in preview environments.",
          duration: 8000,
        });
      }
      setMode("code");
    } catch (err) {
      logError("verify send-code failed", err);
      toast.error(err?.response?.data?.detail || "Could not send code.");
    } finally {
      setCodeSending(false);
    }
  };

  const confirmCode = async (fullCode) => {
    const codeToSend = fullCode || code;
    if (codeToSend.length !== 6) return;
    setCodeConfirming(true);
    try {
      await api.post("/auth/verify-email/confirm-code", {
        email: user.email,
        code: codeToSend,
      });
      toast.success("Email verified.");
      try {
        await checkAuth?.();
      } catch (e) {
        logError("verify checkAuth after code failed", e);
      }
      // Component will unmount because user.email_verified flips true.
    } catch (err) {
      logError("verify confirm-code failed", err);
      const detail = err?.response?.data?.detail;
      toast.error(detail || "Invalid or expired code.");
      setCode("");
    } finally {
      setCodeConfirming(false);
    }
  };

  if (mode === "code") {
    return (
      <div
        className="card-soft p-5 border-l-4 border-[#3D1A78] bg-gradient-to-r from-[#EFE9F9] to-white"
        data-testid="verification-banner-code-mode"
      >
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-full bg-white grid place-items-center text-[#3D1A78] shrink-0">
            <KeyRound size={18} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-[#1A1330] text-sm">
              Enter the 6-digit code we just emailed
            </div>
            <div className="text-xs text-[#4B4567] mt-0.5">
              Sent to{" "}
              <span className="text-[#1A1330] font-medium">{user.email}</span>.
              Expires in 15 minutes.
            </div>
          </div>
          <button
            onClick={() => {
              setMode("idle");
              setCode("");
            }}
            className="w-8 h-8 grid place-items-center rounded-full text-[#6E6787] hover:bg-[#F0EDF7] shrink-0"
            aria-label="Cancel"
            data-testid="verification-cancel-code-button"
          >
            <X size={14} />
          </button>
        </div>

        <div className="mt-4">
          <CodeInput
            value={code}
            onChange={setCode}
            onComplete={(full) => confirmCode(full)}
            disabled={codeConfirming}
            testidPrefix="verify-code"
          />
        </div>

        <div className="mt-4 flex items-center justify-between text-xs">
          <button
            onClick={openCodeMode}
            disabled={codeSending}
            className="text-[#3D1A78] font-semibold hover:underline disabled:opacity-60"
            data-testid="verification-resend-code-button"
          >
            {codeSending ? "Resending…" : "Resend code"}
          </button>
          <button
            onClick={() => confirmCode()}
            disabled={codeConfirming || code.length !== 6}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#3D1A78] text-white text-xs font-semibold hover:bg-[#2C1259] disabled:opacity-60"
            data-testid="verification-confirm-code-button"
          >
            <CheckCircle2 size={12} />
            {codeConfirming ? "Verifying…" : "Verify email"}
          </button>
        </div>
      </div>
    );
  }

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
          <span className="text-[#1A1330] font-medium">{user.email}</span>. Use
          the link, or enter a 6-digit code instead.
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0 flex-wrap">
        <button
          onClick={openCodeMode}
          disabled={codeSending}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#3D1A78] text-[#3D1A78] text-xs font-semibold hover:bg-[#F1EEF7] disabled:opacity-60"
          data-testid="verification-enter-code-button"
        >
          <KeyRound size={12} />
          {codeSending ? "Sending code…" : "Enter code instead"}
        </button>
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
          className="w-8 h-8 grid place-items-center rounded-full text-[#6E6787] hover:bg-[#F0EDF7]"
          aria-label="Dismiss"
          data-testid="verification-dismiss-button"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}
