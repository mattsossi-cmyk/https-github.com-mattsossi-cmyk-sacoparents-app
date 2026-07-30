import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Loader2, ShieldAlert, Users } from "lucide-react";
import { toast } from "sonner";
import AppShell from "../components/AppShell";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

/**
 * Accept a co-parent invite for the Special Needs 2026 assessment.
 * Requires the acceptor to be signed in with an account that is DIFFERENT
 * from the inviter (backend enforces this).
 */
export default function SpecialNeedsInviteAccept() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const [state, setState] = useState({ loading: false, accepted: false, error: null });

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      // Bounce to login; keep return URL so we come back after auth.
      const back = encodeURIComponent(`/invites/special-needs/${token}`);
      navigate(`/login?redirect=${back}`, { replace: true });
    }
  }, [authLoading, user, navigate, token]);

  const accept = async () => {
    setState({ loading: true, accepted: false, error: null });
    try {
      await api.post(`/special-needs-v3/invite/${token}/accept`, {});
      setState({ loading: false, accepted: true, error: null });
      toast.success("Invite accepted — start your assessment.");
      setTimeout(() => navigate("/special-needs-v3", { replace: true }), 800);
    } catch (err) {
      const detail = err?.response?.data?.detail || "Couldn't accept the invite.";
      setState({ loading: false, accepted: false, error: detail });
    }
  };

  return (
    <AppShell>
      <div className="min-h-full bg-gradient-to-b from-[#F8F5FF] via-white to-white">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 py-12">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 text-sm text-[#3D1A78] hover:underline mb-4"
            data-testid="sn-invite-back"
          >
            <ArrowLeft size={14} /> Back to Dashboard
          </Link>

          <div className="rounded-3xl border border-[#CFC1EA] bg-white p-6 sm:p-8 shadow-sm" data-testid="sn-invite-card">
            <div className="flex items-start gap-3">
              <div className="shrink-0 w-11 h-11 rounded-full bg-[#F1EBFA] grid place-items-center text-[#3D1A78]">
                <Users size={20} />
              </div>
              <div className="min-w-0">
                <div className="text-[10px] uppercase tracking-[0.22em] font-bold text-[#3D1A78] mb-0.5">
                  Co-parent invite
                </div>
                <h1 className="font-serif text-2xl sm:text-3xl text-[#1A1330] leading-tight" data-testid="sn-invite-title">
                  Complete your Special Needs assessment
                </h1>
                <p className="text-sm text-[#4B4567] mt-2 leading-relaxed">
                  Your co-parent shared this link. Accept it to attach your assessment to theirs so
                  the two of you can see a side-by-side comparison of alignment, different
                  observations, and priorities. Each parent&apos;s answers remain private — the
                  comparison only shows domain-level results.
                </p>

                <div className="mt-4 rounded-2xl border border-[#F2B4B4] bg-[#FCE9E9] p-3 flex items-start gap-2 text-xs text-[#8B1E1E]">
                  <ShieldAlert size={14} className="shrink-0 mt-0.5" />
                  <span>
                    If you have safety concerns, you do not have to accept. Take the assessment on
                    your own instead — safety is always treated separately from ordinary
                    co-parenting recommendations.
                  </span>
                </div>

                {state.error && (
                  <div className="mt-4 rounded-xl border border-[#F0B6A0] bg-[#FEF1EC] p-3 text-sm text-[#C2481F]" data-testid="sn-invite-error">
                    {state.error}
                  </div>
                )}

                {state.accepted ? (
                  <div className="mt-6 rounded-2xl border border-[#B8DDC6] bg-[#E4F4EC] p-4 text-sm text-[#1F5C3B]" data-testid="sn-invite-accepted">
                    Invite accepted. Redirecting you to your assessment…
                  </div>
                ) : (
                  <div className="mt-6 flex flex-wrap gap-3">
                    <button
                      onClick={accept}
                      disabled={state.loading || !user}
                      className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-full bg-[#3D1A78] text-white text-sm font-semibold hover:bg-[#2D0F63] disabled:opacity-50"
                      data-testid="sn-invite-accept-btn"
                    >
                      {state.loading ? <Loader2 size={14} className="animate-spin" /> : <Users size={14} />}
                      Accept &amp; start my assessment
                    </button>
                    <Link
                      to="/special-needs-v3"
                      className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-full border border-[#E5E0EE] text-[#3D1A78] text-sm hover:bg-[#F5F2FA]"
                      data-testid="sn-invite-solo-btn"
                    >
                      Take it on my own <ArrowRight size={14} />
                    </Link>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
