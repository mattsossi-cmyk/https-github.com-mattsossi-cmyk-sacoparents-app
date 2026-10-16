import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { logError } from "../lib/logger";
import { ConsentFields, consentReady, emptyConsent } from "../components/privacy/ConsentFields";

export default function ClaimAccount() {
  const { user, claimGuest } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "", name: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [consent, setConsent] = useState(emptyConsent);

  if (!user) {
    navigate("/register", { replace: true });
    return null;
  }
  if (!user.is_guest) {
    navigate("/dashboard", { replace: true });
    return null;
  }

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!consentReady(consent)) {
      setError("Please tick both boxes to save your account.");
      return;
    }
    setLoading(true);
    try {
      await claimGuest({ ...form, ...consent });
      navigate("/dashboard", { replace: true });
    } catch (err) {
      logError("Claim failed:", err);
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Could not save your account. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen gentle-bg grid place-items-center p-6">
      <div className="w-full max-w-md fade-up">
        <div className="card-soft p-8 sm:p-10">
          <div className="eyebrow text-[#3D1A78] mb-3">Save your demo</div>
          <h1 className="font-sans font-extrabold text-3xl text-[#1A1330] mb-2 tracking-tight">
            Keep your work forever.
          </h1>
          <p className="text-[#4B4567] mb-6 text-[15px] leading-relaxed">
            All the answers you entered during the demo will move to your new account —
            and you'll unlock the AI summary, PDF download, mediator email, and share links.
          </p>

          <form onSubmit={submit} className="space-y-4">
            <label className="block">
              <span className="text-xs text-[#4B4567] font-semibold uppercase tracking-wider">
                Your name
              </span>
              <input
                type="text"
                required
                autoComplete="name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="input-soft mt-1.5"
                data-testid="claim-name-input"
              />
            </label>
            <label className="block">
              <span className="text-xs text-[#4B4567] font-semibold uppercase tracking-wider">
                Email
              </span>
              <input
                type="email"
                required
                autoComplete="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="input-soft mt-1.5"
                data-testid="claim-email-input"
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
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="input-soft mt-1.5"
                data-testid="claim-password-input"
              />
              <span className="text-[11px] text-[#857E9C] mt-1 block">
                At least 8 characters.
              </span>
            </label>

            {error && (
              <div
                className="text-sm text-[#B71F70] bg-[#B71F70]/8 rounded-xl px-3 py-2"
                data-testid="claim-error"
              >
                {error}
              </div>
            )}

            <ConsentFields tp="claim" value={consent} onChange={setConsent} />

            <button
              type="submit"
              disabled={loading || !consentReady(consent)}
              className="btn-gradient w-full disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="claim-submit-button"
            >
              {loading ? "Saving your account…" : "Save my work"}
            </button>
          </form>

        </div>
      </div>
    </div>
  );
}
