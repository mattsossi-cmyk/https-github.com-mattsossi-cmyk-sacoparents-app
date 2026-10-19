/**
 * SpecialNeedsV2Compare.jsx — Co-parent comparison hub.
 *
 * Lists existing comparison links (incoming + outgoing) and lets the parent
 * start a new one by entering their co-parent's email. Both parents must
 * (a) already have an account, (b) both consent, and (c) both have completed
 * their own SNC v2 assessment.
 */
import React, { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { toast } from "sonner";
import {
  ArrowLeft,
  Loader2,
  Mail,
  Check,
  X,
  Eye,
  RotateCcw,
  Users,
} from "lucide-react";
import { logError } from "../lib/logger";
import PathwayReportUnlockHint from "../components/PathwayReportUnlockHint";

function StatusBadge({ share }) {
  if (share.status === "revoked") {
    return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[0.625rem] font-semibold bg-[#F8D7D7] text-[#B02A2A] border border-[#EFB4B4]" data-testid="share-status-revoked">Revoked</span>;
  }
  if (share.ready_to_view) {
    return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[0.625rem] font-semibold bg-[#E6F4EC] text-[#1F5C3B] border border-[#B5DFC5]" data-testid="share-status-ready">Ready to view</span>;
  }
  if (!share.my_consent) {
    return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[0.625rem] font-semibold bg-[#FBEDDA] text-[#8C5A2C] border border-[#EDD5B0]" data-testid="share-status-await-me">Needs your consent</span>;
  }
  if (!share.partner_consent) {
    return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[0.625rem] font-semibold bg-[#EEE9F7] text-[#3D1A78] border border-[#D6CFE8]" data-testid="share-status-await-partner">Waiting on co-parent</span>;
  }
  if (!share.partner_assessment_complete) {
    return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[0.625rem] font-semibold bg-[#EEE9F7] text-[#3D1A78] border border-[#D6CFE8]">Co-parent not finished</span>;
  }
  if (!share.my_assessment_complete) {
    return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[0.625rem] font-semibold bg-[#FBEDDA] text-[#8C5A2C] border border-[#EDD5B0]">Finish your assessment</span>;
  }
  return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[0.625rem] font-semibold bg-[#EEE9F7] text-[#3D1A78] border border-[#D6CFE8]">Pending</span>;
}

export default function SpecialNeedsV2Compare() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [shares, setShares] = useState([]);
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/snc2/compare/me");
      setShares(res.data?.shares || []);
    } catch (err) {
      logError("snc2 compare list", err);
      toast.error(err?.response?.data?.detail || "Could not load comparisons.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const sendLink = async (e) => {
    e?.preventDefault?.();
    if (!email.trim()) return;
    setBusy(true);
    try {
      const res = await api.post("/snc2/compare/link", { email: email.trim() });
      if (res.data?.already_existed) {
        toast.info("You already have a comparison request with that co-parent.");
      } else {
        toast.success("Comparison request created. Your co-parent must consent from their account.");
      }
      setEmail("");
      await load();
    } catch (err) {
      logError("snc2 compare link", err);
      const detail = err?.response?.data?.detail || "Could not create the comparison request.";
      toast.error(detail);
    } finally {
      setBusy(false);
    }
  };

  const consent = async (shareId, value) => {
    setBusy(true);
    try {
      await api.post(`/snc2/compare/${shareId}/consent`, { consent: value });
      toast.success(value ? "Consent recorded." : "Consent withdrawn.");
      await load();
    } catch (err) {
      logError("snc2 compare consent", err);
      const detail = err?.response?.data?.detail || "Could not update your consent.";
      toast.error(detail);
    } finally { setBusy(false); }
  };

  const revoke = async (shareId) => {
    if (!window.confirm("Revoke this comparison? Neither parent will be able to view it after this.")) return;
    setBusy(true);
    try {
      await api.post(`/snc2/compare/${shareId}/revoke`);
      toast.success("Comparison revoked.");
      await load();
    } catch (err) {
      logError("snc2 compare revoke", err);
      toast.error(err?.response?.data?.detail || "Could not revoke.");
    } finally { setBusy(false); }
  };

  return (
    <AppShell>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10" data-testid="snc2-compare-root">
        <Link to="/special-needs-v2" data-testid="snc2-compare-back" className="inline-flex items-center gap-2 text-xs text-[#4B4567] underline mb-4">
          <ArrowLeft size={12} /> Back to Special Needs assessment
        </Link>

        <div className="text-[0.625rem] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
          Co-Parent Comparison
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">
          See where you and your co-parent already agree.
        </h1>
        <p className="text-sm text-[#4B4567] mt-3 max-w-2xl">
          When both parents complete their own Special Needs assessment and each of you explicitly opts in,
          you can view a neutral, side-by-side comparison of every step. Nothing is ever labeled as
          "correct" or "wrong" — the goal is to spotlight your shared ground and the areas where a
          coordinated conversation will help most.
        </p>


        <PathwayReportUnlockHint shares={shares} testidPrefix="snc2-compare" />

        {/* Start a new comparison */}
        <div className="mt-6 rounded-3xl border border-[#E5E0EE] bg-white p-5 sm:p-7 shadow-sm">
          <div className="flex items-center gap-2 text-[#3D1A78] mb-1"><Users size={16} /><span className="font-semibold text-sm">Start a new comparison</span></div>
          <p className="text-xs text-[#4B4567] mb-4">
            Your co-parent needs an existing SA CoParents account. If they don't have one, use the
            general <Link to="/coparent-invites" className="underline">Invite Co-parent</Link> flow first so they can create their own account.
          </p>
          <form onSubmit={sendLink} className="flex flex-col sm:flex-row gap-3">
            <label className="sr-only" htmlFor="partner-email">Co-parent email</label>
            <div className="flex-1 flex items-center gap-2 border border-[#E5E0EE] rounded-full px-4 py-2 bg-white focus-within:border-[#3D1A78]">
              <Mail size={14} className="text-[#6A5799]" />
              <input
                id="partner-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="coparent@email.com"
                className="flex-1 outline-none text-sm text-[#1A1330] bg-transparent"
                data-testid="snc2-compare-email-input"
              />
            </div>
            <button
              type="submit"
              disabled={busy || !email.trim()}
              data-testid="snc2-compare-send"
              className="inline-flex items-center justify-center gap-2 px-6 py-2 rounded-full text-sm bg-[#3D1A78] text-white hover:brightness-110 disabled:opacity-60"
            >
              {busy ? <Loader2 size={14} className="animate-spin" /> : <Mail size={14} />} Send request
            </button>
          </form>
        </div>

        {/* Existing shares */}
        <div className="mt-6" data-testid="snc2-compare-list">
          <h2 className="font-serif text-xl text-[#1A1330] mb-3">Your comparison requests</h2>
          {loading ? (
            <div className="text-sm text-[#4B4567]"><Loader2 className="animate-spin inline" size={14} /> Loading…</div>
          ) : shares.length === 0 ? (
            <div className="text-sm text-[#4B4567] italic">No comparison requests yet.</div>
          ) : (
            <div className="space-y-3">
              {shares.map((s) => (
                <div key={s.share_id} className="rounded-2xl border border-[#E5E0EE] bg-white p-4 sm:p-5 shadow-sm" data-testid={`snc2-compare-share-${s.share_id}`}>
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div>
                      <div className="text-sm font-semibold text-[#1A1330]">
                        {s.role === "creator" ? "You invited " : "Invited by "}
                        <span className="text-[#3D1A78]">{s.partner_name || s.partner_email}</span>
                      </div>
                      <div className="text-xs text-[#4B4567] mt-0.5">
                        {s.partner_email} · created {s.created_at ? new Date(s.created_at).toLocaleDateString() : "—"}
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <StatusBadge share={s} />
                        {s.shared_pathways && s.shared_pathways.length > 0 && (
                          <span className="text-[0.625rem] text-[#4B4567]">Shared pathways: {s.shared_pathways.join(", ")}</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-wrap">
                      {s.ready_to_view && (
                        <button
                          onClick={() => navigate(`/special-needs-v2/compare/${s.share_id}`)}
                          data-testid={`snc2-compare-view-${s.share_id}`}
                          className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs bg-[#3D1A78] text-white hover:brightness-110"
                        >
                          <Eye size={13} /> View comparison
                        </button>
                      )}
                      {s.status !== "revoked" && !s.my_consent && (
                        <button
                          onClick={() => consent(s.share_id, true)}
                          disabled={busy}
                          data-testid={`snc2-compare-consent-${s.share_id}`}
                          className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs bg-[#3D1A78] text-white hover:brightness-110 disabled:opacity-60"
                        >
                          <Check size={13} /> I consent
                        </button>
                      )}
                      {s.status !== "revoked" && s.my_consent && (
                        <button
                          onClick={() => consent(s.share_id, false)}
                          disabled={busy}
                          data-testid={`snc2-compare-withdraw-${s.share_id}`}
                          className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs border border-[#8C5A2C] text-[#8C5A2C] hover:bg-[#FBEDDA] disabled:opacity-60"
                        >
                          <X size={13} /> Withdraw consent
                        </button>
                      )}
                      {s.status !== "revoked" && (
                        <button
                          onClick={() => revoke(s.share_id)}
                          disabled={busy}
                          data-testid={`snc2-compare-revoke-${s.share_id}`}
                          className="inline-flex items-center gap-2 px-3 py-2 rounded-full text-xs border border-[#B02A2A] text-[#B02A2A] hover:bg-[#F8D7D7] disabled:opacity-60"
                        >
                          <RotateCcw size={13} /> Revoke
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <p className="text-[0.6875rem] text-[#4B4567] mt-8 italic max-w-3xl">
          This tool is neutral: neither parent is labeled as correct. Either parent can revoke at any time.
        </p>
      </div>
    </AppShell>
  );
}
