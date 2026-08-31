import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { FileText } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";
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
  const { login, register } = useAuth();
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register({ name, email, password, role });
      }
      navigate("/dashboard");
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

          <h1 className="text-3xl font-semibold mb-6" data-testid="auth-heading">
            {mode === "login" ? "Welcome back" : "Create your account"}
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
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" className="h-12" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={mode === "register" ? 8 : undefined} data-testid="password-input" />
              {mode === "register" && <p className="text-xs text-muted-foreground">At least 8 characters.</p>}
            </div>
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
            <Button type="submit" className="w-full h-12" disabled={busy} data-testid="auth-submit-btn">
              {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
            </Button>
          </form>
        </div>
      </main>
    </div>
  );
}
