import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Sparkles,
  FileText,
  Handshake,
  Users,
  Send,
  Loader2,
  ArrowRight,
  ShieldAlert,
  Lock,
} from "lucide-react";
import { toast } from "sonner";

import { api } from "../lib/api";
import { logError } from "../lib/logger";
import {
  jointReportUrl,
  jointAgreementUrl,
} from "../lib/jointArtefactUrls";

/**
 * JointAlignmentPromoCard — the "next unmistakable action" card.
 *
 * Two states, one component:
 *   1. Waiting: co-parent hasn't finished (or hasn't been invited). Shows a
 *      big "Invite Co-Parent" input inline. Uses the existing
 *      `/invites/coparent` endpoint so we don't fork the invite flow.
 *   2. Ready: co-parent finished and a Compare share exists. Shows two
 *      solid CTAs — View Joint Alignment Report / View Joint Alignment
 *      Agreement — both routed with `?mint=1` so the parent can send it
 *      to their mediator in one tap.
 *
 * Data source: `GET /snc2/compare/dashboard/highlights` (same call the
 * Dashboard already makes — feels instant on second render because the
 * response is cached in-flight).
 *
 * Drop this at the top of `/next-steps/:assessment` and `/summary`.
 */
export default function JointAlignmentPromoCard({
  contextLine,
  testidPrefix = "joint-alignment-promo",
}) {
  const [snc, setSnc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [inviteUsed, setInviteUsed] = useState(false);
  const [latestStatus, setLatestStatus] = useState(null);
  const [gate, setGate] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [highlights, invites, gateRes] = await Promise.all([
          api.get("/snc2/compare/dashboard/highlights").catch(() => null),
          api.get("/invites/coparent").catch(() => null),
          api.get("/invites/coparent/gate").catch(() => null),
        ]);
        if (cancelled) return;
        setSnc(highlights?.data || null);
        setInviteUsed(!!invites?.data?.invite_used);
        setLatestStatus(invites?.data?.latest_status || null);
        setGate(gateRes?.data || null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const sendInvite = async () => {
    const v = (email || "").trim().toLowerCase();
    if (!v || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) {
      toast.error("Please enter a valid email address.");
      return;
    }
    setSending(true);
    try {
      await api.post("/invites/coparent", { email: v });
      toast.success(`Invite sent to ${v}. They'll get an email shortly.`);
      setEmail("");
      setInviteUsed(true);
      setLatestStatus("pending");
    } catch (e) {
      logError("promo card invite send failed", e);
      const detail = e?.response?.data?.detail;
      const msg =
        (detail && typeof detail === "object" && detail.message) ||
        detail ||
        "Could not send invite. Please try again.";
      toast.error(msg);
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div
        className="card-soft p-6 sm:p-7 flex items-center gap-3 text-[#4B4567]"
        data-testid={`${testidPrefix}-loading`}
      >
        <Loader2 size={18} className="animate-spin" />
        <span className="text-sm">Checking your Joint Alignment status…</span>
      </div>
    );
  }

  const ready = Boolean(snc?.ready && snc?.share_id);
  const shareId = snc?.share_id;
  const partnerName = snc?.partner_name;

  if (ready) {
    return (
      <div
        className="card-soft p-6 sm:p-8 bg-gradient-to-br from-[#F4EFFC] to-white border-l-4 border-[#3D1A78]"
        data-testid={`${testidPrefix}-ready`}
      >
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] grid place-items-center text-white shadow-sm shrink-0">
            <Sparkles size={22} strokeWidth={2.2} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="eyebrow text-[#3D1A78] mb-1">
              Joint Alignment Report
            </div>
            <h2 className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-tight">
              Your Joint Alignment Report is ready
            </h2>
            <p className="text-sm text-[#4B4567] mt-2 max-w-xl">
              {partnerName ? (
                <>
                  You and{" "}
                  <span className="text-[#1A1330] font-medium">
                    {partnerName}
                  </span>{" "}
                  have both finished. Send the report to your mediator or
                  attorney — or open the Agreement to keep working together.
                </>
              ) : (
                <>
                  Both parents have finished. Send the report to your mediator
                  or attorney — or open the Agreement to keep working together.
                </>
              )}
            </p>

            <div className="mt-5 flex flex-wrap items-center gap-3">
              <Link
                to={jointReportUrl(shareId)}
                className="inline-flex items-center gap-2 rounded-full bg-[#3D1A78] text-white px-5 py-2.5 text-sm font-semibold shadow-sm hover:bg-[#2f1360] hover:shadow-md transition-all"
                data-testid={`${testidPrefix}-view-report`}
              >
                <FileText size={16} />
                View Joint Alignment Report
                <ArrowRight size={14} className="opacity-80" />
              </Link>
              <Link
                to={jointAgreementUrl(shareId)}
                className="inline-flex items-center gap-2 rounded-full border border-[#3D1A78] text-[#3D1A78] bg-white px-5 py-2.5 text-sm font-semibold shadow-sm hover:bg-[#F1EEF7] hover:shadow-md transition-all"
                data-testid={`${testidPrefix}-view-agreement`}
              >
                <Handshake size={16} />
                View Joint Alignment Agreement
                <ArrowRight size={14} className="opacity-80" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Waiting state — invite CTA inline.
  return (
    <div
      className="card-soft p-6 sm:p-8 bg-gradient-to-br from-[#EFE9F9] via-white to-[#E5F4F0] border-l-4 border-[#3D1A78]"
      data-testid={`${testidPrefix}-waiting`}
    >
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] grid place-items-center text-white shadow-sm shrink-0">
          <Users size={22} strokeWidth={2.2} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="eyebrow text-[#3D1A78] mb-1">Next step</div>
          <h2 className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-tight">
            Create a Joint Alignment Report
          </h2>
          <p className="text-sm text-[#4B4567] mt-2 max-w-xl">
            {contextLine ||
              "Compare your responses with your co-parent to see areas of alignment, differences, and topics that may need discussion."}{" "}
            Your co-parent will get their own account —{" "}
            <span className="text-[#1A1330] font-medium">
              you never share passwords
            </span>
            .
          </p>

          {inviteUsed ? (
            <div
              className="mt-5 flex items-center gap-2 text-sm text-[#3D1A78] bg-white rounded-2xl border border-[#E5E0EE] px-4 py-3"
              data-testid={`${testidPrefix}-invite-sent`}
            >
              <Send size={14} />
              <span>
                {latestStatus === "expired" || latestStatus === "rejected"
                  ? "Your invitation was not accepted within the 30-day window and is now closed. Only one invitation is permitted between parents."
                  : latestStatus === "signed_up"
                  ? "Your co-parent has joined. We'll unlock this card the moment their side is complete."
                  : "Invite sent. We'll unlock this card the moment they finish."}
              </span>
            </div>
          ) : gate && !gate.clear && gate.code === "safety_screen_required" ? (
            <div
              className="mt-5 rounded-2xl border-2 border-[#F1D9B7] bg-[#FFF6EA] px-4 py-4"
              data-testid={`${testidPrefix}-gate-required`}
            >
              <div className="flex items-start gap-3">
                <ShieldAlert size={18} className="text-[#B45F13] shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="text-sm text-[#5A3C10] leading-relaxed">
                    Complete the short family-violence safety screen first
                    (about 5 minutes). Your answers stay private.
                  </div>
                  <Link
                    to="/safety"
                    data-testid={`${testidPrefix}-take-safety-link`}
                    className="mt-3 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#B45F13] text-white text-sm font-semibold hover:brightness-110"
                  >
                    Take the safety screen
                  </Link>
                </div>
              </div>
            </div>
          ) : gate && !gate.clear && gate.code === "safety_screen_blocked" ? (
            <div
              className="mt-5 rounded-2xl border-2 border-[#F1B7B7] bg-[#FDECEC] px-4 py-4"
              data-testid={`${testidPrefix}-gate-blocked`}
            >
              <div className="flex items-start gap-3">
                <ShieldAlert size={18} className="text-[#9A3A23] shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="text-sm text-[#5B1F1F] leading-relaxed">
                    Based on your safety screen, direct outreach to your co-parent
                    through this app isn&rsquo;t recommended. A mediator or
                    attorney can handle communication on your behalf.{" "}
                    <a
                      href="tel:18007997233"
                      className="underline font-semibold whitespace-nowrap"
                    >
                      Hotline · 1-800-799-7233
                    </a>
                    .
                  </div>
                  <Link
                    to="/professionals"
                    data-testid={`${testidPrefix}-warm-handoff-cta`}
                    className="mt-3 inline-flex items-center gap-2 rounded-full bg-[#9A3A23] text-white px-4 py-2 text-sm font-semibold hover:brightness-110"
                  >
                    Send my case to a mediator instead
                  </Link>
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-5">
              <label className="eyebrow block mb-2">
                Co-parent&apos;s email
              </label>
              <div className="flex flex-col sm:flex-row gap-2">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-soft flex-1"
                  placeholder="coparent@example.com"
                  data-testid={`${testidPrefix}-email-input`}
                />
                <button
                  onClick={sendInvite}
                  disabled={sending}
                  className="inline-flex items-center justify-center gap-2 rounded-full bg-[#3D1A78] text-white px-5 py-2.5 text-sm font-semibold shadow-sm hover:bg-[#2f1360] disabled:opacity-60 transition-all whitespace-nowrap"
                  data-testid={`${testidPrefix}-send-invite`}
                >
                  {sending ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Send size={16} />
                  )}
                  {sending ? "Sending…" : "Invite Co-Parent"}
                </button>
              </div>
              <p
                className="text-[11px] text-[#857E9C] mt-2 inline-flex items-center gap-1.5"
                data-testid={`${testidPrefix}-one-shot-notice`}
              >
                <Lock size={11} /> One invitation per co-parent — please double-check the address.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
