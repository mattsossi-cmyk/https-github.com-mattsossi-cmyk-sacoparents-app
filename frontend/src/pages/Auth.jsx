import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { FileText } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

export default function Auth() {
  const [mode, setMode] = useState("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("parent");
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
        navigate("/dashboard");
      } else if (mode === "register") {
        await register({ name, email, password, role });
        navigate("/dashboard");
      } else if (mode === "forgot") {
        await api.post("/auth/forgot-password", { email });
        setMode("reset");
        toast.success("If an account exists for that email, a verification code is on its way.");
      } else {
        await api.post("/auth/reset-password", { email, code: resetCode, new_password: newPassword });
        toast.success("Password updated. Sign in with your new password.");
        setMode("login");
        setPassword("");
        setResetCode("");
        setNewPassword("");
      }
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col" data-testid="auth-page">
      <header className="max-w-6xl w-full mx-auto px-6 py-6">
        <Link to="/" className="flex items-center gap-2 w-fit" data-testid="auth-brand-link">
          <FileText className="h-6 w-6 text-primary" />
          <span className="font-display text-2xl font-semibold text-primary">SA CoParents</span>
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
            {mode === "login" ? "Welcome back" : mode === "register" ? "Create your account" : mode === "forgot" ? "Reset your password" : "Enter your code"}
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
            {mode === "register" && (
              <div className="space-y-3">
                <Label>I am a…</Label>
                <RadioGroup value={role} onValueChange={setRole} className="flex gap-6" data-testid="role-radio-group">
                  <div className="flex items-center gap-2">
                    <RadioGroupItem value="parent" id="role-parent" data-testid="role-parent-radio" />
                    <Label htmlFor="role-parent" className="font-normal">Parent</Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <RadioGroupItem value="professional" id="role-professional" data-testid="role-professional-radio" />
                    <Label htmlFor="role-professional" className="font-normal">Professional</Label>
                  </div>
                </RadioGroup>
              </div>
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
            <Button type="submit" className="w-full h-12" disabled={busy} data-testid="auth-submit-btn">
              {busy ? "Please wait…" : mode === "login" ? "Sign in" : mode === "register" ? "Create account" : mode === "forgot" ? "Send verification code" : "Reset password"}
            </Button>
            {(mode === "forgot" || mode === "reset") && (
              <button type="button" onClick={() => setMode("login")} className="w-full text-center text-sm text-muted-foreground hover:text-foreground" data-testid="back-to-login-btn">
                Back to sign in
              </button>
            )}
          </form>
        </div>
      </main>
    </div>
  );
}
