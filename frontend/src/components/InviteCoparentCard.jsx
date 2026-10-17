import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Loader2,
  Mail,
  CheckCircle2,
  Send,
  Users,
  ShieldAlert,
  Phone,
  Lock,
  Clock,
} from "lucide-react";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const STATUS_META = {
  pending: { label: "Sent · awaiting response", chip: "bg-[#F0EDF7] text-[#4B4567]" },
  opened: { label: "Opened", chip: "bg-[#D5F2F2] text-[#0E7A7A]" },
  signed_up: { label: "Joined", chip: "bg-[#DEF5E0] text-[#1F6E2E]" },
  expired: { label: "Closed · not accepted", chip: "bg-[#FBE4E1] text-[#8A3A2A]" },
  rejected: { label: "Closed · not accepted", chip: "bg-[#FBE4E1] text-[#8A3A2A]" },
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
 * Reusable "Invite your co-parent" card.
 *
 * Founder guardrails (2026-03-04):
 *   1. IPV / family-violence safety screen must be complete AND Level 3+ before
 *      the invite input is even rendered. Otherwise the card swaps to the
 *      appropriate compassionate state.
 *   2. Only ONE lifetime invitation per inviter. Once used, the form is hidden
 *      and the current status is shown instead — no re-invitations, no
 *      "swap the recipient" trick.
 */
export default function InviteCoparentCard({ variant = "dashboard" }) {
  const [invites, setInvites] = useState([]);
  const [inviteUsed, setInviteUsed] = useState(false);
  const [gate, setGate] = useState(null); // {clear, level, code}
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      const [invitesRes, gateRes] = await Promise.all([
        api.get("/invites/coparent"),
        api.get("/invites/coparent/gate"),
      ]);
      setInvites(invitesRes.data.invites || []);
      setInviteUsed(!!invitesRes.data.invite_used);
      setGate(gateRes.data || null);
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
      await api.post("/invites/coparent", { email: v });
      setSuccess(`Invite sent to ${v}. They'll get an email shortly.`);
      setEmail("");
      await refresh();
    } catch (e) {
      const detail = e?.response?.data?.detail;
      // Server returns a structured object for the 403 gate paths.
      if (detail && typeof detail === "object" && detail.message) {
        setError(detail.message);
      } else {
        setError(detail || "Could not send invite. Please try again.");
      }
    } finally {
      setSending(false);
    }
  };

  const canSend = gate?.clear === true && !inviteUsed;

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

      {loading && (
        <div className="mt-6 flex items-center gap-2 text-sm text-[#4B4567]" data-testid="invite-coparent-loading">
          <Loader2 className="animate-spin" size={14} /> Checking your invite status…
        </div>
      )}

      {/* Gate: safety screen not yet taken */}
      {!loading && gate && !gate.clear && gate.code === "safety_screen_required" && (
        <div
          className="mt-6 rounded-2xl border-2 border-[#F1D9B7] bg-[#FFF6EA] p-4 sm:p-5"
          data-testid="invite-coparent-gate-required"
        >
          <div className="flex items-start gap-3">
            <ShieldAlert size={20} className="text-[#904B0E] shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-serif text-lg text-[#5A3C10]">
                Complete the family-violence safety screen first
              </h4>
              <p className="text-sm text-[#5A3C10]/90 mt-1 leading-relaxed">
                To keep both parents safe, we ask every parent to complete a short
                private safety screen (about 5 minutes) before sending a co-parent
                invitation. Your answers stay private.
              </p>
              <Link
                to="/safety"
                data-testid="invite-coparent-take-safety-link"
                className="mt-3 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#B45F13] text-white text-sm font-semibold hover:brightness-110"
              >
                Take the safety screen
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Gate: safety screen shows FV concerns (Level 1 or 2) */}
      {!loading && gate && !gate.clear && gate.code === "safety_screen_blocked" && (
        <div
          className="mt-6 rounded-2xl border-2 border-[#F1B7B7] bg-[#FDECEC] p-4 sm:p-5"
          data-testid="invite-coparent-gate-blocked"
        >
          <div className="flex items-start gap-3">
            <ShieldAlert size={20} className="text-[#9A3A23] shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-serif text-lg text-[#5B1F1F]">
                Direct outreach isn&rsquo;t recommended right now
              </h4>
              <p className="text-sm text-[#5B1F1F]/90 mt-1 leading-relaxed">
                Based on your safety screen, sending an invitation directly to
                your co-parent through this app isn&rsquo;t safe. A mediator,
                attorney, or DV advocate can handle communication safely on
                your behalf.
              </p>
              <div className="mt-3 rounded-xl bg-white/70 border border-[#F1B7B7] px-4 py-3 flex items-center gap-3">
                <Phone size={16} className="text-[#9A3A23] shrink-0" />
                <div className="text-sm text-[#5B1F1F]">
                  <strong>In danger?</strong> Call{" "}
                  <a href="tel:911" className="underline font-semibold">911</a> or the National DV Hotline{" "}
                  <a href="tel:18007997233" className="underline font-semibold">1-800-799-7233</a>.
                </div>
              </div>
              {/* Warm handoff — one-tap to a vetted mediator/attorney */}
              <Link
                to="/professionals"
                data-testid="invite-coparent-warm-handoff-cta"
                className="mt-4 inline-flex items-center gap-2 rounded-full bg-[#9A3A23] text-white px-4 py-2 text-sm font-semibold hover:brightness-110"
              >
                Send my case to a mediator instead
              </Link>
              <p className="mt-2 text-[11px] text-[#5B1F1F]/80 leading-relaxed">
                A vetted family-law professional receives your case code and can
                reach your co-parent safely — you never need to email them
                directly.
              </p>
              <Link
                to="/safety"
                data-testid="invite-coparent-review-safety-link"
                className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-[#9A3A23] underline"
              >
                Review my safety plan
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Send form — only when gate is clear AND no invite has been used yet */}
      {!loading && canSend && (
        <>
          <div className="mt-6 flex flex-col sm:flex-row gap-2">
            <div className="relative flex-1">
              <Mail
                size={16}
                className="absolute left-4 top-1/2 -translate-y-1/2 text-[#6E6787]"
              />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="co-parent@email.com"
                data-testid="invite-coparent-email-input"
                disabled={sending}
                className="w-full pl-11 pr-4 py-3 rounded-2xl border border-[#E5E0EE] text-sm focus:outline-none focus:border-[#3D1A78] disabled:bg-[#F0EDF7]/40"
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSend();
                }}
              />
            </div>
            <button
              type="button"
              onClick={handleSend}
              disabled={sending}
              data-testid="invite-coparent-send-button"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-2xl bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white font-semibold text-sm shadow-sm hover:shadow-md transition-all disabled:opacity-60 disabled:cursor-not-allowed shrink-0"
            >
              {sending ? <Loader2 className="animate-spin" size={16} /> : <Send size={16} />}
              Send invite
            </button>
          </div>
          <p
            className="text-[11px] text-[#6E6787] mt-2 inline-flex items-center gap-1.5"
            data-testid="invite-coparent-one-shot-notice"
          >
            <Lock size={11} /> One invitation per co-parent — please double-check the address.
          </p>
        </>
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

      {/* Invite already used — show the current status, no form */}
      {!loading && inviteUsed && invites.length > 0 && (
        <div
          className="mt-6 pt-5 border-t border-[#E5E0EE]"
          data-testid="invite-coparent-list"
        >
          <div className="eyebrow mb-3">Your invitation</div>
          <ul className="space-y-2">
            {invites.slice(0, 1).map((inv) => {
              const meta = STATUS_META[inv.status] || STATUS_META.pending;
              const created = fmtDate(inv.created_at);
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
                    <div className="text-[11px] text-[#6E6787] mt-0.5 inline-flex items-center gap-1">
                      <Clock size={11} /> Sent {created || "—"}
                    </div>
                  </div>
                  <span
                    className={`text-[10px] uppercase tracking-[0.12em] px-2 py-0.5 rounded-full ${meta.chip}`}
                  >
                    {meta.label}
                  </span>
                </li>
              );
            })}
          </ul>
          {invites[0].status === "expired" || invites[0].status === "rejected" ? (
            <p className="text-[11px] text-[#6E6787] mt-3 leading-relaxed">
              This invitation was not accepted within the 30-day window and is
              now closed. Only one invitation is permitted between parents
              through this app — if you still need to reach your co-parent, a
              mediator or attorney can help.
            </p>
          ) : invites[0].status === "signed_up" ? (
            <p className="text-[11px] text-[#1F6E2E] mt-3 leading-relaxed">
              Your co-parent has joined and is prepping in their own private
              workspace.
            </p>
          ) : (
            <p className="text-[11px] text-[#6E6787] mt-3 leading-relaxed">
              We&rsquo;ll let you know when your co-parent accepts. No further
              invitations can be sent from this app.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
