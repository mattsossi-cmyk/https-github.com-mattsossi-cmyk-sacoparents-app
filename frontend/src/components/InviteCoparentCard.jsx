import React, { useEffect, useState } from "react";
import { Loader2, Mail, RotateCw, CheckCircle2, Send, Users } from "lucide-react";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const STATUS_META = {
  pending: { label: "Sent", chip: "bg-[#F0EDF7] text-[#4B4567]" },
  opened: { label: "Opened", chip: "bg-[#D5F2F2] text-[#0E7A7A]" },
  signed_up: { label: "Joined", chip: "bg-[#DEF5E0] text-[#1F6E2E]" },
};

function fmtDate(iso) {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
  } catch {
    return null;
  }
}

/**
 * Reusable "Invite your co-parent" card. Drop into Dashboard + Summary.
 * Self-contained: handles email input, send, status list, resend.
 */
export default function InviteCoparentCard({ variant = "dashboard" }) {
  const [invites, setInvites] = useState([]);
  const [rateLimit, setRateLimit] = useState(3);
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [loading, setLoading] = useState(true);
  const [resendingId, setResendingId] = useState(null);

  const refresh = async () => {
    try {
      const r = await api.get("/invites/coparent");
      setInvites(r.data.invites || []);
      setRateLimit(r.data.rate_limit_per_day || 3);
    } catch (e) {
      logError("load invites failed", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleSend = async () => {
    const v = email.trim().toLowerCase();
    if (!v || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) {
      setError("Please enter a valid email address.");
      return;
    }
    setError(null);
    setSuccess(null);
    setSending(true);
    try {
      const r = await api.post("/invites/coparent", { email: v });
      setSuccess(
        r.data.resent
          ? `Resent the invite to ${v}.`
          : `Invite sent to ${v}. They'll get an email shortly.`
      );
      setEmail("");
      await refresh();
    } catch (e) {
      setError(e?.response?.data?.detail || "Could not send invite. Please try again.");
    } finally {
      setSending(false);
    }
  };

  const handleResend = async (inviteId) => {
    setResendingId(inviteId);
    setError(null);
    setSuccess(null);
    try {
      await api.post(`/invites/coparent/resend/${inviteId}`);
      setSuccess("Invite resent.");
      await refresh();
    } catch (e) {
      setError(e?.response?.data?.detail || "Could not resend invite.");
    } finally {
      setResendingId(null);
    }
  };

  const usedToday = invites.filter((i) => {
    if (!i.created_at) return false;
    try {
      const ageHrs = (Date.now() - new Date(i.created_at).getTime()) / 36e5;
      return ageHrs <= 24;
    } catch {
      return false;
    }
  }).length;
  const remaining = Math.max(0, rateLimit - usedToday);

  return (
    <div className="card-soft p-6 sm:p-7" data-testid="invite-coparent-card">
      <div className="flex items-start gap-4">
        <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] grid place-items-center text-white shadow-sm shrink-0">
          <Users size={20} strokeWidth={2.2} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="eyebrow mb-1.5">Prep together</div>
          <h3 className="font-serif text-xl sm:text-2xl text-[#1A1330] leading-snug">
            {variant === "summary"
              ? "Invite your co-parent to prep too"
              : "Invite your co-parent"}
          </h3>
          <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">
            {variant === "summary"
              ? "Now that your prep is complete, give your co-parent the same head start. Their answers stay completely private — you'll never see them."
              : "Send them a link to prep for mediation in their own private workspace. You'll never see each other's answers."}
          </p>
        </div>
      </div>

      <div className="mt-6 flex flex-col sm:flex-row gap-2">
        <div className="relative flex-1">
          <Mail
            size={16}
            className="absolute left-4 top-1/2 -translate-y-1/2 text-[#857E9C]"
          />
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="co-parent@email.com"
            data-testid="invite-coparent-email-input"
            disabled={sending || remaining === 0}
            className="w-full pl-11 pr-4 py-3 rounded-2xl border border-[#E5E0EE] text-sm focus:outline-none focus:border-[#3D1A78] disabled:bg-[#F0EDF7]/40"
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSend();
            }}
          />
        </div>
        <button
          type="button"
          onClick={handleSend}
          disabled={sending || remaining === 0}
          data-testid="invite-coparent-send-button"
          className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-2xl bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white font-semibold text-sm shadow-sm hover:shadow-md transition-all disabled:opacity-60 disabled:cursor-not-allowed shrink-0"
        >
          {sending ? <Loader2 className="animate-spin" size={16} /> : <Send size={16} />}
          Send invite
        </button>
      </div>

      {remaining < rateLimit && (
        <p className="text-[11px] text-[#857E9C] mt-2">
          {remaining} of {rateLimit} invites left today.
        </p>
      )}

      {error && (
        <div
          className="mt-3 rounded-xl bg-[#FCE3DC] text-[#9A3A23] px-4 py-2.5 text-xs"
          data-testid="invite-coparent-error"
        >
          {error}
        </div>
      )}
      {success && (
        <div
          className="mt-3 rounded-xl bg-[#DEF5E0] text-[#1F6E2E] px-4 py-2.5 text-xs flex items-center gap-2"
          data-testid="invite-coparent-success"
        >
          <CheckCircle2 size={14} /> {success}
        </div>
      )}

      {loading ? null : invites.length > 0 ? (
        <div className="mt-6 pt-5 border-t border-[#E5E0EE]" data-testid="invite-coparent-list">
          <div className="eyebrow mb-3">Sent invites</div>
          <ul className="space-y-2">
            {invites.map((inv) => {
              const meta = STATUS_META[inv.status] || STATUS_META.pending;
              const created = fmtDate(inv.created_at);
              const isResending = resendingId === inv.invite_id;
              return (
                <li
                  key={inv.invite_id}
                  className="flex items-center justify-between gap-3 p-3 rounded-xl bg-[#FBFAFD] border border-[#E5E0EE]"
                  data-testid={`invite-row-${inv.invite_id}`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-[#1A1330] truncate">
                      {inv.invitee_email}
                    </div>
                    <div className="text-[11px] text-[#857E9C] mt-0.5">
                      Sent {created || "—"}
                    </div>
                  </div>
                  <span
                    className={`text-[10px] uppercase tracking-[0.12em] px-2 py-0.5 rounded-full ${meta.chip}`}
                  >
                    {meta.label}
                  </span>
                  {inv.status !== "signed_up" && (
                    <button
                      type="button"
                      onClick={() => handleResend(inv.invite_id)}
                      disabled={isResending}
                      data-testid={`invite-resend-${inv.invite_id}`}
                      className="text-[11px] font-medium text-[#3D1A78] hover:underline disabled:opacity-50 inline-flex items-center gap-1"
                    >
                      {isResending ? (
                        <Loader2 size={12} className="animate-spin" />
                      ) : (
                        <RotateCw size={12} />
                      )}
                      Resend
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
