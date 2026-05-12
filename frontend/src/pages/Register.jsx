import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Plus, X } from "lucide-react";

export default function Register() {
  const navigate = useNavigate();
  const { register, loginWithGoogle } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [custody, setCustody] = useState("");
  const [mediationDate, setMediationDate] = useState("");
  const [children, setChildren] = useState([{ uid: "c0", name: "", age: "" }]);
  const [loading, setLoading] = useState(false);

  const addChild = () =>
    setChildren((c) => [...c, { uid: `c${Date.now()}`, name: "", age: "" }]);
  const removeChild = (i) =>
    setChildren((c) => (c.length > 1 ? c.filter((_, idx) => idx !== i) : c));
  const updateChild = (i, field, val) =>
    setChildren((c) => c.map((child, idx) => (idx === i ? { ...child, [field]: val } : child)));

  const onSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await register({
        name,
        email,
        password,
        custody_situation: custody,
        mediation_date: mediationDate || null,
        children: children.filter((c) => c.name.trim()),
      });
      toast.success("Welcome. Your space is ready.");
      navigate("/dashboard");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Could not create account.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen gentle-bg grid place-items-center p-6">
      <div className="w-full max-w-xl fade-up">
        <Link to="/" className="block text-center mb-8">
          <div className="font-serif text-3xl text-[#2A3631]">SA Coparents</div>
          <div className="text-[10px] uppercase tracking-[0.25em] text-[#8A9A92]">
            Relational Mediation Prep
          </div>
        </Link>

        <div className="card-soft p-8 sm:p-10">
          <div className="eyebrow mb-3">Begin</div>
          <h1 className="font-serif text-4xl text-[#2A3631] mb-2">Create your account</h1>
          <p className="text-[#5C6B64] mb-6">
            Private by default. Share only when you choose to.
          </p>

          <button
            type="button"
            onClick={loginWithGoogle}
            className="btn-soft w-full flex items-center justify-center gap-3 mb-5"
            data-testid="google-register-button"
          >
            <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden>
              <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.4 29.3 35 24 35c-6.1 0-11-4.9-11-11s4.9-11 11-11c2.8 0 5.4 1.1 7.3 2.8l5.7-5.7C33.6 6.7 29 5 24 5 13.5 5 5 13.5 5 24s8.5 19 19 19 19-8.5 19-19c0-1.2-.1-2.3-.4-3.5z" />
              <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 16 19 13 24 13c2.8 0 5.4 1.1 7.3 2.8l5.7-5.7C33.6 6.7 29 5 24 5 16.3 5 9.8 9.1 6.3 14.7z" />
              <path fill="#4CAF50" d="M24 43c5 0 9.5-1.6 13-4.3l-6-5.1c-1.9 1.4-4.4 2.4-7 2.4-5.2 0-9.7-3.5-11.3-8.3l-6.5 5C9.8 38.9 16.3 43 24 43z" />
              <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.3-2.3 4.3-4.3 5.6l6 5.1C40.9 35 44 30 44 24c0-1.2-.1-2.3-.4-3.5z" />
            </svg>
            Continue with Google
          </button>

          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 divider-line" />
            <span className="text-xs text-[#8A9A92]">or with email</span>
            <div className="flex-1 divider-line" />
          </div>

          <form onSubmit={onSubmit} className="space-y-4">
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="eyebrow block mb-2">Your name</label>
                <input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="input-soft"
                  data-testid="register-name-input"
                />
              </div>
              <div>
                <label className="eyebrow block mb-2">Email</label>
                <input
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
              <label className="eyebrow block mb-2">Password (min 8 characters)</label>
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-soft"
                data-testid="register-password-input"
              />
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
                      className="w-10 h-10 rounded-full hover:bg-[#F5F3E9] text-[#8A9A92]"
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
                className="mt-2 text-sm text-[#849D8E] hover:underline inline-flex items-center gap-1"
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
                <label className="eyebrow block mb-2">Mediation date (optional)</label>
                <input
                  type="date"
                  value={mediationDate}
                  onChange={(e) => setMediationDate(e.target.value)}
                  className="input-soft"
                  data-testid="register-mediation-date-input"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-sage w-full"
              data-testid="register-submit-button"
            >
              {loading ? "Creating account…" : "Create my account"}
            </button>
          </form>

          <p className="text-sm text-[#5C6B64] mt-6 text-center">
            Already with us?{" "}
            <Link to="/login" className="text-[#849D8E] hover:underline" data-testid="register-to-login-link">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
