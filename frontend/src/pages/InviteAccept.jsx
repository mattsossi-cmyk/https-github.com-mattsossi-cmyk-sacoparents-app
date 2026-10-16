import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Loader2, ShieldCheck, Sparkles, Users } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";
import { ConsentFields, consentReady, emptyConsent } from "../components/privacy/ConsentFields";

/**
 * Public landing for co-parent invites. Loads inviter info via the token,
 * then lets the recipient create their own private account.
 */
export default function InviteAccept() {
  const { token } = useParams();
  const nav = useNavigate();
  const { checkAuth } = useAuth();

  const [loading, setLoading] = useState(true);
  const [info, setInfo] = useState(null);
  const [loadErr, setLoadErr] = useState(null);

  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState(null);
  const [consent, setConsent] = useState(emptyConsent);

  useEffect(() => {
    let alive = true;
    api
      .get(`/invites/coparent/by-token/${token}`)
      .then((r) => alive && setInfo(r.data))
      .catch((e) => {
        logError("invite load failed", e);
        if (alive)
          setLoadErr(e?.response?.data?.detail || "This invite link is no longer valid.");
      })
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [token]);

  const handleSubmit = async () => {
    if (!name.trim()) {
      setErr("Please enter your name.");
      return;
    }
    if (password.length < 8) {
      setErr("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setErr("Passwords don't match.");
      return;
    }
    if (!consentReady(consent)) {
      setErr("Please tick both boxes to create your account.");
      return;
    }
    setErr(null);
    setSubmitting(true);
    try {
      await api.post(`/invites/coparent/accept/${token}`, {
        name: name.trim(),
        password,
        ...consent,
      });
      // Hydrate AuthContext with the new signed-in user, then go to dashboard.
      await checkAuth();
      nav("/dashboard", { replace: true });
    } catch (e) {
      const detail = e?.response?.data?.detail;
      setErr(typeof detail === "string" ? detail : "Could not create your account. Please try again.");
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen gentle-bg grid place-items-center px-4">
        <div className="card-soft p-8 text-center">
          <Loader2 className="animate-spin w-6 h-6 mx-auto text-[#3D1A78]" />
          <p className="text-sm text-[#4B4567] mt-3">Loading your invite…</p>
        </div>
      </div>
    );
  }

  if (loadErr || !info) {
    return (
      <div className="min-h-screen gentle-bg grid place-items-center px-4">
        <div
          className="card-soft p-8 text-center max-w-md"
          data-testid="invite-accept-invalid"
        >
          <h1 className="font-serif text-2xl text-[#1A1330] mb-2">Invite not valid</h1>
          <p className="text-sm text-[#4B4567]">{loadErr}</p>
          <a
            href="/"
            className="inline-block mt-6 text-sm font-medium text-[#3D1A78] hover:underline"
          >
            ← Go to SA CoParenting App
          </a>
        </div>
      </div>
    );
  }

  if (info.already_accepted) {
    return (
      <div className="min-h-screen gentle-bg grid place-items-center px-4">
        <div
          className="card-soft p-8 text-center max-w-md"
          data-testid="invite-accept-already"
        >
          <h1 className="font-serif text-2xl text-[#1A1330] mb-2">Already accepted</h1>
          <p className="text-sm text-[#4B4567]">
            An account has already been created from this invite. Please sign in instead.
          </p>
          <a
            href="/login"
            className="inline-block mt-6 px-5 py-2.5 rounded-full bg-[#3D1A78] text-white font-semibold text-sm"
          >
            Sign in
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen gentle-bg">
      <main className="max-w-xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
        <div className="text-center mb-8 fade-up">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-gradient-to-br from-[#3D1A78] to-[#2DB5B5] grid place-items-center text-white shadow-md mb-4">
            <Users size={26} strokeWidth={2.2} />
          </div>
          <div className="text-[11px] tracking-[0.22em] uppercase font-bold text-[#3D1A78] mb-2">
            You&apos;re invited
          </div>
          <h1 className="font-serif text-3xl sm:text-4xl text-[#1A1330] leading-tight">
            {info.inviter_name} wants to prep
            <br className="hidden sm:block" /> with you
          </h1>
          <p className="text-sm text-[#4B4567] mt-4 max-w-md mx-auto leading-relaxed">
            SA CoParenting App is a guided, child-focused workspace that helps both
            parents arrive at mediation prepared and calm.{" "}
            <strong className="text-[#1A1330]">
              Your answers are completely private — your co-parent will never see them.
            </strong>
          </p>
        </div>

        <div className="card-soft p-6 sm:p-7 fade-up">
          <div className="eyebrow mb-5">Create your private account</div>

          <div className="space-y-4">
            <div>
              <label className="text-xs uppercase tracking-[0.15em] text-[#857E9C] font-bold">
                Email
              </label>
              <input
                type="email"
                value={info.invitee_email || ""}
                disabled
                data-testid="invite-accept-email"
                className="w-full mt-1.5 px-4 py-3 rounded-2xl border border-[#E5E0EE] text-sm bg-[#F0EDF7]/40 text-[#857E9C]"
              />
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.15em] text-[#857E9C] font-bold">
                Your name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="First name (or what your child calls you)"
                data-testid="invite-accept-name"
                className="w-full mt-1.5 px-4 py-3 rounded-2xl border border-[#E5E0EE] text-sm focus:outline-none focus:border-[#3D1A78]"
              />
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.15em] text-[#857E9C] font-bold">
                Choose a password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                data-testid="invite-accept-password"
                className="w-full mt-1.5 px-4 py-3 rounded-2xl border border-[#E5E0EE] text-sm focus:outline-none focus:border-[#3D1A78]"
              />
            </div>
            <div>
              <label className="text-xs uppercase tracking-[0.15em] text-[#857E9C] font-bold">
                Confirm password
              </label>
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="Re-enter password"
                data-testid="invite-accept-confirm"
                className="w-full mt-1.5 px-4 py-3 rounded-2xl border border-[#E5E0EE] text-sm focus:outline-none focus:border-[#3D1A78]"
              />
            </div>
          </div>

          {err && (
            <div
              className="mt-4 rounded-xl bg-[#FCE3DC] text-[#9A3A23] px-4 py-2.5 text-xs"
              data-testid="invite-accept-error"
            >
              {err}
            </div>
          )}

          <div className="mt-5">
            <ConsentFields tp="invite-accept" value={consent} onChange={setConsent} />
          </div>

          <button
            type="button"
            onClick={handleSubmit}
            disabled={submitting || !consentReady(consent)}
            data-testid="invite-accept-submit"
            className="mt-6 w-full inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-full bg-gradient-to-r from-[#3D1A78] to-[#2DB5B5] text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all disabled:opacity-60"
          >
            {submitting ? (
              <Loader2 className="animate-spin" size={16} />
            ) : (
              <Sparkles size={16} />
            )}
            Create my account &amp; start
          </button>

          <div className="mt-5 flex items-start gap-2 text-[11px] text-[#857E9C] leading-relaxed">
            <ShieldCheck size={14} className="text-[#0E7A7A] mt-0.5 shrink-0" />
            <span>
              Your prep is private. {info.inviter_name} won&apos;t see any of your
              answers, journal entries, or summaries.
            </span>
          </div>
        </div>
      </main>
    </div>
  );
}
