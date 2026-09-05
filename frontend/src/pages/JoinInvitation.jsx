/**
 * `/join/:token` — Joint Alignment invitation landing page.
 *
 * Two states:
 *   1. Not signed in — show the "You've been invited" preview
 *      (fetched from the public /invitation/{token} endpoint) and
 *      route the parent through login / register with a
 *      post-auth `?redirect=/join/:token` handoff.
 *   2. Signed in — POST the accept endpoint. If the authed email
 *      matches the invitation email → success screen with a
 *      "Start My Assessment" CTA that opens the right assessment
 *      route. If the email doesn't match → 403 friendly explainer.
 *
 * The preview API deliberately doesn't reveal the invitation email,
 * so we can't pre-check on the client — the accept call is the
 * source of truth on whether the parent is the right person.
 */
import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ShieldCheck,
  Sparkles,
  ArrowRight,
  Loader2,
  LogIn,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";

import AppShell from "../components/AppShell";
import { toast } from "sonner";

const API = process.env.REACT_APP_BACKEND_URL + "/api";

const ASSESSMENT_LABELS = {
  "co-parenting": "Co-Parenting Assessment",
  communication: "Communication Assessment",
  educational: "Educational Needs Assessment",
  medical: "Medical Needs Assessment",
  psychological: "Psychological / Emotional Needs Assessment",
  "special-needs": "Special Needs Assessment",
};

const ASSESSMENT_ROUTES = {
  "co-parenting": "/special-needs-v2",
  communication: "/communication",
  educational: "/edu-deep",
  medical: "/med-deep",
  psychological: "/psych-deep",
  "special-needs": "/special-needs-v2",
};

function getToken() {
  try {
    return localStorage.getItem("token");
  } catch {
    return null;
  }
}

