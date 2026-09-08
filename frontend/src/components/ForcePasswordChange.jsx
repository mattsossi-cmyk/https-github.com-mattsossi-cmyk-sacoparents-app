import { useState } from "react";
import { toast } from "sonner";
import { KeyRound } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function ForcePasswordChange({ onDone }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (next !== confirm) { toast.error("New passwords do not match"); return; }
    setBusy(true);
    try {
      await api.post("/auth/change-password", { current_password: current, new_password: next });
      toast.success("Password updated — welcome to SA CoParents Align");
      onDone();
    } catch (err) { toast.error(formatApiError(err)); } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-foreground/60 backdrop-blur-sm flex items-center justify-center p-4" data-testid="force-password-modal">
      <form onSubmit={submit} className="bg-white rounded-lg border border-border shadow-xl w-full max-w-md p-6 space-y-4">
        <div className="flex items-center gap-2 text-brand-teal"><KeyRound className="h-5 w-5" /><p className="text-xs uppercase tracking-widest font-bold">First sign-in</p></div>
        <h2 className="text-2xl font-semibold">Set your own password</h2>
        <p className="text-sm text-muted-foreground">Your account was created with a temporary password. Please choose a new one before continuing.</p>
        <div className="space-y-2"><Label htmlFor="cur-pw">Temporary password</Label><Input id="cur-pw" type="password" value={current} onChange={(e) => setCurrent(e.target.value)} required data-testid="force-pw-current" /></div>
        <div className="space-y-2"><Label htmlFor="new-pw">New password</Label><Input id="new-pw" type="password" value={next} onChange={(e) => setNext(e.target.value)} required minLength={8} data-testid="force-pw-new" /><p className="text-xs text-muted-foreground">At least 8 characters.</p></div>
        <div className="space-y-2"><Label htmlFor="conf-pw">Confirm new password</Label><Input id="conf-pw" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required minLength={8} data-testid="force-pw-confirm" /></div>
        <Button type="submit" className="w-full h-11" disabled={busy || !current || next.length < 8} data-testid="force-pw-submit">{busy ? "Saving…" : "Save new password"}</Button>
      </form>
    </div>
  );
}
