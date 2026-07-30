/**
 * SpecialNeedsInvite.jsx — send a Special Needs Co-Parenting invite to a
 * co-parent, list previously sent invites, and expose the accept link for
 * manual sharing.
 */
import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { toast } from "sonner";
import {
  Mail,
  Loader2,
  ArrowLeft,
  Copy,
  RefreshCcw,
  Trash2,
  CheckCircle2,
} from "lucide-react";
import { logError } from "../lib/logger";

function statusPill(status) {
  const map = {
    pending: { label: "Waiting for acceptance", cls: "bg-[#FBEDDA] text-[#8C5A2C] border-[#EDD5B0]" },
    accepted: { label: "Accepted", cls: "bg-[#E6F4EC] text-[#1F5C3B] border-[#B5DFC5]" },
    revoked: { label: "Cancelled", cls: "bg-[#EEEAF3] text-[#6E6E82] border-[#D6CFE8]" },
    expired: { label: "Expired", cls: "bg-[#EEEAF3] text-[#6E6E82] border-[#D6CFE8]" },
  };
  const conf = map[status] || map.pending;
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-semibold border ${conf.cls}`}>
      {conf.label}
    </span>
  );
}

export default function SpecialNeedsInvite() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [invites, setInvites] = useState({ sent: [], received: [] });
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const r = await api.get("/snc/invite/mine");
      setInvites(r.data || { sent: [], received: [] });
    } catch (err) {
      logError("snc invite list", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const submit = async (e) => {
    e.preventDefault();
    if (!email.trim()) return;
    setBusy(true);
    try {
      const r = await api.post("/snc/invite/coparent", { email: email.trim() });
      if (r.data?.sent) {
        toast.success("Invite sent.");
      } else if (r.data?.accept_url) {
        toast.info(r.data.reason || "Invite created — email couldn't be delivered.");
      }
      setEmail("");
      await load();
    } catch (err) {
      logError("snc invite create", err);
      toast.error(err?.response?.data?.detail || "Could not create the invite.");
    } finally {
      setBusy(false);
    }
  };

  const resend = async (invite_id) => {
    setBusy(true);
    try {
      const r = await api.post(`/snc/invite/${invite_id}/resend`);
      if (r.data?.sent) toast.success("Invite resent.");
      else toast.info("Email couldn't be delivered. Share the link directly.");
      await load();
    } catch (err) {
      logError("snc invite resend", err);
      toast.error(err?.response?.data?.detail || "Could not resend the invite.");
    } finally {
      setBusy(false);
    }
  };

  const revoke = async (invite_id) => {
    if (!window.confirm("Cancel this invite?")) return;
    setBusy(true);
    try {
      await api.delete(`/snc/invite/${invite_id}`);
      toast.success("Invite cancelled.");
      await load();
    } catch (err) {
      logError("snc invite revoke", err);
      toast.error(err?.response?.data?.detail || "Could not cancel the invite.");
    } finally {
      setBusy(false);
    }
  };

  const copyLink = async (invite) => {
    const url = `${window.location.origin}/special-needs/invite/${invite.token || ""}`;
    try {
      await navigator.clipboard.writeText(url);
      toast.success("Invite link copied.");
    } catch {
      toast.error("Could not copy the link.");
    }
  };

  return (
    <AppShell>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10" data-testid="snc-invite-root">
        <Link to="/special-needs/report" className="inline-flex items-center gap-2 text-xs text-[#4B4567] underline mb-4" data-testid="snc-invite-back">
          <ArrowLeft size={12} /> Back to my report
        </Link>

        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
          Invite your co-parent
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">
          Get a neutral side-by-side once you both finish.
        </h1>
        <p className="text-sm text-[#4B4567] mt-3 max-w-2xl">
          Your co-parent completes the same assessment in their own private
          account. Their answers stay private — no one ever sees the other
          person&apos;s raw responses. The only shared output is a neutral
          side-by-side that highlights agreement, different observations, and
          practical coordination areas. Safety answers are always kept out.
        </p>

        <form
          onSubmit={submit}
          className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-6 shadow-sm"
          data-testid="snc-invite-form"
        >
          <label className="block text-xs font-semibold uppercase tracking-[0.18em] text-[#3D1A78] mb-2">
            Co-parent&apos;s email address
          </label>
          <div className="flex flex-wrap gap-3">
            <input
              data-testid="snc-invite-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="coparent@example.com"
              className="flex-1 min-w-[240px] rounded-full border border-[#D6CFE8] bg-white px-4 py-2.5 text-sm text-[#1A1330] focus:outline-none focus:ring-2 focus:ring-[#3D1A78]/30"
            />
            <button
              type="submit"
              disabled={busy || !email.trim()}
              data-testid="snc-invite-submit"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm bg-[#3D1A78] text-white hover:brightness-110 disabled:opacity-60"
            >
              {busy ? <Loader2 size={14} className="animate-spin" /> : <Mail size={14} />}
              Send invitation
            </button>
          </div>
        </form>

        {/* Sent invites list */}
        <section className="mt-8">
          <h2 className="font-serif text-2xl text-[#1A1330] mb-3">Invites you&apos;ve sent</h2>
          {loading ? (
            <div className="text-sm text-[#4B4567]"><Loader2 className="animate-spin inline" size={14} /> Loading…</div>
          ) : (invites.sent || []).length === 0 ? (
            <div className="text-sm text-[#8471B3] italic">You haven&apos;t sent any invites yet.</div>
          ) : (
            <div className="space-y-3" data-testid="snc-invite-sent-list">
              {invites.sent.map((iv) => (
                <div
                  key={iv.invite_id}
                  className="bg-white rounded-2xl border border-[#E5E0EE] p-4 flex flex-wrap items-center justify-between gap-3 shadow-sm"
                  data-testid={`snc-invite-row-${iv.invite_id}`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium text-[#1A1330] truncate">{iv.invitee_email}</div>
                    <div className="text-[11px] text-[#4B4567] mt-0.5 flex items-center gap-2 flex-wrap">
                      {statusPill(iv.status)}
                      {iv.created_at && (
                        <span>Sent {new Date(iv.created_at).toLocaleDateString()}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {iv.status === "accepted" && (
                      <Link
                        to={`/special-needs/comparison/${iv.invite_id}`}
                        data-testid={`snc-invite-view-comparison-${iv.invite_id}`}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs bg-[#3D1A78] text-white hover:brightness-110"
                      >
                        <CheckCircle2 size={12} /> View comparison
                      </Link>
                    )}
                    {iv.status === "pending" && (
                      <>
                        <button
                          onClick={() => copyLink(iv)}
                          data-testid={`snc-invite-copy-${iv.invite_id}`}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs border border-[#D6CFE8] text-[#3D1A78] hover:bg-[#EEE9F7]"
                        >
                          <Copy size={12} /> Copy link
                        </button>
                        <button
                          onClick={() => resend(iv.invite_id)}
                          data-testid={`snc-invite-resend-${iv.invite_id}`}
                          disabled={busy}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs border border-[#D6CFE8] text-[#3D1A78] hover:bg-[#EEE9F7] disabled:opacity-60"
                        >
                          <RefreshCcw size={12} /> Resend
                        </button>
                      </>
                    )}
                    {iv.status !== "accepted" && (
                      <button
                        onClick={() => revoke(iv.invite_id)}
                        data-testid={`snc-invite-revoke-${iv.invite_id}`}
                        disabled={busy}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs border border-[#EFB4B4] text-[#B02A2A] hover:bg-[#F8D7D7]/40 disabled:opacity-60"
                      >
                        <Trash2 size={12} /> Cancel
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Received invites list */}
        {(invites.received || []).length > 0 && (
          <section className="mt-8">
            <h2 className="font-serif text-2xl text-[#1A1330] mb-3">Invites you accepted</h2>
            <div className="space-y-3" data-testid="snc-invite-received-list">
              {invites.received.map((iv) => (
                <div key={iv.invite_id} className="bg-white rounded-2xl border border-[#E5E0EE] p-4 flex flex-wrap items-center justify-between gap-3 shadow-sm">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium text-[#1A1330]">From {iv.from_name || iv.invitee_email}</div>
                    <div className="text-[11px] text-[#4B4567] mt-0.5">{statusPill(iv.status)}</div>
                  </div>
                  <Link
                    to={`/special-needs/comparison/${iv.invite_id}`}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs bg-[#3D1A78] text-white hover:brightness-110"
                    data-testid={`snc-invite-comparison-received-${iv.invite_id}`}
                  >
                    View comparison
                  </Link>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </AppShell>
  );
}
