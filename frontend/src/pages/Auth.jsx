import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { BrandLogo } from "@/components/Brand";
import { ConfidentialityNotice } from "@/components/ConfidentialityNotice";
import { useAuth } from "@/context/AuthContext";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function Auth() {
  const search = new URLSearchParams(window.location.search);
  const next = search.get("next") || "";
  const inviteToken = next.startsWith("/join/") ? next.slice("/join/".length) : "";
  const isParentFlow = Boolean(inviteToken);
  const [isCourt, setIsCourt] = useState(search.get("court") === "1");
  const role = isParentFlow ? "parent" : isCourt ? "judge" : "professional";
  const resetToken = search.get("rt") || "";
  const [mode, setMode] = useState(search.get("mode") === "register" ? "register" : resetToken ? "reset" : "login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState(search.get("email") || "");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [profile, setProfile] = useState({ phone: "", organization: "", pro_role: "", city: "", state: "", license_number: "", website: "" });
  const [agreed, setAgreed] = useState(false);
  const [resetCode, setResetCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [cooldown, setCooldown] = useState(0);
  const [resending, setResending] = useState(false);

  useEffect(() => {
    if (cooldown <= 0) return undefined;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  const resendCode = async () => {
    setResending(true);
    try {
      await api.post("/auth/forgot-password", { email });
      toast.success("A fresh code is on its way — check your inbox.");
      setCooldown(60);
    } catch (e) {
      toast.error(formatApiError(e));
      if (e?.response?.status === 429) setCooldown(60);
    } finally { setResending(false); }
  };
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else if (mode === "register") {
        await register({ name, email, password, role, invite: inviteToken, agreements_accepted: agreed, ...profile });
      } else if (mode === "forgot") {
        await api.post("/auth/forgot-password", { email });
        setMode("reset");
        setCooldown(60);
        toast.success("Check your inbox (and spam folder) — your 6-digit verification code is on its way (valid for 15 minutes).");
        return;
      } else {
        await api.post("/auth/reset-password", resetToken ? { token: resetToken, new_password: newPassword } : { email, code: resetCode, new_password: newPassword });
        toast.success("Password updated. Sign in with your new password.");
        if (resetToken) navigate("/auth", { replace: true });
        setMode("login");
        setPassword("");
        setResetCode("");
        setNewPassword("");
        return;
      }
      navigate(next || "/dashboard");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col" data-testid="auth-page">
      <header className="max-w-6xl w-full mx-auto px-6 py-6">
        <Link to="/" className="w-fit" data-testid="auth-brand-link">
          <BrandLogo />
        </Link>
      </header>

      <main className="flex-1 flex items-center justify-center px-6 pb-16">
        <div className="w-full max-w-md bg-white border border-border rounded-lg p-8 shadow-sm" data-testid="auth-card">
          {(mode === "login" || mode === "register") && (
            <div className="flex gap-2 mb-8" role="tablist">
              <button
                type="button"
                onClick={() => setMode("login")}
                className={`flex-1 h-10 rounded-md text-sm font-medium transition-colors ${mode === "login" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}
                data-testid="login-tab"
              >
                Sign in
              </button>
              <button
                type="button"
                onClick={() => setMode("register")}
                className={`flex-1 h-10 rounded-md text-sm font-medium transition-colors ${mode === "register" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}
                data-testid="register-tab"
              >
                Create account
              </button>
            </div>
          )}

          <h1 className="text-3xl font-semibold mb-6" data-testid="auth-heading">
            {mode === "login" ? "Welcome back" : mode === "register" ? (isParentFlow ? "Create your parent account" : isCourt ? "Create your court account" : "Create your professional account") : mode === "forgot" ? "Reset your password" : resetToken ? "Set a new password" : "Enter your code"}
          </h1>
          {mode === "register" && !isParentFlow && (
            <div className="flex gap-2 mb-6" role="tablist" data-testid="account-type-tabs">
              <button type="button" onClick={() => setIsCourt(false)} className={`flex-1 h-9 rounded-md text-xs font-medium border transition-colors ${!isCourt ? "border-primary bg-primary/5 text-primary" : "border-border text-muted-foreground"}`} data-testid="account-type-professional">Family professional</button>
              <button type="button" onClick={() => setIsCourt(true)} className={`flex-1 h-9 rounded-md text-xs font-medium border transition-colors ${isCourt ? "border-primary bg-primary/5 text-primary" : "border-border text-muted-foreground"}`} data-testid="account-type-court">Judge / court staff</button>
            </div>
          )}

          <form onSubmit={submit} className="space-y-5" data-testid="auth-form">
            {mode === "register" && (
              <div className="space-y-2">
                <Label htmlFor="name">Full name</Label>
                <Input id="name" className="h-12" value={name} onChange={(e) => setName(e.target.value)} required data-testid="name-input" />
              </div>
            )}
            {mode === "register" && !isParentFlow && (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label htmlFor="phone">Phone</Label>
                    <Input id="phone" className="h-12" value={profile.phone} onChange={(e) => setProfile({ ...profile, phone: e.target.value })} data-testid="phone-input" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="organization">{isCourt ? "Court (e.g. 285th District Court, Bexar County)" : "Organization"}</Label>
                    <Input id="organization" className="h-12" value={profile.organization} onChange={(e) => setProfile({ ...profile, organization: e.target.value })} required={isCourt} data-testid="organization-input" />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="pro-role">{isCourt ? "Court role" : "Professional role"}</Label>
                  <select id="pro-role" className="w-full h-12 rounded-md border border-input bg-white px-3 text-sm" value={profile.pro_role} onChange={(e) => setProfile({ ...profile, pro_role: e.target.value })} data-testid="pro-role-select">
                    <option value="">Choose your role…</option>
                    {(isCourt ? ["Judge", "Associate judge", "Court coordinator", "Staff attorney / briefing attorney", "Other court staff"] : ["Mediator", "Attorney", "Therapist or counselor", "Parenting facilitator or coordinator", "Amicus attorney", "Child advocate", "Educational professional", "Medical professional", "Other approved professional"]).map((r) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label htmlFor="city">City</Label>
                    <Input id="city" className="h-12" value={profile.city} onChange={(e) => setProfile({ ...profile, city: e.target.value })} data-testid="city-input" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="state">State</Label>
                    <Input id="state" className="h-12" value={profile.state} onChange={(e) => setProfile({ ...profile, state: e.target.value })} data-testid="state-input" />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="license">License, certification, or State Bar number (when applicable)</Label>
                  <Input id="license" className="h-12" value={profile.license_number} onChange={(e) => setProfile({ ...profile, license_number: e.target.value })} data-testid="license-input" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="website">Professional website (optional)</Label>
                  <Input id="website" className="h-12" value={profile.website} onChange={(e) => setProfile({ ...profile, website: e.target.value })} data-testid="website-input" />
                </div>
              </>
            )}
            {!(mode === "reset" && resetToken) && (
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" className="h-12" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="email-input" />
            </div>
            )}
            {(mode === "login" || mode === "register") && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  {mode === "login" && (
                    <button type="button" onClick={() => setMode("forgot")} className="text-xs text-primary hover:underline" data-testid="forgot-password-link">
                      Forgot password?
                    </button>
                  )}
                </div>
                <Input id="password" type="password" className="h-12" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={mode === "register" ? 8 : undefined} data-testid="password-input" />
                {mode === "register" && <p className="text-xs text-muted-foreground">At least 8 characters.</p>}
              </div>
            )}
            {mode === "register" && isParentFlow && (
              <p className="text-sm text-muted-foreground bg-secondary/50 border border-border rounded-md p-3" data-testid="parent-invite-note">
                You're creating a parent account to accept your secure invitation. Joint reports are initiated by authorized professionals.
              </p>
            )}
            {mode === "forgot" && (
              <p className="text-sm text-muted-foreground" data-testid="forgot-info">
                Enter your account email. If an account exists, we'll send a 6-digit verification code to it.
              </p>
            )}
            {mode === "reset" && (
              <>
                {resetToken ? (
                  <p className="text-sm text-muted-foreground" data-testid="reset-link-info">You opened a one-click reset link. Choose a new password below — no code needed.</p>
                ) : (
                <div className="space-y-2">
                  <Label htmlFor="reset-code">Verification code</Label>
                  <Input id="reset-code" className="h-12 tracking-[0.3em] text-center text-lg" value={resetCode} onChange={(e) => setResetCode(e.target.value)} required maxLength={6} placeholder="6-digit code" data-testid="reset-code-input" />
                  <p className="text-xs text-muted-foreground">Check your email (including spam/junk) for the code. It expires in 15 minutes. Requesting a new code replaces the previous one.</p>
                  <p className="text-xs text-muted-foreground">
                    Didn't get it?{" "}
                    {cooldown > 0 ? (
                      <span data-testid="resend-code-countdown">Resend available in {cooldown}s</span>
                    ) : (
                      <button type="button" onClick={resendCode} disabled={resending} className="text-primary underline disabled:opacity-50" data-testid="resend-code-btn">{resending ? "Sending…" : "Resend code"}</button>
                    )}
                  </p>
                </div>
                )}
                <div className="space-y-2">
                  <Label htmlFor="new-password">New password</Label>
                  <Input id="new-password" type="password" className="h-12" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={8} data-testid="new-password-input" />
                  <p className="text-xs text-muted-foreground">At least 8 characters.</p>
                </div>
              </>
            )}
            {mode === "register" && !isParentFlow && (
              <>
                <label className="flex items-start gap-2.5 text-sm text-muted-foreground" data-testid="agreements-row">
                  <input type="checkbox" className="mt-1" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} data-testid="agreements-checkbox" />
                  <span>I accept the <Link to="/legal/professional-use" className="text-primary hover:underline">Professional-Use Agreement</Link>, confidentiality acknowledgment, <Link to="/privacy" className="text-primary hover:underline">Privacy Policy</Link>, appropriate-use policy, and no-professional-relationship disclaimer.</span>
                </label>
                <p className="text-xs text-muted-foreground bg-secondary/50 border border-border rounded-md p-3" data-testid="no-relationship-disclaimer">
                  Creating or using an SA CoParents Align account does not establish an attorney-client, therapist-client, physician-patient, mediator, evaluator, or other professional relationship with a parent or family.
                </p>
              </>
            )}
            {mode === "register" && <ConfidentialityNotice variant={isParentFlow ? "parent" : "professional"} />}
            <Button type="submit" className="w-full h-12" disabled={busy || (mode === "register" && !isParentFlow && !agreed)} data-testid="auth-submit-btn">
              {busy ? "Please wait…" : mode === "login" ? "Sign in" : mode === "register" ? (isParentFlow ? "Create parent account" : isCourt ? "Create court account" : "Create professional account") : mode === "forgot" ? "Send verification code" : "Reset password"}
            </Button>
            {(mode === "forgot" || mode === "reset") && (
              <button type="button" onClick={() => setMode("login")} className="w-full text-center text-sm text-muted-foreground hover:text-foreground" data-testid="back-to-login-btn">
                Back to sign in
              </button>
            )}
          </form>
          {(mode === "login" || mode === "register") && !isParentFlow && (
            <div className="mt-6 bg-secondary/50 border border-border rounded-md p-4 text-sm" data-testid="parent-notice">
              <p className="font-semibold">Are you a parent?</p>
              <p className="text-muted-foreground mt-1">Individual parent assessments begin at <a href="https://sacoparentsapp.online" target="_blank" rel="noreferrer" className="text-primary hover:underline">SA CoParents App</a>. Joint reports here are initiated by an authorized professional — you'll enter through your secure invitation link or case code.</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
