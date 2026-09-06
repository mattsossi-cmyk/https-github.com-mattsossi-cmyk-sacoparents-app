import { useState } from "react";
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
  const role = isParentFlow ? "parent" : "professional";
  const [mode, setMode] = useState(search.get("mode") === "register" ? "register" : "login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [resetCode, setResetCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else if (mode === "register") {
        await register({ name, email, password, role, invite: inviteToken });
      } else if (mode === "forgot") {
        await api.post("/auth/forgot-password", { email });
        setMode("reset");
        toast.success("If an account exists for that email, a verification code is on its way.");
        return;
      } else {
        await api.post("/auth/reset-password", { email, code: resetCode, new_password: newPassword });
        toast.success("Password updated. Sign in with your new password.");
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
            {mode === "login" ? "Welcome back" : mode === "register" ? (isParentFlow ? "Create your parent account" : "Create your professional account") : mode === "forgot" ? "Reset your password" : "Enter your code"}
          </h1>

          <form onSubmit={submit} className="space-y-5" data-testid="auth-form">
            {mode === "register" && (
              <div className="space-y-2">
                <Label htmlFor="name">Full name</Label>
                <Input id="name" className="h-12" value={name} onChange={(e) => setName(e.target.value)} required data-testid="name-input" />
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" className="h-12" value={email} onChange={(e) => setEmail(e.target.value)} required data-testid="email-input" />
            </div>
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
                <div className="space-y-2">
                  <Label htmlFor="reset-code">Verification code</Label>
                  <Input id="reset-code" className="h-12 tracking-[0.3em] text-center text-lg" value={resetCode} onChange={(e) => setResetCode(e.target.value)} required maxLength={6} placeholder="6-digit code" data-testid="reset-code-input" />
                  <p className="text-xs text-muted-foreground">Check your email for the code. It expires in 10 minutes.</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="new-password">New password</Label>
                  <Input id="new-password" type="password" className="h-12" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={8} data-testid="new-password-input" />
                  <p className="text-xs text-muted-foreground">At least 8 characters.</p>
                </div>
              </>
            )}
            {mode === "register" && <ConfidentialityNotice variant={isParentFlow ? "parent" : "professional"} />}
            <Button type="submit" className="w-full h-12" disabled={busy} data-testid="auth-submit-btn">
              {busy ? "Please wait…" : mode === "login" ? "Sign in" : mode === "register" ? (isParentFlow ? "Create parent account" : "Create professional account") : mode === "forgot" ? "Send verification code" : "Reset password"}
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
