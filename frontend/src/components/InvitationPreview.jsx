import { useState } from "react";
import { Eye } from "lucide-react";
import { toast } from "sonner";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export function InvitationPreviewButton({ payload, disabled, onSend, sending }) {
  const [open, setOpen] = useState(false);
  const [previews, setPreviews] = useState(null);
  const [tab, setTab] = useState("a");

  const openPreview = async () => {
    setPreviews(null);
    setOpen(true);
    try {
      const { data } = await api.post("/joint/invitations/preview", payload);
      setPreviews(data.previews);
    } catch (e) { setOpen(false); toast.error(formatApiError(e)); }
  };

  const current = previews?.find((p) => p.role === tab);
  return (
    <>
      <Button variant="outline" onClick={openPreview} disabled={disabled} className="gap-2" data-testid="preview-invitations-btn"><Eye className="h-4 w-4" /> Preview emails</Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-2xl" data-testid="invitation-preview-modal">
          <DialogHeader>
            <DialogTitle>Preview parent invitations</DialogTitle>
            <DialogDescription>Exactly what each parent will receive. Each email carries its own private link — the parents never share one.</DialogDescription>
          </DialogHeader>
          {!previews ? (
            <p className="text-sm text-muted-foreground py-8 text-center" data-testid="invitation-preview-loading">Building preview…</p>
          ) : (
            <div className="space-y-3">
              <div className="flex gap-2" data-testid="invitation-preview-tabs">
                {previews.map((p) => (
                  <button key={p.role} type="button" onClick={() => setTab(p.role)} className={`px-3 py-1.5 rounded-md text-sm font-medium border ${tab === p.role ? "bg-brand-purple text-white border-brand-purple" : "bg-white border-border hover:bg-muted"}`} data-testid={`invitation-preview-tab-${p.role}`}>
                    Parent {p.role.toUpperCase()}{p.to ? ` · ${p.to}` : ""}
                  </button>
                ))}
              </div>
              {current && (
                <>
                  <p className="text-sm" data-testid="invitation-preview-subject"><span className="font-semibold">Subject:</span> {current.subject}</p>
                  <iframe title={`Invitation preview parent ${tab}`} srcDoc={current.html} className="w-full h-80 border border-border rounded-md bg-white" data-testid="invitation-preview-frame" />
                </>
              )}
            </div>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)} data-testid="invitation-preview-close">Back to edit</Button>
            <Button onClick={() => { setOpen(false); onSend(); }} disabled={!previews || sending} data-testid="invitation-preview-send">{sending ? "Sending…" : "Send Invitations"}</Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
