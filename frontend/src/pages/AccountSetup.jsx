import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";
import PasswordStrengthMeter, { scorePassword } from "../components/PasswordStrengthMeter";
import { ConsentFields, consentReady, emptyConsent } from "../components/privacy/ConsentFields";

export default function AccountSetup() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { checkAuth } = useAuth();
  const previewed = useRef(false);

  const [stage, setStage] = useState("loading"); // loading | ready | error
  const [error, setError] = useState(null);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);
  const [consent, setConsent] = useState(emptyConsent);

  useEffect(() => {
    if (previewed.current) return;
    previewed.current = true;
    const token = params.get("token");
    if (!token) {
      setStage("error");
      setError({
        title: "Missing setup token",
        message: "Open the most recent setup link from your inbox.",
        code: "missing_token",
      });
      return;
    }
    (async () => {
      try {
        const r = await api.get("/auth/magic-link/preview", { params: { token } });
        if (r.data?.mode !== "signup") {
          setStage("error");
          setError({
            title: "Wrong link type",
            message: "This link is for signing in, not for creating an account. Use the sign-in link from your inbox.",
            code: "wrong_mode",
          });
          return;
        }
        setEmail(r.data.email || "");
        setStage("ready");
      } catch (err) {
        logError("setup preview failed:", err);
        const status = err?.response?.status;
        setStage("error");
        setError({
          title: "We couldn't open that setup link",
          message: err?.response?.data?.detail || "The link is invalid or expired. Please request a new one from the login page.",
          code: status ? `http_${status}` : "preview_failed",
        });
      }
    })();
  }, [params]);

  const submit = async (e) => {
    e.preventDefault();
    setFormError(null);
    if (!consentReady(consent)) {
      setFormError("Please tick both boxes to create your account.");
      return;
    }
    if (scorePassword(password).score < 2) {
      setFormError("Please choose a stronger password.");
      return;
    }
    setSubmitting(true);
    try {
      const token = params.get("token");
      await api.post("/auth/signup-from-token", { token, name, password, ...consent });
      await checkAuth();
      navigate("/dashboard", { replace: true });
    } catch (err) {
      logError("signup-from-token failed:", err);
      const detail = err?.response?.data?.detail;
      setFormError(typeof detail === "string" ? detail : "Could not create your account. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (stage === "loading") {
    return (
      <div className="min-h-screen gentle-bg grid place-items-center">
        <div className="text-center" data-testid="setup-loading">
          <div className="text-xs uppercase tracking-[0.25em] text-[#6E6787] mb-3">
            Opening your setup link
          </div>
          <div className="font-serif text-2xl text-[#1A1330]">One moment…</div>
        </div>
      </div>
    );
  }

  if (stage === "error") {
    return (
      <div className="min-h-screen gentle-bg grid place-items-center p-6">
        <div className="w-full max-w-md card-soft p-8 text-center fade-up" data-testid="setup-error">
          <div className="text-xs uppercase tracking-[0.25em] text-[#B07A6A] mb-3">
            Setup link issue
          </div>
          <h1 className="font-serif text-2xl text-[#1A1330] mb-3">{error.title}</h1>
          <p className="text-[#4B4567] mb-6">{error.message}</p>
          <Link to="/login" replace className="btn-sage w-full" data-testid="setup-back-to-login">
            Back to sign in
          </Link>
          <div className="text-[0.6875rem] uppercase tracking-[0.2em] text-[#A7B3AD] mt-6">
            Code: {error.code}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen gentle-bg grid place-items-center p-6">
      <div className="w-full max-w-md fade-up">
        <div className="card-soft p-8 sm:p-10">
          <div className="eyebrow text-[#3D1A78] mb-3">Welcome</div>
          <h1 className="font-sans font-extrabold text-3xl text-[#1A1330] mb-2 tracking-tight">
            Set up your account
          </h1>
          <p className="text-[#4B4567] mb-6 text-[15px] leading-relaxed">
            Email verified. Just pick a name and a password to finish.
          </p>

          <form onSubmit={submit} className="space-y-4">
            <label className="block">
              <span className="text-xs text-[#4B4567] font-semibold uppercase tracking-wider">
                Email (verified)
              </span>
              <input
                type="email"
                readOnly
                value={email}
                className="input-soft mt-1.5 opacity-80 cursor-not-allowed"
                data-testid="setup-email-input"
              />
            </label>
            <label className="block">
              <span className="text-xs text-[#4B4567] font-semibold uppercase tracking-wider">
                Your name
              </span>
              <input
                type="text"
                required
                autoComplete="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input-soft mt-1.5"
                data-testid="setup-name-input"
              />
            </label>
            <label className="block">
              <span className="text-xs text-[#4B4567] font-semibold uppercase tracking-wider">
                Password
              </span>
              <input
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-soft mt-1.5"
                data-testid="setup-password-input"
              />
              <PasswordStrengthMeter
                password={password}
                testid="setup-password-strength"
              />
              <span className="text-[0.6875rem] text-[#6E6787] mt-1 block">
                At least 8 characters. You'll use this to sign in next time.
              </span>
            </label>

            {formError && (
              <div className="text-sm text-[#B71F70] bg-[#B71F70]/8 rounded-xl px-3 py-2" data-testid="setup-form-error">
                {formError}
              </div>
            )}

            <ConsentFields tp="setup" value={consent} onChange={setConsent} />

            <button
              type="submit"
              disabled={submitting || !consentReady(consent)}
              className="btn-gradient w-full disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="setup-submit-button"
            >
              {submitting ? "Creating your account…" : "Create my account"}
            </button>
          </form>

        </div>
      </div>
    </div>
  );
}
