/**
 * SharedWithProfessionals — parent-facing management console for
 * every professional invitation they've sent. Powered by:
 *   GET  /api/parent/professional-invitations
 *   POST /api/parent/professional-invitations/{id}/revoke
 *   POST /api/parent/professional-invitations/{id}/extend
 *   POST /api/parent/professional-invitations/{id}/resend
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft, ShieldCheck, Loader2, RefreshCcw, Send, Ban, CalendarClock,
  Mail, FileText, Users, AlertCircle, Sparkles, Copy,
} from "lucide-react";

import AppShell from "../components/AppShell";
import { toast } from "sonner";
import { api } from "../lib/api";
import { logError } from "../lib/logger";

const STATUS_PILL = {
  invitation_sent: { label: "Invitation sent",     cls: "bg-[#F1EEF7] text-[#3D1A78]" },
  accepted:        { label: "Access active",       cls: "bg-[#E6F4EC] text-[#1F5C3B]" },
  declined:        { label: "Declined",            cls: "bg-[#FCE3DC] text-[#9A3A23]" },
  invitation_expired: { label: "Invitation expired", cls: "bg-[#FFF6E5] text-[#8A5B00]" },
  access_expired:  { label: "Access expired",      cls: "bg-[#FFF6E5] text-[#8A5B00]" },
  access_revoked:  { label: "Access revoked",      cls: "bg-[#FCE3DC] text-[#9A3A23]" },
};

function formatDate(iso) {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }); }
  catch { return iso; }
}

function daysUntil(iso) {
  if (!iso) return null;
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return null;
  return Math.round((then - Date.now()) / (1000 * 60 * 60 * 24));
}

export default function SharedWithProfessionals() {
  const [invitations, setInvitations] = useState(null);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const load = async () => {
    setError(null);
    try {
      const r = await api.get("/parent/professional-invitations");
      setInvitations(r.data?.invitations || []);
    } catch (err) {
      logError("shared-with-pros load failed", err);
      setError("Couldn't load your invitations.");
      setInvitations([]);
    }
  };
  useEffect(() => { load(); }, []);

  const handleRevoke = async (inv) => {
    if (!window.confirm(
      `Revoke access for ${inv.professional_first_name} ${inv.professional_last_name}?\n\n` +
      "They will lose portal access immediately. Previously downloaded copies cannot be recalled."
    )) return;
    setBusyId(inv.invitation_id);
    try {
      await api.post(`/parent/professional-invitations/${inv.invitation_id}/revoke`);
      toast.success("Access revoked.");
      await load();
    } catch (err) {
      logError("revoke failed", err);
      toast.error("Couldn't revoke access.");
    } finally { setBusyId(null); }
  };

  const handleExtend = async (inv) => {
    const raw = window.prompt("Extend access by how many days? (7 / 30 / 60 / 90)", "30");
    const days = parseInt(raw || "", 10);
    if (![7, 30, 60, 90].includes(days)) {
      toast.error("Please pick 7, 30, 60, or 90.");
      return;
    }
    setBusyId(inv.invitation_id);
    try {
      await api.post(
        `/parent/professional-invitations/${inv.invitation_id}/extend`,
        { access_days: days },
      );
      toast.success(`Access extended by ${days} days.`);
      await load();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Couldn't extend access.");
    } finally { setBusyId(null); }
  };

  const handleResend = async (inv) => {
    setBusyId(inv.invitation_id);
    try {
      const r = await api.post(`/parent/professional-invitations/${inv.invitation_id}/resend`);
      if (r.data?.accept_url) {
        try {
          await navigator.clipboard.writeText(r.data.accept_url);
          toast.success("Fresh invitation sent · link copied to clipboard.");
        } catch { toast.success("Fresh invitation sent."); }
      } else {
        toast.success("Fresh invitation sent.");
      }
      await load();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Couldn't resend.");
    } finally { setBusyId(null); }
  };

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10" data-testid="shared-with-pros-page">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
          data-testid="shared-back-link"
        >
          <ArrowLeft size={14} /> Back to dashboard
        </Link>
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] flex items-center gap-1.5">
              <ShieldCheck size={12} /> Shared with professionals
            </div>
            <h1
              className="font-serif text-4xl sm:text-5xl text-[#1A1330] leading-tight mt-1"
              data-testid="shared-with-pros-title"
            >
              Who has access to what
            </h1>
            <p className="text-[#4B4567] mt-3 leading-relaxed max-w-2xl">
              You&rsquo;re in control. Extend, revoke, or resend access at any
              time — sharing one report doesn&rsquo;t share your whole
              account, and giving one professional access doesn&rsquo;t give
              another one access.
            </p>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <button
              type="button"
              onClick={load}
              className="inline-flex items-center gap-1.5 rounded-full bg-white border border-[#E5E0EE] hover:bg-[#F5F1FB] text-[#3D1A78] px-3 py-1.5 text-xs font-semibold"
              data-testid="shared-refresh"
            >
              <RefreshCcw size={12} /> Refresh
            </button>
            <Link
              to="/share/professional"
              className="inline-flex items-center gap-1.5 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-3 py-1.5 text-xs font-semibold"
              data-testid="shared-invite-new"
            >
              <Sparkles size={12} /> Invite a professional
            </Link>
          </div>
        </div>

        {error && (
          <div role="alert" className="mt-6 rounded-xl bg-[#FCE3DC] border border-[#F5D0C5] text-[#9A3A23] px-4 py-3 text-sm">
            {error}
          </div>
        )}
        {invitations === null && (
          <div className="mt-8 text-center text-[#857E9C]" data-testid="shared-loading">
            <Loader2 className="animate-spin inline mr-2" size={16} />
            Loading your invitations…
          </div>
        )}
        {invitations !== null && invitations.length === 0 && (
          <div
            className="mt-8 rounded-3xl border border-[#E5E0EE] bg-white p-10 text-center"
            data-testid="shared-empty"
          >
            <Users size={22} className="mx-auto text-[#857E9C]" />
            <h2 className="font-serif text-2xl text-[#1A1330] mt-3">No invitations yet</h2>
            <p className="text-sm text-[#4B4567] mt-2 max-w-md mx-auto">
              Ready to share what you&rsquo;ve prepared with a mediator,
              attorney, or therapist? You pick which reports go out.
            </p>
            <Link
              to="/share/professional"
              className="inline-flex items-center gap-1.5 mt-4 rounded-full bg-[#3D1A78] hover:bg-[#2a0f5f] text-white px-4 py-2 text-sm font-semibold"
              data-testid="shared-empty-cta"
            >
              <Send size={13} /> Invite your first professional
            </Link>
          </div>
        )}
        {invitations !== null && invitations.length > 0 && (
          <ul className="mt-8 space-y-3" data-testid="shared-list">
            {invitations.map((inv) => {
              const isRevoked = !!inv.revoked_at;
              const daysToAccessExpire = daysUntil(inv.access_expiration);
              const pillStatus = isRevoked
                ? "access_revoked"
                : (daysToAccessExpire !== null && daysToAccessExpire < 0
                    ? "access_expired" : inv.status);
              const pill = STATUS_PILL[pillStatus] || STATUS_PILL.invitation_sent;
              const soonExpiring = daysToAccessExpire !== null && daysToAccessExpire >= 0 && daysToAccessExpire <= 7 && !isRevoked;
              return (
                <li
                  key={inv.invitation_id}
                  className="rounded-3xl border border-[#E5E0EE] bg-white p-5 shadow-sm"
                  data-testid={`shared-row-${inv.invitation_id}`}
                >
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-semibold text-[#1A1330]">
                          {inv.professional_first_name} {inv.professional_last_name}
                        </span>
                        <span className="text-[11px] text-[#857E9C]">·</span>
                        <span className="text-[11px] text-[#857E9C] capitalize">
                          {(inv.professional_role || "").replace("-", " ")}
                        </span>
                        <span
                          className={`ml-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${pill.cls}`}
                          data-testid={`shared-row-status-${inv.invitation_id}`}
                        >
                          {pill.label}
                        </span>
                        {soonExpiring && (
                          <span className="rounded-full px-2 py-0.5 text-[10px] font-semibold bg-[#FFF6E5] text-[#8A5B00]">
                            Access expires in {daysToAccessExpire}d
                          </span>
                        )}
                      </div>
                      <div className="text-[12px] text-[#4B4567] mt-1 flex items-center gap-1.5 flex-wrap">
                        <Mail size={11} /> {inv.professional_email}
                        {inv.organization && <span>· {inv.organization}</span>}
                      </div>
                      <div className="mt-2 flex items-start gap-1.5 text-[12px] text-[#4B4567]">
                        <FileText size={11} className="mt-0.5 flex-shrink-0" />
                        <span>
                          {(inv.selected_reports || []).map((r) => r.title).join(", ") || "—"}
                        </span>
                      </div>
                      <div className="mt-2 text-[11px] text-[#857E9C] flex flex-wrap gap-x-3 gap-y-0.5">
                        <span>Sent {formatDate(inv.created_at)}</span>
                        <span>Access expires {formatDate(inv.access_expiration)}</span>
                        {inv.download_permission
                          ? <span className="text-[#3D1A78]">Download allowed</span>
                          : <span>View-only</span>}
                        {(inv.view_count > 0 || inv.download_count > 0) && (
                          <span>
                            {inv.view_count} view{inv.view_count === 1 ? "" : "s"}
                            {" · "}{inv.download_count} download{inv.download_count === 1 ? "" : "s"}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2 border-t border-[#EEE8F7] pt-3">
                    {!isRevoked && inv.status !== "accepted" && (
                      <button
                        type="button"
                        onClick={() => handleResend(inv)}
                        disabled={busyId === inv.invitation_id}
                        className="inline-flex items-center gap-1 rounded-full bg-white border border-[#D6CFE8] hover:bg-[#F5F1FB] text-[#3D1A78] px-3 py-1 text-[11px] font-semibold disabled:opacity-50"
                        data-testid={`shared-row-resend-${inv.invitation_id}`}
                      >
                        <Send size={11} /> Resend
                      </button>
                    )}
                    {!isRevoked && (
                      <button
                        type="button"
                        onClick={() => handleExtend(inv)}
                        disabled={busyId === inv.invitation_id}
                        className="inline-flex items-center gap-1 rounded-full bg-white border border-[#D6CFE8] hover:bg-[#F5F1FB] text-[#3D1A78] px-3 py-1 text-[11px] font-semibold disabled:opacity-50"
                        data-testid={`shared-row-extend-${inv.invitation_id}`}
                      >
                        <CalendarClock size={11} /> Extend
                      </button>
                    )}
                    {!isRevoked && (
                      <button
                        type="button"
                        onClick={() => handleRevoke(inv)}
                        disabled={busyId === inv.invitation_id}
                        className="inline-flex items-center gap-1 rounded-full border border-[#F5D0C5] text-[#9A3A23] hover:bg-[#FCE3DC] bg-white px-3 py-1 text-[11px] font-semibold disabled:opacity-50"
                        data-testid={`shared-row-revoke-${inv.invitation_id}`}
                      >
                        {busyId === inv.invitation_id ? <Loader2 size={10} className="animate-spin" /> : <Ban size={11} />}
                        Revoke
                      </button>
                    )}
                    {isRevoked && (
                      <span className="text-[11px] text-[#857E9C] italic">
                        Access was revoked on {formatDate(inv.revoked_at)}
                      </span>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}

        <div className="mt-8 rounded-2xl bg-[#F5F1FB] border border-[#D6CFE8] p-4 text-[12px] text-[#3D1A78]" data-testid="shared-privacy-note">
          <div className="font-semibold flex items-center gap-1.5 mb-1">
            <ShieldCheck size={12} /> Privacy at a glance
          </div>
          You control your individual reports. Sharing one report doesn&rsquo;t
          share your full account. Giving one professional access doesn&rsquo;t
          give access to another professional. Revoking prevents future portal
          access — but SA CoParents can&rsquo;t recall a copy already downloaded.
        </div>
      </div>
    </AppShell>
  );
}
