import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export function DeleteAccountButton({ onDeleted }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const go = async () => {
    setBusy(true);
    try { await api.delete("/auth/me", { data: { password: pw, confirm } }); toast.success("Your account and private data were deleted."); setOpen(false); await onDeleted?.(); navigate("/"); } catch (e) { toast.error(formatApiError(e)); } finally { setBusy(false); }
  };
  return (
    <>
      <Button variant="ghost" size="sm" className="text-red-700 hover:bg-red-50 hover:text-red-800" onClick={() => setOpen(true)} data-testid="delete-account-btn"><Trash2 className="mr-1 h-4 w-4" /> Delete my account</Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent data-testid="delete-account-dialog">
          <DialogHeader><DialogTitle>Delete your account and private data</DialogTitle>
            <DialogDescription>This removes your account, your assessment answers, safety screening, communication readiness and foundation statements. Reports already certified by a professional keep only a neutral "former participant" placeholder. This cannot be undone.</DialogDescription></DialogHeader>
          <div className="space-y-3">
            <div><Label htmlFor="del-pw">Your password</Label><Input id="del-pw" type="password" value={pw} onChange={(e) => setPw(e.target.value)} data-testid="delete-account-password" /></div>
            <div><Label htmlFor="del-confirm">Type DELETE to confirm</Label><Input id="del-confirm" value={confirm} onChange={(e) => setConfirm(e.target.value)} data-testid="delete-account-confirm" /></div>
            <Button variant="destructive" disabled={busy || confirm.trim().toUpperCase() !== "DELETE" || !pw} onClick={go} data-testid="delete-account-submit">Permanently delete</Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