export default function JoinInvitation() {
  const { token } = useParams();
  const navigate = useNavigate();
  const [preview, setPreview] = useState(null);
  const [previewError, setPreviewError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const [emailMismatch, setEmailMismatch] = useState(false);

  const authToken = getToken();

  // 1. Fetch invitation preview (no auth required).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch(`${API}/joint-alignment/invitation/${token}`);
        const body = await r.json();
        if (cancelled) return;
        if (r.ok) setPreview(body);
        else if (r.status === 410)
          setPreviewError({ code: 410, msg: body.detail || "Invitation expired" });
        else setPreviewError({ code: r.status, msg: body.detail || "Invitation not found" });
      } catch (e) {
        if (!cancelled) setPreviewError({ code: 0, msg: "Network error" });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  // 2. Auto-accept when the parent is signed in and the preview loaded.
  useEffect(() => {
    if (!authToken || !preview || accepted || previewError) return;
    if (preview.already_accepted) {
      setAccepted(true);
      return;
    }
    (async () => {
      setAccepting(true);
      try {
        const r = await fetch(
          `${API}/joint-alignment/invitation/${token}/accept`,
          {
            method: "POST",
            headers: { Authorization: `Bearer ${authToken}` },
          }
        );
        const body = await r.json();
        if (r.ok) {
          setAccepted(true);
          toast.success("Invitation linked to your account");
        } else if (r.status === 403) {
          setEmailMismatch(true);
        } else if (r.status === 410) {
          setPreviewError({ code: 410, msg: body.detail || "Invitation expired" });
        } else {
          toast.error(body.detail || "Could not accept invitation");
        }
      } catch (e) {
        toast.error("Network error");
      } finally {
        setAccepting(false);
      }
    })();
  }, [authToken, preview, accepted, previewError, token]);

  const gotoAssessment = () => {
    if (!preview) return;
    const route = ASSESSMENT_ROUTES[preview.assessment_type] || "/dashboard";
    navigate(route);
  };

  return (
    <AppShell>
      <div
        className="max-w-2xl mx-auto px-4 sm:px-6 py-10 sm:py-14"
        data-testid="join-invitation-page"
      >
        <div className="rounded-3xl bg-white border border-[#E5E0EE] p-6 sm:p-10 shadow-sm">
          <div className="text-[11px] uppercase tracking-[0.18em] font-bold text-[#3D1A78] mb-2">
            Joint Alignment invitation
          </div>

          {loading && (
            <div
              className="flex items-center gap-3 text-[#4B4567]"
              data-testid="join-invitation-loading"
            >
              <Loader2 className="animate-spin" size={18} />
              Loading invitation…
            </div>
          )}

          {!loading && previewError && (
            <div data-testid="join-invitation-error">
              <div className="flex items-center gap-3 text-[#8F1D24]">
                <AlertTriangle size={20} />
                <h1 className="font-serif text-2xl">
                  {previewError.code === 410
                    ? "This invitation has expired"
                    : "Invitation not found"}
                </h1>
              </div>
              <p className="text-[#4B4567] mt-3 leading-relaxed">
                Please ask the professional who invited you to send a fresh
                Joint Alignment Case link.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => navigate("/join")}
                  className="rounded-full bg-[#3D1A78] text-white px-5 py-2.5 text-sm font-semibold hover:bg-[#2A0F5F] transition"
                >
                  Have an Alignment Code? Enter it here
                </button>
                <button
                  type="button"
                  onClick={() => navigate("/dashboard")}
                  className="rounded-full border border-[#E5E0EE] text-[#3D1A78] px-5 py-2.5 text-sm font-semibold hover:border-[#3D1A78] transition"
                >
                  Go to dashboard
                </button>
              </div>
            </div>
          )}

          {!loading && preview && !previewError && (
            <>
              <h1
                className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight mt-2"
                data-testid="join-invitation-title"
              >
                You&rsquo;ve been invited to a Joint Alignment Report.
              </h1>

              <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3">
                <InfoRow
                  label="Assessment"
                  value={
                    ASSESSMENT_LABELS[preview.assessment_type] ||
                    preview.assessment_type
                  }
                  testid="join-invitation-assessment"
                />
                <InfoRow
                  label="Requested by"
                  value={preview.professional_name || "Your invited professional"}
                  testid="join-invitation-professional"
                />
                <InfoRow
                  label="Case ID"
                  value={preview.case_id}
                  testid="join-invitation-case-id"
                />
              </div>

              <div className="mt-6 rounded-2xl bg-[#F8F7FC] border border-[#E5E0EE] p-4 flex gap-3 items-start text-[13.5px] text-[#4B4567] leading-relaxed">
                <ShieldCheck
                  size={18}
                  className="text-[#3D1A78] flex-shrink-0 mt-0.5"
                />
                <p className="!m-0">
                  Your individual assessment is completed privately. Your
                  co-parent completes their assessment separately. The Joint
                  Alignment process is designed to identify areas of shared
                  understanding, different perspectives, and subjects that may
                  benefit from additional discussion, options, or resources.
                </p>
              </div>

              {/* Auth wall */}
              {!authToken && (
                <div
                  className="mt-6 rounded-2xl border-2 border-[#3D1A78] bg-white p-5"
                  data-testid="join-invitation-auth-wall"
                >
                  <h2 className="font-serif text-xl text-[#1A1330] flex items-center gap-2">
                    <LogIn size={18} className="text-[#3D1A78]" />
                    Sign in to link this invitation
                  </h2>
                  <p className="text-[13.5px] text-[#4B4567] mt-2 leading-relaxed">
                    We&rsquo;ll match this invitation to your SA CoParents
                    account. If you don&rsquo;t have one yet, you can create
                    it in the next step.
                  </p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <button
                      type="button"
                      onClick={() =>
                        navigate(
                          `/login?redirect=${encodeURIComponent(`/join/${token}`)}`
                        )
                      }
                      className="rounded-full bg-[#3D1A78] text-white px-5 py-2.5 text-sm font-semibold hover:bg-[#2A0F5F] transition"
                      data-testid="join-invitation-signin"
                    >
                      Sign in
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        navigate(
                          `/register?redirect=${encodeURIComponent(`/join/${token}`)}`
                        )
                      }
                      className="rounded-full border border-[#3D1A78] text-[#3D1A78] px-5 py-2.5 text-sm font-semibold hover:bg-[#F8F7FC] transition"
                      data-testid="join-invitation-register"
                    >
                      Create an account
                    </button>
                  </div>
                </div>
              )}

              {/* Email mismatch */}
              {authToken && emailMismatch && (
                <div
                  className="mt-6 rounded-2xl border-2 border-[#8F1D24] bg-[#FDECEC] p-5"
                  data-testid="join-invitation-email-mismatch"
                >
                  <h2 className="font-serif text-xl text-[#8F1D24] flex items-center gap-2">
                    <AlertTriangle size={18} />
                    This invitation was sent to a different email
                  </h2>
                  <p className="text-[13.5px] text-[#4B4567] mt-2 leading-relaxed">
                    Please sign out and sign back in using the email address
                    the professional used on your invitation. Your account is
                    safe — nothing was linked.
                  </p>
                </div>
              )}

              {/* Accepting spinner */}
              {authToken && accepting && !accepted && !emailMismatch && (
                <div
                  className="mt-6 flex items-center gap-3 text-[#4B4567]"
                  data-testid="join-invitation-accepting"
                >
                  <Loader2 className="animate-spin" size={18} />
                  Linking this invitation to your account…
                </div>
              )}

              {/* Accepted */}
              {authToken && accepted && (
                <div
                  className="mt-6 rounded-2xl border-2 border-[#1E7A55] bg-[#F1F9F4] p-5"
                  data-testid="join-invitation-accepted"
                >
                  <h2 className="font-serif text-xl text-[#1A1330] flex items-center gap-2">
                    <CheckCircle2 size={18} className="text-[#1E7A55]" />
                    You&rsquo;re linked to this Joint Alignment case
                  </h2>
                  <p className="text-[13.5px] text-[#4B4567] mt-2 leading-relaxed">
                    Complete your individual assessment when you&rsquo;re
                    ready. Your co-parent will complete theirs separately, and
                    the professional will be notified once both are done.
                  </p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <button
                      type="button"
                      onClick={gotoAssessment}
                      className="inline-flex items-center gap-2 rounded-full bg-[#3D1A78] text-white px-5 py-2.5 text-sm font-semibold hover:bg-[#2A0F5F] transition"
                      data-testid="join-invitation-start-assessment"
                    >
                      <Sparkles size={16} />
                      Start My Assessment
                      <ArrowRight size={14} />
                    </button>
                    <button
                      type="button"
                      onClick={() => navigate("/dashboard")}
                      className="rounded-full border border-[#E5E0EE] text-[#3D1A78] px-5 py-2.5 text-sm font-semibold hover:border-[#3D1A78] transition"
                    >
                      Go to my dashboard
                    </button>
                  </div>
                </div>
              )}

              <div className="mt-8 text-center">
                <button
                  type="button"
                  onClick={() => navigate("/join")}
                  className="text-[13px] text-[#3D1A78] underline hover:text-[#2A0F5F]"
                  data-testid="join-invitation-manual-code-link"
                >
                  Enter an Alignment Code instead
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}

function InfoRow({ label, value, testid }) {
  return (
    <div className="rounded-xl border border-[#E5E0EE] bg-[#FAFAFC] p-3">
      <div className="text-[10px] uppercase tracking-[0.14em] font-bold text-[#857E9C]">
        {label}
      </div>
      <div
        className="text-[14px] text-[#1A1330] font-medium mt-1 leading-tight"
        data-testid={testid}
      >
        {value}
      </div>
    </div>
  );
}
