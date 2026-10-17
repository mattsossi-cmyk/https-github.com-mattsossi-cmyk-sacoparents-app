import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Plus, X } from "lucide-react";
import PasswordStrengthMeter, { scorePassword } from "../components/PasswordStrengthMeter";
import { ConsentFields, consentReady, emptyConsent } from "../components/privacy/ConsentFields";

export default function Register() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [custody, setCustody] = useState("");
  const [mediationDate, setMediationDate] = useState("");
  const [children, setChildren] = useState([{ uid: "c0", name: "", age: "" }]);
  const [loading, setLoading] = useState(false);
  const [consent, setConsent] = useState(emptyConsent);

  const addChild = () =>
    setChildren((c) => [...c, { uid: `c${Date.now()}`, name: "", age: "" }]);
  const removeChild = (i) =>
    setChildren((c) => (c.length > 1 ? c.filter((_, idx) => idx !== i) : c));
  const updateChild = (i, field, val) =>
    setChildren((c) => c.map((child, idx) => (idx === i ? { ...child, [field]: val } : child)));

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!consentReady(consent)) {
      toast.error("Please tick both boxes to create your account.");
      return;
    }
    if (scorePassword(password).score < 2) {
      toast.error("Please choose a stronger password.");
      return;
    }
    setLoading(true);
    try {
      await register({
        name,
        email,
        password,
        custody_situation: custody,
        mediation_date: mediationDate || null,
        children: children.filter((c) => c.name.trim()),
        ...consent,
      });
      toast.success("Welcome. Your space is ready.");
      navigate("/onboarding/what-do-you-need", { replace: true });
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Could not create account.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen gentle-bg grid place-items-center p-6">
      <div className="w-full max-w-xl fade-up">
        <Link to="/" className="block text-center mb-8">
          <svg width={68} height={68} viewBox="0 0 64 64" className="mx-auto mb-3" aria-hidden>
            <defs>
              <linearGradient id="regBmGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#3D1A78" />
                <stop offset="55%" stopColor="#5E2DB5" />
                <stop offset="100%" stopColor="#2DB5B5" />
              </linearGradient>
            </defs>
            <path
              d="M32 56 C12 42, 4 30, 12 18 C18 9, 28 10, 32 18 C36 10, 46 9, 52 18 C60 30, 52 42, 32 56 Z"
              fill="url(#regBmGrad)"
            />
            <circle cx="24" cy="26" r="4" fill="white" opacity="0.95" />
            <circle cx="40" cy="26" r="4" fill="white" opacity="0.95" />
            <path d="M22 36 Q32 44 42 36" stroke="white" strokeWidth="2.5" fill="none" strokeLinecap="round" opacity="0.9" />
          </svg>
          <div className="font-sans font-extrabold text-3xl text-[#1A1330] tracking-tight">
            <span className="text-brand-gradient">SA</span> CoParents
          </div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-[#6E6787] mt-1">
            Helping families communicate better
          </div>
        </Link>

        <div className="card-soft p-8 sm:p-10">
          <div className="eyebrow text-[#3D1A78] mb-3">Begin</div>
          <h1 className="font-sans font-extrabold text-4xl text-[#1A1330] mb-2 tracking-tight">Create your account</h1>
          <p className="text-[#4B4567] mb-6">
            Private by default. Share only when you choose to.
          </p>

          <form onSubmit={onSubmit} className="space-y-4">
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="register-name" className="eyebrow block mb-2">Your name</label>
                <input
                  id="register-name"
                  autoComplete="name"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="input-soft"
                  data-testid="register-name-input"
                />
              </div>
              <div>
                <label htmlFor="register-email" className="eyebrow block mb-2">Email</label>
                <input
                  id="register-email"
                  autoComplete="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-soft"
                  data-testid="register-email-input"
                />
              </div>
            </div>
            <div>
              <label htmlFor="register-password" className="eyebrow block mb-2">Password (min 8 characters)</label>
              <input
                id="register-password"
                autoComplete="new-password"
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-soft"
                data-testid="register-password-input"
              />
              <PasswordStrengthMeter
                password={password}
                testid="register-password-strength"
              />
              <div className="mt-2 text-right">
                <Link
                  to="/forgot-password"
                  className="text-xs text-[#3D1A78] font-semibold hover:underline"
                  data-testid="register-forgot-password-link"
                >
                  Already have an account? Reset password
                </Link>
              </div>
            </div>

            <div>
              <label className="eyebrow block mb-2">Children</label>
              <div className="space-y-2">
                {children.map((c, i) => (
                  <div key={c.uid} className="grid grid-cols-[1fr_120px_auto] gap-2 items-center">
                    <input
                      placeholder="Name"
                      value={c.name}
                      onChange={(e) => updateChild(i, "name", e.target.value)}
                      className="input-soft"
                      data-testid={`register-child-name-${i}`}
                    />
                    <input
                      placeholder="Age"
                      value={c.age}
                      onChange={(e) => updateChild(i, "age", e.target.value)}
                      className="input-soft"
                      data-testid={`register-child-age-${i}`}
                    />
                    <button
                      type="button"
                      onClick={() => removeChild(i)}
                      className="w-10 h-10 rounded-full hover:bg-[#EFE9F9] text-[#6E6787]"
                      aria-label="Remove child"
                      data-testid={`register-child-remove-${i}`}
                    >
                      <X size={16} className="mx-auto" />
                    </button>
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={addChild}
                className="mt-2 text-sm text-[#3D1A78] hover:underline inline-flex items-center gap-1"
                data-testid="register-add-child"
              >
                <Plus size={14} /> Add another child
              </button>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="eyebrow block mb-2">Current custody situation</label>
                <input
                  placeholder="e.g. 50/50, weekends only…"
                  value={custody}
                  onChange={(e) => setCustody(e.target.value)}
                  className="input-soft"
                  data-testid="register-custody-input"
                />
              </div>
              <div>
                <label htmlFor="register-mediation-date" className="eyebrow block mb-2">Mediation date (optional)</label>
                <input
                  id="register-mediation-date"
                  type="date"
                  value={mediationDate}
                  onChange={(e) => setMediationDate(e.target.value)}
                  className="input-soft"
                  data-testid="register-mediation-date-input"
                />
              </div>
            </div>

            <ConsentFields tp="register" value={consent} onChange={setConsent} />

            <button
              type="submit"
              disabled={loading || !consentReady(consent)}
              className="btn-gradient w-full disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="register-submit-button"
            >
              {loading ? "Creating account…" : "Create my account"}
            </button>
          </form>

          <p className="text-sm text-[#4B4567] mt-6 text-center">
            Already with us?{" "}
            <Link to="/login" className="text-[#3D1A78] font-semibold underline underline-offset-2" data-testid="register-to-login-link">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
