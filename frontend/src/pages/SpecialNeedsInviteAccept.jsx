/**
 * SpecialNeedsInviteAccept.jsx — landing page for a Special Needs Co-Parenting
 * invitation link. Public preview for signed-out users, one-tap accept for
 * signed-in users.
 */
import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Loader2, Sparkles, ShieldCheck } from "lucide-react";
import { logError } from "../lib/logger";

const BACKEND = process.env.REACT_APP_BACKEND_URL || "";

export default function SpecialNeedsInviteAccept() {
  const { token } = useParams();
  const nav = useNavigate();
  const [state, setState] = useState({ loading: true, invite: null, error: null });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        // Public endpoint — use raw axios so we don't require auth cookies.
        const r = await axios.get(`${BACKEND}/api/snc/invite/by-token/${token}`);
        setState({ loading: false, invite: r.data, error: null });
      } catch (err) {
        logError("snc invite lookup", err);
        setState({ loading: false, invite: null, error: err?.response?.data?.detail || "Invite not found." });
      }
    })();
  }, [token]);

  const accept = async () => {
    setBusy(true);
    try {
      const r = await api.post(`/snc/invite/accept/${token}`);
      toast.success("Invite accepted. Let's start your assessment.");
      if (r.data?.invite?.invite_id) {
        localStorage.setItem("snc_active_invite_id", r.data.invite.invite_id);
      }
      nav("/special-needs");
    } catch (err) {
      if (err?.response?.status === 401) {
        // Route to login and come back to this URL after auth.
        localStorage.setItem("snc_pending_invite_token", token);
        nav(`/login?next=${encodeURIComponent(window.location.pathname)}`);
        return;
      }
      logError("snc invite accept", err);
      toast.error(err?.response?.data?.detail || "Could not accept the invite.");
    } finally {
      setBusy(false);
    }
  };

  if (state.loading) {
    return (
      <AppShell>
        <div className="max-w-2xl mx-auto px-4 py-10 text-[#4B4567]">
          <Loader2 className="animate-spin inline" /> Loading invite…
        </div>
      </AppShell>
    );
  }

  if (state.error || !state.invite) {
    return (
      <AppShell>
        <div className="max-w-2xl mx-auto px-4 py-10">
          <h1 className="font-serif text-3xl text-[#1A1330] mb-2">Invite not found</h1>
          <p className="text-sm text-[#4B4567]">
            {state.error || "This link may have expired or been cancelled by the sender."}
          </p>
        </div>
      </AppShell>
    );
  }

  const invite = state.invite;
  const inviter = invite.from_name || invite.invitee_email || "Your co-parent";

  return (
    <AppShell>
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-6 sm:py-10" data-testid="snc-invite-accept-root">
        <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-1">
          Special Needs Co-Parenting invitation
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">
          {inviter} invited you to a side-by-side.
        </h1>
        <p className="text-sm text-[#4B4567] mt-3">
          You&apos;ll complete the same 13-section assessment in your <strong>own private account</strong>. Neither of you will see the other&apos;s raw answers — the only shared output is a neutral side-by-side once both parents finish. Safety responses are always kept out.
        </p>

        <div className="mt-6 bg-white rounded-3xl border border-[#E5E0EE] p-5 sm:p-7 shadow-sm">
          <div className="flex items-start gap-3">
            <Sparkles className="text-[#3D1A78] mt-1" size={22} />
            <div>
              <h2 className="font-serif text-xl text-[#1A1330] mb-1">What happens next</h2>
              <ol className="mt-2 space-y-2 text-sm text-[#1A1330] list-decimal pl-5">
                <li>Accept the invite (creates the link between your two accounts).</li>
                <li>Complete the 13-section assessment at your own pace, with save-and-resume.</li>
                <li>Once you both finish, either parent can open the neutral side-by-side.</li>
              </ol>
            </div>
          </div>
        </div>

        <div className="mt-4 rounded-3xl bg-[#F8F5FC] border border-[#EEE9F7] p-4 sm:p-5 text-xs text-[#4B4567] flex gap-3 items-start">
          <ShieldCheck size={16} className="text-[#3D1A78] shrink-0 mt-0.5" />
          <div>
            The comparison never names a &ldquo;correct&rdquo; parent, never
            diagnoses a child, and never determines parental fitness. It
            highlights agreement, different observations, missing information,
            professional questions, and practical coordination areas.
          </div>
        </div>

        {invite.status === "accepted" ? (
          <div className="mt-6" data-testid="snc-invite-already-accepted">
            <div className="rounded-3xl border border-[#B5DFC5] bg-[#E6F4EC] p-4 text-sm text-[#1F5C3B] mb-4">
              This invite has already been accepted. Continue to your assessment.
            </div>
            <button
              onClick={() => nav("/special-needs")}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm bg-[#3D1A78] text-white hover:brightness-110"
              data-testid="snc-invite-open-assessment"
            >
              Open my assessment
            </button>
          </div>
        ) : (
          <div className="mt-6">
            <button
              onClick={accept}
              disabled={busy}
              data-testid="snc-invite-accept"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm bg-[#3D1A78] text-white hover:brightness-110 disabled:opacity-60"
            >
              {busy ? <Loader2 size={14} className="animate-spin" /> : null}
              Accept and start my assessment
            </button>
          </div>
        )}
      </div>
    </AppShell>
  );
}
